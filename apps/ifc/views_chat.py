"""
Chat-UI Views für CAD-Hub.

Stellt einen HTMX-basierten Chat-Endpoint bereit, der den ChatAgent
mit dem CADToolkit verbindet.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, View

from apps.core.mixins import TenantMixin

from .models import IFCModel

logger = logging.getLogger(__name__)

CAD_SYSTEM_PROMPT = """Du bist ein CAD-Assistent für Architekten und Planer.
Du hast Zugriff auf IFC-Modelldaten (Räume, Wände, Fenster, Türen, Decken).
Beantworte Fragen präzise auf Deutsch. Nutze die verfügbaren Tools, um
Daten aus dem Modell abzurufen. Gib Flächen in m² und Längen in m an.
Wenn du Daten abrufst, fasse die Ergebnisse verständlich zusammen."""


def _get_session_backend():
    """Returns RedisSessionBackend in production, InMemory in dev."""
    from django.conf import settings as django_settings

    redis_url = getattr(django_settings, "REDIS_URL", None)
    if redis_url:
        try:
            import redis.asyncio as aioredis
            from chat_agent.session import RedisSessionBackend

            client = aioredis.from_url(redis_url, decode_responses=True)
            return RedisSessionBackend(client, prefix="cad:chat:", ttl_seconds=86400)
        except ImportError:
            pass

    from chat_agent.session import InMemorySessionBackend
    return InMemorySessionBackend()


def _get_agent(model_id: str):
    """Erstellt einen ChatAgent für ein IFC-Modell (lazy import)."""
    from chat_agent.agent import ChatAgent
    from creative_services.core.llm_client import LLMClient, LLMConfig, LLMProvider

    from .toolkit import CADToolkit

    toolkit = CADToolkit()
    llm = LLMClient(
        LLMConfig(
            provider=LLMProvider.OPENAI,
            model="gpt-4o-mini",
            max_tokens=2048,
        )
    )
    return ChatAgent(
        toolkit=toolkit,
        completion=llm,
        session_backend=_get_session_backend(),
        system_prompt=CAD_SYSTEM_PROMPT,
    )


class ChatView(TenantMixin, LoginRequiredMixin, TemplateView):
    """Chat-UI für ein IFC-Modell."""

    template_name = "cad_hub/chat.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tid = self._tenant_id()
        model_id = self.kwargs.get("model_id")
        if model_id:
            ctx["ifc_model"] = get_object_or_404(
                IFCModel, pk=model_id, tenant_id=tid
            )
        ctx["session_id"] = str(uuid.uuid4())
        return ctx


class ChatAPIView(TenantMixin, LoginRequiredMixin, View):
    """HTMX/JSON endpoint: POST {message, session_id, model_id}."""

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, Exception):
            body = request.POST

        message = body.get("message", "").strip()
        session_id = body.get("session_id", str(uuid.uuid4()))
        model_id = body.get("model_id", "")

        if not message:
            return JsonResponse({"error": "Nachricht fehlt."}, status=400)

        tid = self._tenant_id()

        # Verify model belongs to tenant
        if model_id:
            if not IFCModel.objects.filter(pk=model_id, tenant_id=tid).exists():
                return JsonResponse(
                    {"error": "Modell nicht gefunden."}, status=404
                )

        agent = _get_agent(model_id)

        # Run async agent in sync view
        response = asyncio.run(
            agent.chat(
                session_id=session_id,
                user_message=message,
                user=request.user,
                tenant_id=str(tid) if tid else None,
                metadata={"model_id": model_id},
            )
        )

        if request.headers.get("HX-Request"):
            from django.template.loader import render_to_string
            html = render_to_string(
                "cad_hub/partials/_chat_message.html",
                {
                    "message": message,
                    "response": response.content or "Keine Antwort erhalten.",
                    "error": response.error,
                    "tool_calls_made": response.tool_calls_made,
                },
                request=request,
            )
            from django.http import HttpResponse
            return HttpResponse(html)

        return JsonResponse(
            {
                "content": response.content,
                "error": response.error,
                "tool_calls_made": response.tool_calls_made,
                "rounds": response.rounds,
                "model": response.model,
            }
        )

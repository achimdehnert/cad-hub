"""
Registry Signals — Subscription-Aktivierung triggert GitHub Actions.

Wenn eine TenantSubscription auf status='active' gesetzt wird,
wird automatisch der workflow_dispatch für tenant-onboarding.yml getriggert.

Konfiguration via settings:
    GITHUB_REGISTRY_TOKEN = "ghp_..."   # PAT mit workflow scope
    GITHUB_REGISTRY_OWNER = "achimdehnert"
    GITHUB_REGISTRY_REPO  = "nl2cad"
"""
import logging
from decimal import Decimal

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

logger = logging.getLogger(__name__)


def _trigger_onboarding_workflow(subscription: "TenantSubscription") -> bool:
    """
    Triggert GitHub Actions workflow_dispatch für tenant-onboarding.yml.
    Gibt True zurück wenn erfolgreich, False bei Fehler (best-effort).
    """
    try:
        import httpx
    except ImportError:
        logger.warning("[Registry] httpx nicht installiert — Workflow-Trigger übersprungen")
        return False

    token = getattr(settings, "GITHUB_REGISTRY_TOKEN", "")
    owner = getattr(settings, "GITHUB_REGISTRY_OWNER", "achimdehnert")
    repo  = getattr(settings, "GITHUB_REGISTRY_REPO", "nl2cad")

    if not token:
        logger.warning(
            "[Registry] GITHUB_REGISTRY_TOKEN nicht gesetzt — "
            "Workflow-Trigger für %s übersprungen", subscription.id
        )
        return False

    org = subscription.organization
    module = subscription.module

    # Alle aktiven Module dieser Organisation sammeln
    from .models import TenantSubscription
    active_modules = (
        TenantSubscription.objects
        .filter(organization=org, status="active")
        .values_list("module_id", flat=True)
    )
    enabled_packages = ",".join(sorted(active_modules))

    monthly_total = (
        TenantSubscription.objects
        .filter(organization=org, status="active")
        .aggregate(total=__import__("django.db.models", fromlist=["Sum"]).Sum("monthly_eur"))
    )["total"] or Decimal("0")

    payload = {
        "ref": "main",
        "inputs": {
            "tenant_id":       str(org.slug),
            "tenant_name":     str(org.name),
            "contact_email":   str(org.owner_email if hasattr(org, "owner_email") else ""),
            "branch":          str(subscription.berufsprofil_id or "sonstige"),
            "enabled_packages": enabled_packages,
            "monthly_eur":     str(float(monthly_total)),
            "approved_by":     str(subscription.approved_by or "admin"),
        },
    }

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/tenant-onboarding.yml/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 204:
            logger.info(
                "[Registry] GitHub Actions tenant-onboarding.yml getriggert: org=%s module=%s",
                org.slug, module.id,
            )
            return True
        else:
            logger.error(
                "[Registry] Workflow-Trigger fehlgeschlagen: status=%s body=%s",
                resp.status_code, resp.text[:200],
            )
            return False
    except Exception as exc:
        logger.error("[Registry] Workflow-Trigger Exception: %s", exc)
        return False


@receiver(post_save, sender="registry.TenantSubscription")
def on_subscription_saved(sender, instance, created: bool, **kwargs) -> None:
    """
    Trigger bei Subscription-Speicherung:
    - Neu angelegt mit status=active → Workflow triggern
    - Status wechselt zu active → Workflow triggern
    - activated_at setzen wenn noch nicht gesetzt
    """
    from .models import TenantSubscription

    if instance.status != TenantSubscription.SubscriptionStatus.ACTIVE:
        return

    # activated_at setzen (ohne erneutes Signal)
    if not instance.activated_at:
        TenantSubscription.objects.filter(pk=instance.pk).update(
            activated_at=timezone.now()
        )

    # Nur triggern wenn gerade aktiviert (nicht bei jedem Save)
    # Erkennung: created=True ODER previous_status != active
    # Einfache Heuristik: activated_at war vorher leer
    if created or not instance.activated_at:
        _trigger_onboarding_workflow(instance)
        return

    # Bei Update: pre_save-State nicht verfügbar ohne django-model-utils.
    # Daher: Signal nur beim expliziten activate_subscriptions Admin-Action auslösen.
    # Das Admin-Action setzt das Flag _trigger_workflow=True auf der Instanz.
    if getattr(instance, "_trigger_workflow", False):
        _trigger_onboarding_workflow(instance)

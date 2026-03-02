"""
Seed aifw LLM configuration for cad-hub.

Seeds providers, models, and the cad_nlp AIActionType required by
apps.core.services.llm_client.generate_text().

Idempotent — safe to run multiple times (get_or_create / update_or_create).

Usage:
    python manage.py seed_aifw_config
"""

from django.core.management.base import BaseCommand

from aifw.models import AIActionType, LLMModel, LLMProvider


class Command(BaseCommand):
    help = "Seed aifw providers, models, and cad_nlp action type for cad-hub"

    def handle(self, *args, **options):
        self.stdout.write("Seeding aifw config for cad-hub...\n")

        # Providers
        providers_data = [
            {"name": "openai", "display_name": "OpenAI", "api_key_env_var": "OPENAI_API_KEY"},
            {"name": "anthropic", "display_name": "Anthropic Claude", "api_key_env_var": "ANTHROPIC_API_KEY"},
        ]
        providers = {}
        for data in providers_data:
            p, created = LLMProvider.objects.update_or_create(
                name=data["name"], defaults=data
            )
            providers[data["name"]] = p
            self.stdout.write(f"  {'Created' if created else 'Exists'} provider: {p.display_name}")

        # Models
        models_data = [
            {
                "provider": "openai",
                "name": "gpt-4o-mini",
                "display_name": "GPT-4o Mini",
                "max_tokens": 4096,
                "input_cost_per_million": 0.15,
                "output_cost_per_million": 0.6,
                "is_default": True,
            },
            {
                "provider": "openai",
                "name": "gpt-4o",
                "display_name": "GPT-4o",
                "max_tokens": 4096,
                "supports_vision": True,
                "input_cost_per_million": 2.5,
                "output_cost_per_million": 10.0,
            },
            {
                "provider": "anthropic",
                "name": "claude-3-5-haiku-20241022",
                "display_name": "Claude 3.5 Haiku",
                "max_tokens": 8192,
                "input_cost_per_million": 0.25,
                "output_cost_per_million": 1.25,
            },
        ]
        models = {}
        for data in models_data:
            provider = providers[data.pop("provider")]
            m, created = LLMModel.objects.update_or_create(
                provider=provider, name=data["name"], defaults=data
            )
            models[data["name"]] = m
            self.stdout.write(f"  {'Created' if created else 'Exists'} model: {m}")

        # AIActionType — cad_nlp (required by llm_client.generate_text)
        default_model = models.get("gpt-4o-mini")
        fallback_model = models.get("claude-3-5-haiku-20241022")

        action, created = AIActionType.objects.update_or_create(
            code="cad_nlp",
            defaults={
                "name": "CAD NLP Generation",
                "description": "Natural language processing for CAD annotations, descriptions, and queries.",
                "default_model": default_model,
                "fallback_model": fallback_model,
                "max_tokens": 2000,
                "temperature": 0.3,
                "is_active": True,
            },
        )
        self.stdout.write(
            f"  {'Created' if created else 'Updated'} action: {action.name} (code={action.code})"
        )

        self.stdout.write(self.style.SUCCESS("\n✅ cad-hub aifw config seeded!"))
        self.stdout.write(f"   Providers: {LLMProvider.objects.count()}")
        self.stdout.write(f"   Models: {LLMModel.objects.count()}")
        self.stdout.write(f"   Actions: {AIActionType.objects.count()}")

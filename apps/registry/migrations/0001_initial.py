"""Initial migration for apps.registry."""
import django.db.models.deletion
import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("django_tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NL2CADModule",
            fields=[
                ("id", models.SlugField(primary_key=True, serialize=False, help_text="URL-sicherer Bezeichner, z.B. 'brandschutz'")),
                ("package", models.CharField(max_length=120, unique=True, verbose_name="PyPI-Package-Name")),
                ("name", models.CharField(max_length=120, verbose_name="Anzeigename")),
                ("icon", models.CharField(default="📦", max_length=10, verbose_name="Icon (Emoji)")),
                ("color", models.CharField(default="#2563eb", max_length=7, verbose_name="Farbe (Hex)")),
                ("tagline", models.CharField(blank=True, max_length=200, verbose_name="Kurzzeile")),
                ("description", models.TextField(blank=True, verbose_name="Beschreibung")),
                ("features", models.JSONField(default=list, verbose_name="Features")),
                ("deps", models.JSONField(default=list, verbose_name="Abhängigkeiten")),
                ("norms", models.JSONField(default=list, verbose_name="Regelwerke / Normen")),
                ("main_classes", models.JSONField(default=list, verbose_name="Wichtigste Klassen")),
                ("is_required", models.BooleanField(default=False, verbose_name="Pflicht (immer aktiv)")),
                ("status", models.CharField(choices=[("stable", "Stabil (produktiv)"), ("beta", "Beta"), ("planned", "In Planung"), ("deprecated", "Veraltet")], db_index=True, default="planned", max_length=20, verbose_name="Status")),
                ("priority", models.CharField(choices=[("high", "Hoch"), ("medium", "Mittel"), ("low", "Niedrig")], default="medium", max_length=10, verbose_name="Priorität")),
                ("story_points", models.PositiveIntegerField(default=0, verbose_name="Story Points")),
                ("target_quarter", models.CharField(blank=True, max_length=20, verbose_name="Ziel-Quartal")),
                ("adr_path", models.CharField(blank=True, max_length=255, verbose_name="ADR-Pfad")),
                ("workflow_path", models.CharField(blank=True, max_length=255, verbose_name="Workflow-Pfad")),
                ("pypi_url", models.URLField(blank=True, verbose_name="PyPI-URL")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="Reihenfolge")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "nl2cad-Modul", "verbose_name_plural": "nl2cad-Module", "ordering": ["sort_order", "id"], "db_table": "registry_module"},
        ),
        migrations.CreateModel(
            name="BerufsProfil",
            fields=[
                ("id", models.SlugField(primary_key=True, serialize=False, help_text="z.B. 'brandschutz_sv'")),
                ("name", models.CharField(max_length=100, verbose_name="Berufsbezeichnung")),
                ("icon", models.CharField(default="👤", max_length=10, verbose_name="Icon")),
                ("fokus", models.CharField(blank=True, max_length=200, verbose_name="Fachlicher Fokus")),
                ("bereitschaft", models.CharField(blank=True, max_length=100, verbose_name="Sofort-Bereitschaft")),
                ("install_command", models.TextField(blank=True, verbose_name="pip install Befehl")),
                ("yaml_config", models.TextField(blank=True, verbose_name="YAML-Konfiguration")),
                ("nlp_keywords", models.TextField(blank=True, verbose_name="NLP-Keywords")),
                ("report_template", models.CharField(blank=True, max_length=100, verbose_name="Report-Template")),
                ("primary_output", models.CharField(blank=True, max_length=200, verbose_name="Primärer Output")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Berufsprofil", "verbose_name_plural": "Berufsprofile", "ordering": ["sort_order", "name"], "db_table": "registry_berufsprofil"},
        ),
        migrations.CreateModel(
            name="ProfilModuleMapping",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("profil", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="registry.berufsprofil")),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="registry.nl2cadmodule")),
                ("mapping_type", models.CharField(choices=[("vorhanden", "✅ Vorhanden"), ("konfiguration", "🔧 Nur Konfiguration nötig"), ("neu", "🔨 Neu-Entwicklung"), ("nicht", "— Nicht relevant")], default="neu", max_length=20, verbose_name="Mapping-Typ")),
                ("is_recommended", models.BooleanField(default=True, verbose_name="Empfohlen")),
            ],
            options={"verbose_name": "Profil-Modul-Zuordnung", "verbose_name_plural": "Profil-Modul-Zuordnungen", "ordering": ["profil", "module__sort_order"], "db_table": "registry_profil_module_mapping", "unique_together": {("profil", "module")}},
        ),
        migrations.AddField(
            model_name="berufsprofil",
            name="modules",
            field=models.ManyToManyField(related_name="berufsprofile", through="registry.ProfilModuleMapping", to="registry.nl2cadmodule", verbose_name="Module"),
        ),
        migrations.CreateModel(
            name="ModulePricing",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pricing_tiers", to="registry.nl2cadmodule", verbose_name="Modul")),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="custom_module_pricing", to="django_tenancy.organization", verbose_name="Organisation (leer = Standard)")),
                ("pricing_type", models.CharField(choices=[("standard", "Standard"), ("custom", "Individuell (Tenant-spezifisch)"), ("free", "Kostenlos")], default="standard", max_length=20, verbose_name="Preistyp")),
                ("setup_eur", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8, verbose_name="Setup-Preis (€)")),
                ("monthly_eur", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8, verbose_name="Monatspreis (€)")),
                ("label", models.CharField(blank=True, max_length=100, verbose_name="Preis-Label")),
                ("valid_from", models.DateField(blank=True, null=True, verbose_name="Gültig ab")),
                ("valid_until", models.DateField(blank=True, null=True, verbose_name="Gültig bis")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Modul-Preis", "verbose_name_plural": "Modul-Preise", "ordering": ["module", "organization"], "db_table": "registry_module_pricing", "unique_together": {("module", "organization")}},
        ),
        migrations.AddIndex(
            model_name="modulePricing",
            index=models.Index(fields=["module", "organization"], name="registry_mo_module_i_idx"),
        ),
        migrations.CreateModel(
            name="TenantSubscription",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("tenant_id", models.UUIDField(db_index=True, help_text="Multi-tenancy isolator")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="module_subscriptions", to="django_tenancy.organization", verbose_name="Organisation")),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="subscriptions", to="registry.nl2cadmodule", verbose_name="Modul")),
                ("berufsprofil", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="registry.berufsprofil", verbose_name="Berufsprofil (bei Onboarding gewählt)")),
                ("status", models.CharField(choices=[("pending", "Ausstehend (Freigabe erwartet)"), ("trial", "Test-Phase"), ("active", "Aktiv"), ("suspended", "Gesperrt"), ("cancelled", "Gekündigt")], db_index=True, default="pending", max_length=20, verbose_name="Status")),
                ("monthly_eur", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8, verbose_name="Aktueller Monatspreis (€)")),
                ("setup_eur", models.DecimalField(decimal_places=2, default=Decimal("0"), max_digits=8, verbose_name="Setup-Preis (€)")),
                ("activated_at", models.DateTimeField(blank=True, null=True, verbose_name="Aktiviert am")),
                ("cancelled_at", models.DateTimeField(blank=True, null=True, verbose_name="Gekündigt am")),
                ("trial_until", models.DateField(blank=True, null=True, verbose_name="Test-Phase bis")),
                ("approved_by", models.CharField(blank=True, max_length=100, verbose_name="Freigabe durch")),
                ("notes", models.TextField(blank=True, verbose_name="Interne Notizen")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Modul-Subscription", "verbose_name_plural": "Modul-Subscriptions", "ordering": ["-created_at"], "db_table": "registry_tenant_subscription", "unique_together": {("organization", "module")}},
        ),
        migrations.AddIndex(
            model_name="tenantsubscription",
            index=models.Index(fields=["tenant_id", "status"], name="registry_te_tenant__idx"),
        ),
        migrations.AddIndex(
            model_name="tenantsubscription",
            index=models.Index(fields=["organization", "status"], name="registry_te_org_sta_idx"),
        ),
        migrations.CreateModel(
            name="DiscountRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, verbose_name="Bezeichnung")),
                ("min_modules", models.PositiveIntegerField(default=3, verbose_name="Mind. Anzahl Module")),
                ("discount_percent", models.DecimalField(decimal_places=2, default=Decimal("15"), max_digits=5, verbose_name="Rabatt (%)")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktiv")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "Rabatt-Regel", "verbose_name_plural": "Rabatt-Regeln", "ordering": ["min_modules"], "db_table": "registry_discount_rule"},
        ),
    ]

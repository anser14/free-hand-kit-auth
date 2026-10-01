# Generated manually for the first stable database contract of fk_auth.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="OneTimeCredential",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                (
                    "purpose",
                    models.CharField(
                        choices=[("email_verification", "Email verification")], max_length=32
                    ),
                ),
                ("email", models.EmailField(max_length=254)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="onetimecredential",
            index=models.Index(fields=["user", "purpose", "consumed_at"], name="fk_auth_one_user_id_54da79_idx"),
        ),
        migrations.AddIndex(
            model_name="onetimecredential",
            index=models.Index(fields=["email", "purpose", "consumed_at"], name="fk_auth_one_email_41f6aa_idx"),
        ),
    ]

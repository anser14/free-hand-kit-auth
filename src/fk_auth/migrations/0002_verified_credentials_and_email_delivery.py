"""Separate verified-email evidence from consumed credentials and add a safe outbox."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("fk_auth", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="onetimecredential",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="EmailDelivery",
            fields=[
                (
                    "id",
                    models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"),
                ),
                ("recipient", models.EmailField(max_length=254)),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("email_verification", "Email verification"),
                            ("password_reset", "Password reset"),
                        ],
                        max_length=32,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sending", "Sending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("is_resend", models.BooleanField(default=False)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("available_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.AddIndex(
            model_name="emaildelivery",
            index=models.Index(fields=["status", "available_at"], name="fk_auth_delivery_ready_idx"),
        ),
        migrations.AddIndex(
            model_name="emaildelivery",
            index=models.Index(fields=["user", "kind", "status"], name="fk_auth_delivery_user_idx"),
        ),
    ]

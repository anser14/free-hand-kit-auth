"""Purge privacy-sensitive, expired Freehand Kit Auth operational data."""

from django.core.management.base import BaseCommand

from fk_auth.conf import get_settings
from fk_auth.services.credentials import purge_expired_unverified_credentials
from fk_auth.services.outbox import purge_old_deliveries


class Command(BaseCommand):
    help = "Purge expired unverified credentials and retained outbox records."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        settings = get_settings()
        credential_days = int(settings["CREDENTIAL_RETENTION_DAYS"])
        delivery_days = int(settings["EMAIL"]["OUTBOX_RETENTION_DAYS"])
        if options["dry_run"]:
            self.stdout.write(
                f"Would purge expired unverified credentials older than {credential_days} day(s) "
                f"and outbox records older than {delivery_days} day(s)."
            )
            return
        credentials = purge_expired_unverified_credentials(retention_days=credential_days)
        deliveries = purge_old_deliveries(retention_days=delivery_days)
        self.stdout.write(
            self.style.SUCCESS(
                f"Purged {credentials} credential record(s) and {deliveries} delivery record(s)."
            )
        )

"""Dispatch retryable Freehand Kit Auth email-delivery records."""

from django.core.management.base import BaseCommand

from fk_auth.services.outbox import dispatch_pending_deliveries


class Command(BaseCommand):
    help = "Dispatch pending or retryable Freehand Kit Auth email deliveries."

    def add_arguments(self, parser):  # type: ignore[no-untyped-def]
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):  # type: ignore[no-untyped-def]
        limit = max(1, int(options["limit"]))
        delivered = dispatch_pending_deliveries(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"Delivered {delivered} email(s)."))

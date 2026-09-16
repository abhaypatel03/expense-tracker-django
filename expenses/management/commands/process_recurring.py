from django.core.management.base import BaseCommand

from expenses.services import process_recurring_expenses


class Command(BaseCommand):
    help = "Create due recurring expenses without duplicating occurrences."

    def handle(self, *args, **options):
        processed = process_recurring_expenses()
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed recurring expenses: {processed}"
            )
        )

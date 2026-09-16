import calendar
from datetime import date, timedelta

from django.db import transaction

from .models import Expense


def next_recurring_date(current_date, frequency):
    """Return the next occurrence, clamping month-end dates safely."""
    if frequency == "daily":
        return current_date + timedelta(days=1)

    if frequency == "weekly":
        return current_date + timedelta(days=7)

    if frequency == "monthly":
        year = current_date.year + (current_date.month // 12)
        month = current_date.month % 12 + 1
        day = min(
            current_date.day,
            calendar.monthrange(year, month)[1],
        )
        return date(year, month, day)

    if frequency == "yearly":
        year = current_date.year + 1
        day = min(
            current_date.day,
            calendar.monthrange(year, current_date.month)[1],
        )
        return date(year, current_date.month, day)

    raise ValueError(f"Unsupported recurring frequency: {frequency}")


def process_recurring_expenses(as_of=None, user=None):
    """Create all due recurring occurrences and return the count created."""
    as_of = as_of or date.today()
    recurring = Expense.objects.filter(
        is_recurring=True,
        next_recurring_date__isnull=False,
    )

    if user is not None:
        recurring = recurring.filter(user=user)

    processed = 0

    for expense in recurring.order_by("id").values_list("id", flat=True):
        with transaction.atomic():
            current = Expense.objects.select_for_update().get(id=expense)

            while (
                current.is_recurring
                and current.next_recurring_date
                and current.next_recurring_date <= as_of
            ):
                due_date = current.next_recurring_date
                frequency = current.recurring_frequency
                following_date = next_recurring_date(due_date, frequency)

                occurrence_exists = Expense.objects.filter(
                    user=current.user,
                    title=current.title,
                    amount=current.amount,
                    category=current.category,
                    description=current.description,
                    date=due_date,
                    is_recurring=True,
                    recurring_frequency=frequency,
                    next_recurring_date=following_date,
                ).exists()

                if not occurrence_exists:
                    Expense.objects.create(
                        user=current.user,
                        title=current.title,
                        amount=current.amount,
                        category=current.category,
                        description=current.description,
                        date=due_date,
                        is_recurring=True,
                        recurring_frequency=frequency,
                        next_recurring_date=following_date,
                    )
                    processed += 1

                current.next_recurring_date = following_date
                current.save(update_fields=["next_recurring_date", "updated_at"])

    return processed

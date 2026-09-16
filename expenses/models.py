from datetime import date
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.username


class Expense(models.Model):

    CATEGORY_CHOICES = [
        ("Food", "Food"),
        ("Shopping", "Shopping"),
        ("Travel", "Travel"),
        ("Bills", "Bills"),
        ("Entertainment", "Entertainment"),
        ("Health", "Health"),
        ("Education", "Education"),
        ("Other", "Other"),
    ]

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="expenses"
    )

    title = models.CharField(
        max_length=200
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    date = models.DateField(
        default=date.today
    )

    # =========================
    # RECURRING EXPENSE FIELDS
    # =========================

    is_recurring = models.BooleanField(
        default=False
    )

    recurring_frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        blank=True,
        null=True
    )

    next_recurring_date = models.DateField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.title} - ₹{self.amount}"


class Budget(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="budgets"
    )

    month = models.DateField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.user.username} - {self.month:%B %Y} - ₹{self.amount}"

    class Meta:
        ordering = ["-month"]

        constraints = [
            models.UniqueConstraint(
                fields=["user", "month"],
                name="unique_user_month_budget",
            )
        ]
from django.contrib import admin
from .models import Expense, Profile, Budget


# =====================================================
# EXPENSE
# =====================================================

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "title",
        "amount",
        "category",
        "date",
        "created_at",
    )

    list_filter = (
        "category",
        "date",
    )

    search_fields = (
        "title",
        "user__username",
    )

    ordering = (
        "-date",
        "-id",
    )


# =====================================================
# PROFILE
# =====================================================

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "created_at",
    )

    search_fields = (
        "user__username",
    )


# =====================================================
# BUDGET
# =====================================================

@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "user",
        "amount",
        "updated_at",
    )

    search_fields = (
        "user__username",
    )

    ordering = (
        "-updated_at",
    )
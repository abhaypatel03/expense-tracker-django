from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from .models import Expense, Budget


@staff_member_required
def admin_dashboard(request):

    today = timezone.localdate()

    # ==========================================
    # TOTAL USERS
    # ==========================================

    total_users = User.objects.filter(
        is_superuser=False
    ).count()

    # ==========================================
    # TOTAL EXPENSE
    # ==========================================

    total_expense = Expense.objects.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # ==========================================
    # TOTAL BUDGET
    # ==========================================

    total_budget = Budget.objects.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # ==========================================
    # TODAY EXPENSE
    # ==========================================

    today_expense = Expense.objects.filter(
        date=today
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    # ==========================================
    # RECENT EXPENSES
    # ==========================================

    recent_expenses = Expense.objects.select_related(
        "user"
    ).order_by(
        "-date",
        "-id"
    )[:10]

    # ==========================================
    # CATEGORY-WISE EXPENSE
    # ==========================================

    category_expenses = Expense.objects.values(
        "category"
    ).annotate(
        total=Sum("amount")
    ).order_by("-total")

    # ==========================================
    # CONTEXT
    # ==========================================

    context = {
        "total_users": total_users,
        "total_expense": total_expense,
        "total_budget": total_budget,
        "today_expense": today_expense,
        "recent_expenses": recent_expenses,
        "category_expenses": category_expenses,
    }

    return render(
        request,
        "expenses/admin_dashboard.html",
        context
    )
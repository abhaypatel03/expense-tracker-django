import os
from datetime import date
import csv
from decimal import Decimal, InvalidOperation
from functools import wraps
from reportlab.pdfgen import canvas

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.paginator import Paginator

from .forms import ExpenseForm, RegisterForm, ProfileForm
from .models import Expense, Profile, Budget
from .services import process_recurring_expenses


def normal_user_required(view_func):
    @wraps(view_func)
    def wrapped_view(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("login")

        if request.user.is_staff:
            return redirect("login")

        return view_func(request, *args, **kwargs)

    return wrapped_view



@normal_user_required
def export_pdf(request):

    expenses = Expense.objects.filter(
        user=request.user
    ).order_by("-date", "-id")

    response = HttpResponse(
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        'attachment; filename="expenses.pdf"'
    )

    pdf = canvas.Canvas(response)

    # Page size
    width, height = 595, 842

    # Title
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 50, "Expense Report")

    # User
    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        50,
        height - 70,
        f"User: {request.user.username}"
    )

    # Table heading
    y = height - 110

    pdf.setFont("Helvetica-Bold", 10)

    pdf.drawString(50, y, "Title")
    pdf.drawString(220, y, "Amount")
    pdf.drawString(320, y, "Category")
    pdf.drawString(450, y, "Date")

    y -= 20

    pdf.setFont("Helvetica", 9)

    for expense in expenses:

        # New page if required
        if y < 50:
            pdf.showPage()

            y = height - 50

            pdf.setFont("Helvetica-Bold", 10)

            pdf.drawString(50, y, "Title")
            pdf.drawString(220, y, "Amount")
            pdf.drawString(320, y, "Category")
            pdf.drawString(450, y, "Date")

            y -= 20
            pdf.setFont("Helvetica", 9)

        title = str(expense.title)[:25]
        amount = str(expense.amount)
        category = str(expense.category)[:18]
        date = str(expense.date)

        pdf.drawString(50, y, title)
        pdf.drawString(220, y, amount)
        pdf.drawString(320, y, category)
        pdf.drawString(450, y, date)

        y -= 18

    pdf.save()

    return response


@normal_user_required
def export_csv(request):

    # -----------------------------------------
    # USER EXPENSES
    # -----------------------------------------

    expenses = Expense.objects.filter(
        user=request.user
    ).order_by(
        "-date",
        "-id"
    )

    # -----------------------------------------
    # SEARCH
    # -----------------------------------------

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        expenses = expenses.filter(
            title__icontains=search
        )

    # -----------------------------------------
    # CATEGORY
    # -----------------------------------------

    category = request.GET.get(
        "category",
        ""
    ).strip()

    if category:

        expenses = expenses.filter(
            category=category
        )

    # -----------------------------------------
    # FROM DATE
    # -----------------------------------------

    from_date = request.GET.get(
        "from_date",
        ""
    ).strip()

    if from_date:

        expenses = expenses.filter(
            date__gte=from_date
        )

    # -----------------------------------------
    # TO DATE
    # -----------------------------------------

    to_date = request.GET.get(
        "to_date",
        ""
    ).strip()

    if to_date:

        expenses = expenses.filter(
            date__lte=to_date
        )

    # -----------------------------------------
    # SORTING
    # -----------------------------------------

    sort = request.GET.get(
        "sort",
        ""
    ).strip()

    if sort == "amount_asc":

        expenses = expenses.order_by(
            "amount"
        )

    elif sort == "amount_desc":

        expenses = expenses.order_by(
            "-amount"
        )

    elif sort == "newest":

        expenses = expenses.order_by(
            "-date",
            "-id"
        )

    elif sort == "oldest":

        expenses = expenses.order_by(
            "date",
            "id"
        )

    # -----------------------------------------
    # CSV RESPONSE
    # -----------------------------------------

    response = HttpResponse(
        content_type="text/csv"
    )

    response["Content-Disposition"] = (
        'attachment; filename="expenses.csv"'
    )

    # -----------------------------------------
    # CSV WRITER
    # -----------------------------------------

    writer = csv.writer(
        response
    )

    # -----------------------------------------
    # HEADER
    # -----------------------------------------

    writer.writerow([
        "Title",
        "Amount",
        "Category",
        "Date",
        "Description"
    ])

    # -----------------------------------------
    # DATA
    # -----------------------------------------

    for expense in expenses:

        writer.writerow([
            expense.title,
            expense.amount,
            expense.category,
            expense.date,
            getattr(
                expense,
                "description",
                ""
            )
        ])

    return response

# =========================================================
# DASHBOARD
# =========================================================

@normal_user_required
def dashboard(request):

    user = request.user
    process_recurring_expenses(user=user)
    today = timezone.localdate()

    # =====================================================
    # USER EXPENSES
    # =====================================================

    expenses = Expense.objects.filter(
        user=user
    )

    # =====================================================
    # TOTAL EXPENSE
    # =====================================================

    total_expense = expenses.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # =====================================================
    # CURRENT MONTH EXPENSE
    # =====================================================

    month_expense = expenses.filter(
        date__year=today.year,
        date__month=today.month
    )

    month_total = month_expense.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # =====================================================
    # TODAY EXPENSE
    # =====================================================

    today_total = expenses.filter(
        date=today
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    # =====================================================
    # RECENT EXPENSES
    # =====================================================

    recent_expenses = expenses.order_by(
        "-date",
        "-id"
    )[:5]

    # =====================================================
    # CATEGORY DATA
    # =====================================================

    categories = expenses.values(
        "category"
    ).annotate(
        total=Sum("amount")
    ).order_by("-total")

    category_data = []

    for item in categories:

        category_data.append({
            "name": item["category"],
            "total": float(item["total"])
        })

    # =====================================================
    # MONTHLY CHART DATA
    # =====================================================

    monthly_data = []

    for month in range(1, 13):

        monthly_total = expenses.filter(
            date__year=today.year,
            date__month=month
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        monthly_data.append({
            "month": date(
                today.year,
                month,
                1
            ).strftime("%b"),

            "total": float(monthly_total)
        })

    # =====================================================
    # CURRENT MONTH BUDGET
    # =====================================================

    current_month = today.replace(day=1)

    budget = Budget.objects.filter(
        user=user,
        month=current_month
    ).first()

    budget_amount = 0
    remaining_budget = 0
    budget_percentage = 0

    if budget:

        budget_amount = float(
            budget.amount
        )

        remaining_budget = (
            budget_amount - float(month_total)
        )

        if remaining_budget < 0:
            remaining_budget = 0

        if budget_amount > 0:

            budget_percentage = (
                float(month_total)
                / budget_amount
            ) * 100

            if budget_percentage > 100:
                budget_percentage = 100

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "total": total_expense,

        "total_expense": total_expense,

        "month_total": month_total,

        "this_month": month_total,

        "today_total": today_total,

        "today_expense": today_total,

        "recent_expenses": recent_expenses,

        "categories": category_data,

        "monthly_data": monthly_data,

        "budget_amount": budget_amount,

        "remaining_budget": remaining_budget,

        "budget_percentage": budget_percentage,

        "current_month": today.strftime(
            "%B %Y"
        ),
    }

    return render(
        request,
        "expenses/dashboard.html",
        context
    )


# =========================================================
# EXPENSES
# =========================================================
@normal_user_required
def expenses(request):

    expense_list = Expense.objects.filter(
        user=request.user
    )

    # =====================================================
    # SEARCH
    # =====================================================

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        expense_list = expense_list.filter(
            title__icontains=search
        )

    # =====================================================
    # CATEGORY
    # =====================================================

    category = request.GET.get(
        "category",
        ""
    ).strip()

    if category:

        expense_list = expense_list.filter(
            category=category
        )

    # =====================================================
    # FROM DATE
    # =====================================================

    from_date = request.GET.get(
        "from_date",
        ""
    ).strip()

    if from_date:

        expense_list = expense_list.filter(
            date__gte=from_date
        )

    # =====================================================
    # TO DATE
    # =====================================================

    to_date = request.GET.get(
        "to_date",
        ""
    ).strip()

    if to_date:

        expense_list = expense_list.filter(
            date__lte=to_date
        )

    # =====================================================
    # SORTING
    # =====================================================

    sort = request.GET.get(
        "sort",
        "newest"
    )

    if sort == "amount_low":

        expense_list = expense_list.order_by(
            "amount",
            "-date",
            "-id"
        )

    elif sort == "amount_high":

        expense_list = expense_list.order_by(
            "-amount",
            "-date",
            "-id"
        )

    elif sort == "oldest":

        expense_list = expense_list.order_by(
            "date",
            "id"
        )

    else:

        # Newest → Oldest
        sort = "newest"

        expense_list = expense_list.order_by(
            "-date",
            "-id"
        )

    # =====================================================
    # TOTAL
    # =====================================================

    total = expense_list.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # =====================================================
    # PAGINATION
    # =====================================================

    paginator = Paginator(
        expense_list,
        10
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "expenses": page_obj,

        "page_obj": page_obj,

        "search": search,

        "selected_category": category,

        "from_date": from_date,

        "to_date": to_date,

        "sort": sort,

        "total": total,

    }

    return render(
        request,
        "expenses/expenses.html",
        context
    )


# =========================================================
# ADD EXPENSE
# =========================================================

@normal_user_required
def add_expense(request):

    form = ExpenseForm(
        request.POST or None
    )

    if form.is_valid():

        expense = form.save(
            commit=False
        )

        expense.user = request.user

        expense.save()

        messages.success(
            request,
            "Expense added successfully."
        )

        return redirect("expenses")

    return render(
        request,
        "expenses/add_expense.html",
        {
            "form": form,
            "title": "Add Expense"
        }
    )


# =========================================================
# EDIT EXPENSE
# =========================================================

@normal_user_required
def edit_expense(request, expense_id):

    expense = get_object_or_404(
        Expense,
        id=expense_id,
        user=request.user
    )

    form = ExpenseForm(
        request.POST or None,
        instance=expense
    )

    if form.is_valid():

        form.save()

        messages.success(
            request,
            "Expense updated successfully."
        )

        return redirect("expenses")

    return render(
        request,
        "expenses/edit_expense.html",
        {
            "form": form,
            "title": "Edit Expense",
            "expense": expense
        }
    )


# =========================================================
# DELETE EXPENSE
# =========================================================

@normal_user_required
def delete_expense(request, expense_id):

    expense = get_object_or_404(
        Expense,
        id=expense_id,
        user=request.user
    )

    if request.method == "POST":

        expense.delete()

        messages.success(
            request,
            "Expense deleted successfully."
        )

        return redirect("expenses")

    return render(
        request,
        "expenses/delete.html",
        {
            "expense": expense
        }
    )


# =========================================================
# REPORTS
# =========================================================

@normal_user_required
def reports(request):

    user = request.user
    today = timezone.localdate()

    user_expenses = Expense.objects.filter(
        user=user
    )

    # =====================================================
    # TOTAL EXPENSE
    # =====================================================

    total_expense = user_expenses.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # =====================================================
    # CURRENT MONTH EXPENSE
    # =====================================================

    month_expenses_queryset = user_expenses.filter(
        date__year=today.year,
        date__month=today.month
    )

    month_total = month_expenses_queryset.aggregate(
        total=Sum("amount")
    )["total"] or 0

    # =====================================================
    # TODAY EXPENSE
    # =====================================================

    today_expense = user_expenses.filter(
        date=today
    ).aggregate(
        total=Sum("amount")
    )["total"] or 0

    # =====================================================
    # CATEGORY DATA
    # =====================================================

    categories = user_expenses.values(
        "category"
    ).annotate(
        total=Sum("amount")
    ).order_by("-total")

    # =====================================================
    # MONTH-WISE DATA
    # =====================================================

    month_expenses = (
        user_expenses
        .values(
            "date__year",
            "date__month"
        )
        .annotate(
            total=Sum("amount")
        )
        .order_by(
            "date__year",
            "date__month"
        )
    )

    month_names = [
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    monthly_data = []

    for item in month_expenses:

        month_number = item["date__month"]

        monthly_data.append({
            "month": month_names[month_number],
            "year": item["date__year"],
            "total": item["total"],
        })

    # =====================================================
    # CURRENT MONTH BUDGET
    # =====================================================

    current_month = today.replace(
        day=1
    )

    budget = Budget.objects.filter(
        user=user,
        month=current_month
    ).first()

    budget_amount = (
        budget.amount
        if budget
        else Decimal("0.00")
    )

    budget_percentage = 0

    if budget_amount > 0:
        budget_percentage = min(
            (month_total / budget_amount) * 100,
            Decimal("100")
        )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "total_expense": total_expense,

        "month_total": month_total,

        "monthly_expense": month_total,

        "today_expense": today_expense,

        "categories": categories,

        "category_expenses": categories,

        "expenses": user_expenses,

        "monthly_data": monthly_data,

        "budget_amount": budget_amount,

        "budget_percentage": budget_percentage,

        "current_month": today.strftime(
            "%B %Y"
        ),
    }

    return render(
        request,
        "expenses/reports.html",
        context
    )


# =========================================================
# PROFILE
# =========================================================

@normal_user_required
def profile(request):

    profile, created = Profile.objects.get_or_create(
        user=request.user
    )

    return render(
        request,
        "expenses/profile.html",
        {
            "profile": profile
        }
    )


# =========================================================
# EDIT PROFILE
# =========================================================

@normal_user_required
def edit_profile(request):

    user = request.user

    if request.method == "POST":

        form = ProfileForm(
            request.POST,
            instance=user
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Profile updated successfully."
            )

            return redirect("profile")

    else:

        form = ProfileForm(
            instance=user
        )

    return render(
        request,
        "expenses/edit_profile.html",
        {
            "form": form
        }
    )

# =========================================================
# CHANGE PASSWORD
# =========================================================

@normal_user_required
def change_password(request):

    if request.method == "POST":

        form = PasswordChangeForm(
            request.user,
            request.POST
        )

        if form.is_valid():

            user = form.save()

            update_session_auth_hash(
                request,
                user
            )

            messages.success(
                request,
                "Password changed successfully!"
            )

            return redirect("profile")

    else:

        form = PasswordChangeForm(
            request.user
        )

    return render(
        request,
        "expenses/change_password.html",
        {
            "form": form
        }
    )


# =========================================================
# LOGIN
# =========================================================

def login_view(request):

    if request.user.is_authenticated:

        if request.user.is_staff:

            return render(
                request,
                "expenses/login.html",
                {
                    "error": (
                        "Admin is open at /admin/. "
                        "Login here with a website user account."
                    ),
                }
            )

        return redirect("dashboard")

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            if user.is_staff:

                return render(
                    request,
                    "expenses/login.html",
                    {
                        "error": "Staff accounts must use the admin login."
                    }
                )

            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend"
            )

            return redirect("dashboard")

        return render(
            request,
            "expenses/login.html",
            {
                "error": "Invalid username or password.",
            }
        )

    return render(
        request,
        "expenses/login.html",
        {}
    )


# =========================================================
# REGISTER
# =========================================================

def register(request):

    if (
        request.user.is_authenticated
        and not request.user.is_staff
    ):
        return redirect("dashboard")

    form = RegisterForm(
        request.POST or None
    )

    if form.is_valid():

        user = form.save()

        login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend"
        )

        return redirect("dashboard")

    return render(
        request,
        "expenses/register.html",
        {
            "form": form
        }
    )


# =========================================================
# LOGOUT
# =========================================================

def logout_view(request):

    return redirect(
        "logout_confirm"
    )


# =========================================================
# LOGOUT CONFIRMATION
# =========================================================

@normal_user_required
def logout_confirm(request):

    if request.method == "POST":

        logout(request)

        return redirect(
            "login"
        )

    return render(
        request,
        "expenses/logout_confirm.html"
    )


# =========================================================
# BUDGET
# =========================================================

@normal_user_required
def budget(request):

    today = timezone.localdate()

    current_month = today.replace(
        day=1
    )

    # =====================================================
    # CURRENT MONTH BUDGET
    # =====================================================

    budget_obj, created = Budget.objects.get_or_create(
        user=request.user,
        month=current_month,
        defaults={
            "amount": Decimal("0.00")
        }
    )

    # =====================================================
    # SAVE BUDGET
    # =====================================================

    if request.method == "POST":

        budget_amount = request.POST.get(
            "budget_amount",
            ""
        ).strip()

        try:

            budget_amount = Decimal(
                budget_amount
            )

            if budget_amount < 0:

                messages.error(
                    request,
                    "Budget cannot be negative."
                )

            else:

                budget_obj.amount = budget_amount

                budget_obj.save()

                messages.success(
                    request,
                    "Budget saved successfully!"
                )

                return redirect(
                    "budget"
                )

        except (
            InvalidOperation,
            TypeError
        ):

            messages.error(
                request,
                "Please enter a valid amount."
            )

    # =====================================================
    # CURRENT MONTH EXPENSES
    # =====================================================

    month_expenses = Expense.objects.filter(
        user=request.user,
        date__year=today.year,
        date__month=today.month
    )

    total_spent = month_expenses.aggregate(
        total=Sum("amount")
    )["total"] or 0

    monthly_budget = budget_obj.amount

    # =====================================================
    # REMAINING
    # =====================================================

    remaining = (
        monthly_budget - total_spent
    )

    # =====================================================
    # PERCENTAGE
    # =====================================================

    if monthly_budget > 0:

        percentage = (
            total_spent
            / monthly_budget
        ) * 100

    else:

        percentage = 0

    progress_percentage = min(
        percentage,
        100
    )

    # =====================================================
    # STATUS
    # =====================================================

    if monthly_budget == 0:

        status_message = (
            "💡 Set your monthly budget to start tracking."
        )

    elif remaining < 0:

        status_message = (
            "⚠️ You have exceeded your monthly budget."
        )

    elif percentage >= 80:

        status_message = (
            "⚠️ You are close to your monthly budget."
        )

    else:

        status_message = (
            "✓ You are within your monthly budget."
        )

    # =====================================================
    # CONTEXT
    # =====================================================

    context = {

        "monthly_budget": monthly_budget,

        "budget_amount": monthly_budget,

        "total_spent": total_spent,

        "remaining": remaining,

        "percentage": round(
            percentage,
            1
        ),

        "progress_percentage": round(
            progress_percentage,
            1
        ),

        "current_month": current_month.strftime(
            "%B %Y"
        ),

        "status_message": status_message,
    }

    return render(
        request,
        "expenses/budget.html",
        context
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@normal_user_required
def notifications(request):

    user = request.user
    today = timezone.localdate()

    user_expenses = Expense.objects.filter(
        user=user
    )

    notification_list = []

    # =====================================================
    # NEW EXPENSE
    # =====================================================

    latest_expense = user_expenses.order_by(
        "-id"
    ).first()

    if latest_expense:

        notification_list.append({

            "type": "new",

            "title": "New Expense Added",

            "message": (
                f"₹{latest_expense.amount} expense "
                f"'{latest_expense.title}' was added."
            ),

            "date": latest_expense.date,

        })

    # =====================================================
    # HIGH EXPENSE
    # =====================================================

    high_expenses = user_expenses.filter(
        amount__gte=1000
    ).order_by(
        "-id"
    )[:5]

    for expense in high_expenses:

        notification_list.append({

            "type": "high",

            "title": "High Expense",

            "message": (
                f"You spent ₹{expense.amount} "
                f"on {expense.title}."
            ),

            "date": expense.date,

        })

    # =====================================================
    # CURRENT MONTH BUDGET
    # =====================================================

    current_month = today.replace(
        day=1
    )

    budget = Budget.objects.filter(
        user=user,
        month=current_month
    ).first()

    if budget:

        monthly_expense = user_expenses.filter(
            date__year=today.year,
            date__month=today.month
        ).aggregate(
            total=Sum("amount")
        )["total"] or 0

        budget_amount = budget.amount

        if budget_amount > 0:

            # =================================================
            # BUDGET EXCEEDED
            # =================================================

            if monthly_expense >= budget_amount:

                notification_list.append({

                    "type": "budget",

                    "title": "Budget Limit Reached",

                    "message": (
                        f"You spent ₹{monthly_expense} "
                        f"from your ₹{budget_amount} budget."
                    ),

                    "date": today,

                })

            # =================================================
            # 80% WARNING
            # =================================================

            elif monthly_expense >= (
                budget_amount * Decimal("0.80")
            ):

                notification_list.append({

                    "type": "warning",

                    "title": "Budget Warning",

                    "message": (
                        "You have used more than 80% "
                        "of your monthly budget."
                    ),

                    "date": today,

                })

    return render(
        request,
        "expenses/notifications.html",
        {
            "notifications": notification_list
        }
    )


# =========================================================
# RECURRING EXPENSES
# =========================================================

@normal_user_required
def recurring_expenses(request):

    process_recurring_expenses(user=request.user)

    expenses = Expense.objects.filter(
        user=request.user,
        is_recurring=True,
    ).order_by("next_recurring_date", "-date", "-id")

    return render(
        request,
        "expenses/recurring_expenses.html",
        {
            "expenses": expenses,
        }
    )
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views



urlpatterns = [

    # ==============================
    # DASHBOARD
    # ==============================

    path(
        "",
        views.dashboard,
        name="dashboard"
    ),


    # ==============================
    # LOGIN
    # ==============================

    path(
        "login/",
        views.login_view,
        name="login"
    ),


    # ==============================
    # REGISTER
    # ==============================

    path(
        "register/",
        views.register,
        name="register"
    ),


    # ==============================
    # LOGOUT
    # ==============================

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

    path(
        "logout/confirm/",
        views.logout_confirm,
        name="logout_confirm"
    ),


    # ==============================
    # EXPENSES
    # ==============================

    path(
        "expenses/",
        views.expenses,
        name="expenses"
    ),

    path(
        "expenses/add/",
        views.add_expense,
        name="add_expense"
    ),

    path(
        "expenses/recurring/",
        views.recurring_expenses,
        name="recurring_expenses"
    ),

    path(
        "expenses/edit/<int:expense_id>/",
        views.edit_expense,
        name="edit_expense"
    ),

    path(
        "expenses/delete/<int:expense_id>/",
        views.delete_expense,
        name="delete_expense"
    ),


    # ==============================
    # REPORTS
    # ==============================

    path(
        "reports/",
        views.reports,
        name="reports"
    ),


    # ==============================
    # PROFILE
    # ==============================

    path(
        "profile/",
        views.profile,
        name="profile"
    ),

    path(
        "profile/edit/",
        views.edit_profile,
        name="edit_profile"
    ),


    # ==============================
    # CHANGE PASSWORD
    # ==============================

    path(
        "change-password/",
        views.change_password,
        name="change_password"
    ),


    # ==============================
    # NOTIFICATIONS
    # ==============================

    path(
        "notifications/",
        views.notifications,
        name="notifications"
    ),


    # ==============================
    # BUDGET
    # ==============================

    path(
        "budget/",
        views.budget,
        name="budget"
    ),


    path(
    "forgot-password/",
    auth_views.PasswordResetView.as_view(
        template_name="expenses/forgot_password.html",
        email_template_name="expenses/password_reset_email.txt",
        subject_template_name="expenses/password_reset_subject.txt",
    ),
    name="password_reset"
),

path(
    "forgot-password/done/",
    auth_views.PasswordResetDoneView.as_view(
        template_name="expenses/password_reset_done.html"
    ),
    name="password_reset_done"
),

path(
    "reset/<uidb64>/<token>/",
    auth_views.PasswordResetConfirmView.as_view(
        template_name="expenses/password_reset_confirm.html"
    ),
    name="password_reset_confirm"
),
path(
    "expenses/export/csv/",
    views.export_csv,
    name="export_csv"
),

path(
    "reset/done/",
    auth_views.PasswordResetCompleteView.as_view(
        template_name="expenses/password_reset_complete.html"
    ),
    name="password_reset_complete"
),
path("expenses/export/csv/", views.export_csv, name="export_csv"),

path(
    "expenses/export/pdf/",
    views.export_pdf,
    name="export_pdf"
),

]

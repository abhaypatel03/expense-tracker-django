from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Budget, Expense
from .services import next_recurring_date, process_recurring_expenses


class AuthenticationSeparationTests(TestCase):
	def setUp(self):
		self.normal_user = User.objects.create_user(
			username="normal",
			password="StrongPassword123!",
		)
		self.staff_user = User.objects.create_user(
			username="staff",
			password="StrongPassword123!",
			is_staff=True,
		)
		self.admin_user = User.objects.create_superuser(
			username="admin",
			password="StrongPassword123!",
		)

	def test_normal_user_login_reaches_dashboard(self):
		response = self.client.post(
			reverse("login"),
			{"username": "normal", "password": "StrongPassword123!"},
		)

		self.assertRedirects(response, reverse("dashboard"))

	def test_staff_account_cannot_use_website_login(self):
		response = self.client.post(
			reverse("login"),
			{"username": "staff", "password": "StrongPassword123!"},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Staff accounts must use the admin login.")
		self.assertNotIn("_auth_user_id", self.client.session)

	def test_admin_is_redirected_to_admin_from_website_root(self):
		self.client.force_login(self.admin_user)

		response = self.client.get(reverse("dashboard"))

		self.assertRedirects(response, reverse("login"))

	def test_normal_user_cannot_enter_admin(self):
		self.client.force_login(self.normal_user)

		response = self.client.get(reverse("admin:index"))

		self.assertRedirects(
			response,
			f"{reverse('admin:login')}?next={reverse('admin:index')}",
		)

	def test_admin_logout_returns_to_admin_login(self):
		self.client.force_login(self.admin_user)

		response = self.client.post(reverse("admin:logout"))

		self.assertRedirects(response, reverse("admin:login"))

	def test_registration_creates_normal_user(self):
		response = self.client.post(
			reverse("register"),
			{
				"username": "new-user",
				"first_name": "New",
				"last_name": "User",
				"email": "new@example.com",
				"password1": "StrongPassword123!",
				"password2": "StrongPassword123!",
			},
		)

		self.assertRedirects(response, reverse("dashboard"))
		registered_user = User.objects.get(username="new-user")
		self.assertFalse(registered_user.is_staff)
		self.assertFalse(registered_user.is_superuser)

from .models import Budget, Expense

class ExpenseIsolationTests(TestCase):
	def test_user_sees_only_their_expenses(self):
		owner = User.objects.create_user(username="owner", password="StrongPassword123!")
		other_user = User.objects.create_user(username="other", password="StrongPassword123!")
		Expense.objects.create(
			user=owner,
			title="Visible expense",
			amount="10.00",
			category="Food",
		)
		Expense.objects.create(
			user=other_user,
			title="Hidden expense",
			amount="20.00",
			category="Travel",
		)
		self.client.force_login(owner)

		response = self.client.get(reverse("expenses"))

		self.assertContains(response, "Visible expense")
		self.assertNotContains(response, "Hidden expense")

class BudgetPageTests(TestCase):
	def setUp(self):
		self.user = User.objects.create_user(
			username="budget-user",
			password="StrongPassword123!",
		)
		self.client.force_login(self.user)

	def test_budget_page_creates_current_month_budget(self):
		response = self.client.get(reverse("budget"))
		current_month = date.today().replace(day=1)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(
			Budget.objects.get(user=self.user, month=current_month).amount,
			Decimal("0.00"),
		)

	def test_budget_page_saves_current_month_budget(self):
		response = self.client.post(
			reverse("budget"),
			{"budget_amount": "25000.50"},
		)
		current_month = date.today().replace(day=1)

		self.assertRedirects(response, reverse("budget"))
		self.assertEqual(
			Budget.objects.get(user=self.user, month=current_month).amount,
			Decimal("25000.50"),
		)


class ExpenseEditDeleteTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user(
			username="expense-owner",
			password="StrongPassword123!",
		)
		self.other_user = User.objects.create_user(
			username="expense-other",
			password="StrongPassword123!",
		)
		self.expense = Expense.objects.create(
			user=self.owner,
			title="Lunch",
			amount="100.00",
			category="Food",
			date=date.today(),
		)

	def test_owner_can_edit_expense(self):
		self.client.force_login(self.owner)

		response = self.client.post(
			reverse("edit_expense", args=[self.expense.id]),
			{
				"title": "Dinner",
				"amount": "250.00",
				"category": "Food",
				"date": date.today().isoformat(),
			},
		)

		self.assertRedirects(response, reverse("expenses"))
		self.expense.refresh_from_db()
		self.assertEqual(self.expense.title, "Dinner")
		self.assertEqual(self.expense.amount, Decimal("250.00"))

	def test_delete_requires_confirmation_then_deletes_on_post(self):
		self.client.force_login(self.owner)
		delete_url = reverse("delete_expense", args=[self.expense.id])

		response = self.client.get(delete_url)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Delete Expense?")
		self.assertTrue(Expense.objects.filter(id=self.expense.id).exists())

		response = self.client.post(delete_url)
		self.assertRedirects(response, reverse("expenses"))
		self.assertFalse(Expense.objects.filter(id=self.expense.id).exists())

	def test_user_cannot_edit_or_delete_another_users_expense(self):
		self.client.force_login(self.other_user)
		edit_url = reverse("edit_expense", args=[self.expense.id])
		delete_url = reverse("delete_expense", args=[self.expense.id])

		self.assertEqual(self.client.get(edit_url).status_code, 404)
		self.assertEqual(self.client.get(delete_url).status_code, 404)
		self.assertTrue(Expense.objects.filter(id=self.expense.id).exists())

	def test_user_data_endpoints_do_not_expose_another_users_expenses(self):
		Expense.objects.create(
			user=self.other_user,
			title="Private expense",
			amount="900.00",
			category="Bills",
			date=date.today(),
		)
		self.client.force_login(self.owner)

		for url_name in (
			"dashboard",
			"expenses",
			"recurring_expenses",
			"reports",
			"notifications",
			"export_csv",
		):
			response = self.client.get(reverse(url_name))
			self.assertNotContains(response, "Private expense")

		pdf_response = self.client.get(reverse("export_pdf"))
		self.assertNotIn(b"Private expense", pdf_response.content)


class ReportsPageTests(TestCase):
	def test_reports_show_current_user_data_and_budget_progress(self):
		user = User.objects.create_user(
			username="reports-user",
			password="StrongPassword123!",
		)
		today = date.today()
		Expense.objects.create(
			user=user,
			title="Groceries",
			amount="250.00",
			category="Food",
			date=today,
		)
		Budget.objects.create(
			user=user,
			month=today.replace(day=1),
			amount="1000.00",
		)
		self.client.force_login(user)

		response = self.client.get(reverse("reports"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Food")
		self.assertContains(response, "₹250.00")
		self.assertEqual(response.context["budget_percentage"], Decimal("25"))


class RecurringExpenseTests(TestCase):
	def setUp(self):
		self.owner = User.objects.create_user(
			username="recurring-owner",
			password="StrongPassword123!",
		)
		self.other_user = User.objects.create_user(
			username="recurring-other",
			password="StrongPassword123!",
		)

	def test_normal_expense_clears_recurring_fields(self):
		from .forms import ExpenseForm

		form = ExpenseForm({
			"title": "Lunch",
			"amount": "100.00",
			"category": "Food",
			"date": "2026-09-16",
			"is_recurring": "",
			"recurring_frequency": "monthly",
			"next_recurring_date": "2026-10-16",
		})

		self.assertTrue(form.is_valid())
		self.assertIsNone(form.cleaned_data["recurring_frequency"])
		self.assertIsNone(form.cleaned_data["next_recurring_date"])

	def test_recurring_page_is_user_scoped(self):
		Expense.objects.create(
			user=self.owner,
			title="Owner subscription",
			amount="499.00",
			category="Entertainment",
			is_recurring=True,
			recurring_frequency="monthly",
			next_recurring_date=date(2026, 10, 5),
		)
		Expense.objects.create(
			user=self.other_user,
			title="Other subscription",
			amount="299.00",
			category="Entertainment",
			is_recurring=True,
			recurring_frequency="monthly",
			next_recurring_date=date(2026, 10, 6),
		)

		self.client.force_login(self.owner)
		response = self.client.get(reverse("recurring_expenses"))

		self.assertContains(response, "Owner subscription")
		self.assertNotContains(response, "Other subscription")

	def test_processing_handles_month_end_and_is_idempotent(self):
		source = Expense.objects.create(
			user=self.owner,
			title="Month end subscription",
			amount="50.00",
			category="Bills",
			date=date(2026, 1, 31),
			is_recurring=True,
			recurring_frequency="monthly",
			next_recurring_date=date(2026, 2, 28),
		)

		self.assertEqual(next_recurring_date(date(2026, 1, 31), "monthly"), date(2026, 2, 28))
		self.assertEqual(process_recurring_expenses(date(2026, 2, 28)), 1)
		self.assertEqual(
			Expense.objects.filter(
				user=self.owner,
				title="Month end subscription",
				date=date(2026, 2, 28),
			).count(),
			1,
		)
		source.refresh_from_db()
		self.assertEqual(source.next_recurring_date, date(2026, 3, 28))
		self.assertEqual(process_recurring_expenses(date(2026, 2, 28)), 0)

	def test_management_command_twice_creates_one_occurrence(self):
		due_date = date.today() - timedelta(days=1)
		Expense.objects.create(
			user=self.owner,
			title="Streaming plan",
			amount="499.00",
			category="Entertainment",
			date=due_date - timedelta(days=1),
			is_recurring=True,
			recurring_frequency="monthly",
			next_recurring_date=due_date,
		)

		call_command("process_recurring", verbosity=0)
		call_command("process_recurring", verbosity=0)

		self.assertEqual(
			Expense.objects.filter(
				user=self.owner,
				title="Streaming plan",
				date=due_date,
			).count(),
			1,
		)

	def test_owner_can_edit_all_recurring_fields(self):
		expense = Expense.objects.create(
			user=self.owner,
			title="Old subscription",
			amount="100.00",
			category="Bills",
			date=date(2026, 9, 1),
			is_recurring=True,
			recurring_frequency="monthly",
			next_recurring_date=date(2026, 10, 1),
		)
		self.client.force_login(self.owner)

		response = self.client.post(
			reverse("edit_expense", args=[expense.id]),
			{
				"title": "Updated subscription",
				"amount": "250.00",
				"category": "Entertainment",
				"date": "2026-09-05",
				"description": "Updated details",
				"is_recurring": "on",
				"recurring_frequency": "weekly",
				"next_recurring_date": "2026-09-20",
			},
		)

		self.assertRedirects(response, reverse("expenses"))
		expense.refresh_from_db()
		self.assertEqual(expense.title, "Updated subscription")
		self.assertEqual(expense.amount, Decimal("250.00"))
		self.assertEqual(expense.recurring_frequency, "weekly")
		self.assertEqual(expense.next_recurring_date, date(2026, 9, 20))

	def test_normal_expense_post_saves_without_recurring_fields(self):
		self.client.force_login(self.owner)

		response = self.client.post(
			reverse("add_expense"),
			{
				"title": "One-time lunch",
				"amount": "120.00",
				"category": "Food",
				"date": "2026-09-16",
				"description": "Normal expense",
				"is_recurring": "",
				"recurring_frequency": "",
				"next_recurring_date": "",
			},
		)

		self.assertRedirects(response, reverse("expenses"))
		expense = Expense.objects.get(title="One-time lunch")
		self.assertFalse(expense.is_recurring)
		self.assertIsNone(expense.recurring_frequency)
		self.assertIsNone(expense.next_recurring_date)

	def test_recurring_delete_uses_confirmation_then_deletes(self):
		expense = Expense.objects.create(
			user=self.owner,
			title="Recurring to delete",
			amount="80.00",
			category="Bills",
			is_recurring=True,
			recurring_frequency="monthly",
			next_recurring_date=date(2026, 10, 1),
		)
		self.client.force_login(self.owner)
		delete_url = reverse("delete_expense", args=[expense.id])

		self.assertEqual(self.client.get(delete_url).status_code, 200)
		self.assertContains(self.client.get(delete_url), "Delete Expense?")
		response = self.client.post(delete_url)

		self.assertRedirects(response, reverse("expenses"))
		self.assertFalse(Expense.objects.filter(id=expense.id).exists())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PasswordResetTests(TestCase):
	def test_registered_email_receives_reset_link(self):
		user = User.objects.create_user(
			username="ajaypatel09",
			email="ssupabhay@gmail.com",
			password="OldPassword123!",
		)

		response = self.client.post(
			reverse("password_reset"),
			{"email": "ssupabhay@gmail.com"},
		)

		self.assertRedirects(response, reverse("password_reset_done"))
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn("/reset/", mail.outbox[0].body)
		self.assertIn(user.email, mail.outbox[0].to)

# Create your tests here.

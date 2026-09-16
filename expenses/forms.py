from django import forms
from django.contrib.auth.models import User

from .models import Expense


# =========================================================
# EXPENSE FORM
# =========================================================

class ExpenseForm(forms.ModelForm):

    class Meta:
        model = Expense

        fields = [
            "title",
            "amount",
            "category",
            "date",
            "description",
            "is_recurring",
            "recurring_frequency",
            "next_recurring_date",
        ]

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "placeholder": "Enter expense title"
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "placeholder": "Enter amount",
                    "min": "0.01",
                    "step": "0.01"
                }
            ),

            "category": forms.TextInput(
                attrs={
                    "placeholder": "Enter category"
                }
            ),

            "date": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "placeholder": "Enter description",
                    "rows": 4
                }
            ),

            "is_recurring": forms.CheckboxInput(),

            "recurring_frequency": forms.Select(),

            "next_recurring_date": forms.DateInput(
                attrs={
                    "type": "date"
                }
            ),
        }

    def clean_amount(self):

        amount = self.cleaned_data.get("amount")

        if amount is None:
            raise forms.ValidationError(
                "Amount is required."
            )

        if amount <= 0:
            raise forms.ValidationError(
                "Amount must be greater than 0."
            )

        if amount > 10000000:
            raise forms.ValidationError(
                "Amount is too large."
            )

        return amount

    def clean(self):

        cleaned_data = super().clean()

        is_recurring = cleaned_data.get("is_recurring")
        recurring_frequency = cleaned_data.get("recurring_frequency")
        next_recurring_date = cleaned_data.get("next_recurring_date")

        if is_recurring:

            if not recurring_frequency:
                self.add_error(
                    "recurring_frequency",
                    "Select a recurring frequency."
                )

            if not next_recurring_date:
                self.add_error(
                    "next_recurring_date",
                    "Enter the next recurring date."
                )

        else:
            cleaned_data["recurring_frequency"] = None
            cleaned_data["next_recurring_date"] = None

        return cleaned_data


# =========================================================
# REGISTER FORM
# =========================================================

class RegisterForm(forms.ModelForm):

    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter password"
            }
        )
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm password"
            }
        )
    )

    class Meta:

        model = User

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
        ]

        widgets = {

            "username": forms.TextInput(
                attrs={
                    "placeholder": "Enter username"
                }
            ),

            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "First name"
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Last name"
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Email address"
                }
            ),
        }

    def clean_email(self):

        email = self.cleaned_data.get("email")

        if not email:
            raise forms.ValidationError(
                "Email is required."
            )

        email = email.strip().lower()

        if User.objects.filter(
            email=email
        ).exists():

            raise forms.ValidationError(
                "This email is already registered."
            )

        return email

    def clean_first_name(self):

        first_name = self.cleaned_data.get(
            "first_name"
        )

        if not first_name:
            raise forms.ValidationError(
                "First name is required."
            )

        if not first_name.replace(
            " ", ""
        ).isalpha():

            raise forms.ValidationError(
                "First name can contain only letters."
            )

        return first_name.strip()

    def clean_last_name(self):

        last_name = self.cleaned_data.get(
            "last_name"
        )

        if not last_name:
            raise forms.ValidationError(
                "Last name is required."
            )

        if not last_name.replace(
            " ", ""
        ).isalpha():

            raise forms.ValidationError(
                "Last name can contain only letters."
            )

        return last_name.strip()

    def clean(self):

        cleaned_data = super().clean()

        password1 = cleaned_data.get(
            "password1"
        )

        password2 = cleaned_data.get(
            "password2"
        )

        if password1 and password2:

            if password1 != password2:

                raise forms.ValidationError(
                    "Passwords do not match."
                )

        return cleaned_data

    def save(self, commit=True):

        user = super().save(
            commit=False
        )

        user.set_password(
            self.cleaned_data["password1"]
        )

        if commit:
            user.save()

        return user


# =========================================================
# PROFILE FORM
# =========================================================

class ProfileForm(forms.ModelForm):

    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter first name"
            }
        )
    )

    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter last name"
            }
        )
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter email address"
            }
        )
    )

    class Meta:

        model = User

        fields = [
            "first_name",
            "last_name",
            "email",
        ]

    # -----------------------------------------
    # FIRST NAME
    # -----------------------------------------

    def clean_first_name(self):

        first_name = self.cleaned_data.get(
            "first_name"
        )

        if not first_name:
            raise forms.ValidationError(
                "First name is required."
            )

        if not first_name.replace(
            " ", ""
        ).isalpha():

            raise forms.ValidationError(
                "First name can contain only letters."
            )

        return first_name.strip()

    # -----------------------------------------
    # LAST NAME
    # -----------------------------------------

    def clean_last_name(self):

        last_name = self.cleaned_data.get(
            "last_name"
        )

        if not last_name:
            raise forms.ValidationError(
                "Last name is required."
            )

        if not last_name.replace(
            " ", ""
        ).isalpha():

            raise forms.ValidationError(
                "Last name can contain only letters."
            )

        return last_name.strip()

    # -----------------------------------------
    # EMAIL
    # -----------------------------------------

    def clean_email(self):

        email = self.cleaned_data.get(
            "email"
        )

        if not email:
            raise forms.ValidationError(
                "Email is required."
            )

        email = email.strip().lower()

        if User.objects.filter(
            email=email
        ).exclude(
            pk=self.instance.pk
        ).exists():

            raise forms.ValidationError(
                "This email is already being used."
            )

        return email
from decimal import Decimal
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction
from .models import Business, Customer, Quote, Invoice, Payment, Expense


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)
    business_name = forms.CharField(max_length=140, label="Business name")
    sector = forms.ChoiceField(choices=Business.SECTORS)

    class Meta:
        model = User
        fields = ["username", "email", "business_name", "sector", "password1", "password2"]

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.email = self.cleaned_data["email"]
            user.save(update_fields=["email"])
            Business.objects.create(owner=user, name=self.cleaned_data["business_name"], sector=self.cleaned_data["sector"])
        return user


class StyledFormMixin:
    def style_fields(self):
        for field in self.fields.values():
            field.widget.attrs["class"] = (field.widget.attrs.get("class", "") + " form-control").strip()


class BusinessForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Business
        fields = ["name", "sector", "region", "town", "phone", "email", "registration_status", "has_business_bank_account"]
        widgets = {"has_business_bank_account": forms.CheckboxInput(attrs={"class": "form-check-input"})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.style_fields()


class CustomerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "contact_name", "email", "phone", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.style_fields()


class QuoteForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Quote
        fields = ["customer", "description", "amount", "issue_date", "valid_until", "status"]
        widgets = {"issue_date": forms.DateInput(attrs={"type": "date"}), "valid_until": forms.DateInput(attrs={"type": "date"})}
    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs); self.style_fields()
        if business: self.fields["customer"].queryset = Customer.objects.filter(business=business)


class InvoiceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ["customer", "description", "amount", "issue_date", "due_date"]
        widgets = {"issue_date": forms.DateInput(attrs={"type": "date"}), "due_date": forms.DateInput(attrs={"type": "date"})}
    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs); self.style_fields()
        if business: self.fields["customer"].queryset = Customer.objects.filter(business=business)


class PaymentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "payment_date", "method", "reference"]
        widgets = {"payment_date": forms.DateInput(attrs={"type": "date"})}
    def __init__(self, *args, invoice=None, **kwargs):
        super().__init__(*args, **kwargs); self.style_fields(); self.invoice = invoice
    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if self.invoice and amount > self.invoice.balance:
            raise forms.ValidationError(f"The payment cannot exceed the remaining balance of R {self.invoice.balance:,.2f}.")
        return amount


class ExpenseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["description", "category", "amount", "expense_date", "due_date", "is_paid"]
        widgets = {"expense_date": forms.DateInput(attrs={"type": "date"}), "due_date": forms.DateInput(attrs={"type": "date"}), "is_paid": forms.CheckboxInput(attrs={"class": "form-check-input"})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self.style_fields()


from .models import BusinessUpdate


class BusinessUpdateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = BusinessUpdate
        fields = [
            "business",
            "title",
            "category",
            "priority",
            "status",
            "body",
            "follow_up_date",
            "visible_to_business",
        ]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
            "visible_to_business": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()
        self.fields["business"].queryset = Business.objects.order_by("name")
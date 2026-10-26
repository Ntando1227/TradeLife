from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .forms import SignUpForm, BusinessForm, CustomerForm, QuoteForm, InvoiceForm, PaymentForm, ExpenseForm
from .models import Business, Customer, Quote, Invoice, Payment, Expense, Opportunity
from .services import cash_forecast, readiness, opportunity_match


def signup(request):
    if request.user.is_authenticated: return redirect("dashboard")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(); login(request, user); return redirect("dashboard")
    return render(request, "registration/signup.html", {"form": form})


def home(request):
    return redirect("dashboard") if request.user.is_authenticated else redirect("login")


def owned_business(user):
    from django.http import Http404
    from .models import Business, BusinessMember

    business = Business.objects.filter(owner=user).first()
    if business:
        return business

    membership = (
        BusinessMember.objects
        .filter(user=user)
        .select_related("business")
        .first()
    )
    if membership:
        return membership.business

    raise Http404("This account is not linked to a business.")

def next_reference(queryset, prefix):
    return f"{prefix}-{timezone.localdate():%y%m%d}-{queryset.count() + 1:03d}"


@login_required
def quote_list(request):
    return render(request, "core/quote_list.html", {"quotes": owned_business(request.user).quotes.select_related("customer")})


@login_required
def quote_detail(request, quote_id):
    quote = get_object_or_404(Quote.objects.select_related("business", "customer"), pk=quote_id, business__owner=request.user)
    return render(request, "core/quote_document.html", {"quote": quote})


@login_required
def quote_create(request):
    business = owned_business(request.user); form = QuoteForm(request.POST or None, business=business)
    if request.method == "POST" and form.is_valid():
        quote = form.save(commit=False); quote.business = business; quote.reference = next_reference(business.quotes, "Q"); quote.save(); messages.success(request, f"Quotation {quote.reference} created."); return redirect("quote_list")
    return render(request, "core/form_page.html", {"form": form, "title": "Create quotation", "subtitle": "A single total is used in this starter version. You can add line items as a next improvement."})


@login_required
@require_POST
@transaction.atomic
def quote_to_invoice(request, quote_id):
    business = owned_business(request.user); quote = get_object_or_404(Quote.objects.select_for_update(), pk=quote_id, business=business)
    if hasattr(quote, "invoice"):
        messages.info(request, "This quotation already has an invoice."); return redirect("invoice_list")
    invoice = Invoice.objects.create(business=business, customer=quote.customer, quote=quote, reference=next_reference(business.invoices, "INV"), description=quote.description, amount=quote.amount, due_date=timezone.localdate() + timedelta(days=14))
    quote.status = "invoiced"; quote.save(update_fields=["status"]); messages.success(request, f"Invoice {invoice.reference} created with a 14-day due date."); return redirect("invoice_list")


@login_required
def invoice_list(request):
    business = owned_business(request.user)
    return render(request, "core/invoice_list.html", {"invoices": business.invoices.select_related("customer").prefetch_related("payments")})


@login_required
def invoice_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice.objects.select_related("business", "customer").prefetch_related("payments"), pk=invoice_id, business__owner=request.user)
    return render(request, "core/invoice_document.html", {"invoice": invoice})


@login_required
def invoice_create(request):
    business = owned_business(request.user); form = InvoiceForm(request.POST or None, business=business)
    if request.method == "POST" and form.is_valid():
        invoice = form.save(commit=False); invoice.business = business; invoice.reference = next_reference(business.invoices, "INV"); invoice.save(); messages.success(request, f"Invoice {invoice.reference} created."); return redirect("invoice_list")
    return render(request, "core/form_page.html", {"form": form, "title": "Create invoice"})


@login_required
@transaction.atomic
def payment_create(request, invoice_id):
    business = owned_business(request.user); invoice = get_object_or_404(Invoice.objects.select_for_update().prefetch_related("payments"), pk=invoice_id, business=business)
    if invoice.balance <= 0: messages.info(request, "This invoice is already fully paid."); return redirect("invoice_list")
    form = PaymentForm(request.POST or None, invoice=invoice)
    if request.method == "POST" and form.is_valid():
        payment = form.save(commit=False); payment.business = business; payment.invoice = invoice; payment.save(); invoice.refresh_from_db(); messages.success(request, f"Payment recorded. Remaining balance: R {invoice.balance:,.2f}."); return redirect("invoice_list")
    return render(request, "core/form_page.html", {"form": form, "title": f"Record payment for {invoice.reference}", "subtitle": f"Remaining invoice balance: R {invoice.balance:,.2f}. This records a payment; it does not move money."})


@login_required
def expense_list(request):
    return render(request, "core/expense_list.html", {"expenses": owned_business(request.user).expenses.all()})


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        expense = form.save(commit=False); expense.business = owned_business(request.user); expense.save(); messages.success(request, "Expense recorded."); return redirect("expense_list")
    return render(request, "core/form_page.html", {"form": form, "title": "Record expense"})


@login_required
def forecast_page(request):
    business = owned_business(request.user); forecast = cash_forecast(business)
    return render(request, "core/forecast.html", {"forecast": forecast, "invoices": business.invoices.select_related("customer").prefetch_related("payments"), "expenses": business.expenses.filter(is_paid=False).order_by("due_date")})


@login_required
def opportunity_list(request):
    business = owned_business(request.user); opportunities = Opportunity.objects.filter(is_active=True)
    matches = [(item, opportunity_match(business, item)) for item in opportunities]
    return render(request, "core/opportunities.html", {"matches": matches, "business": business})

from django.contrib.auth.decorators import login_required

@login_required
def business_profile(request):
    from django.contrib import messages
    from django.forms import modelform_factory
    from django.shortcuts import redirect, render
    from .models import Business

    business = Business.objects.filter(owner=request.user).first()
    BusinessForm = modelform_factory(Business, exclude=("owner",))

    if request.method == "POST":
        form = BusinessForm(request.POST, instance=business)
        if form.is_valid():
            saved_business = form.save(commit=False)
            saved_business.owner = request.user
            saved_business.save()
            form.save_m2m()
            messages.success(request, "Business profile saved.")
            return redirect("business_profile")
    else:
        form = BusinessForm(instance=business)

    return render(
        request,
        "core/business_profile_form.html",
        {
            "form": form,
            "business": business,
        },
    )

from django.contrib.auth.decorators import login_required

@login_required
def readiness_page(request):
    from django.shortcuts import render
    from .models import Business

    business = Business.objects.filter(owner=request.user).first()
    missing_fields = []
    checked_fields = []

    if business:
        excluded = {"id", "owner", "created_at", "updated_at"}
        for model_field in business._meta.fields:
            if model_field.name in excluded or model_field.auto_created:
                continue

            value = getattr(business, model_field.name, None)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(model_field.verbose_name.title())
            else:
                checked_fields.append(model_field.verbose_name.title())

    total_fields = len(missing_fields) + len(checked_fields)
    completion = round((len(checked_fields) / total_fields) * 100) if total_fields else 0

    return render(
        request,
        "core/readiness.html",
        {
            "business": business,
            "missing_fields": missing_fields,
            "completion": completion,
        },
    )


@login_required
def forecast_page(request):
    from decimal import Decimal, InvalidOperation
    from django.apps import apps
    from django.shortcuts import render
    from .models import Business

    business = Business.objects.filter(owner=request.user).first()

    def recorded_total(model_name, amount_names):
        if not business:
            return Decimal("0.00")

        try:
            model = apps.get_model("core", model_name)
        except LookupError:
            return Decimal("0.00")

        model_field_names = {field.name for field in model._meta.get_fields()}

        if "business" in model_field_names:
            records = model.objects.filter(business=business)
        elif "owner" in model_field_names:
            records = model.objects.filter(owner=request.user)
        else:
            return Decimal("0.00")

        amount_field = next(
            (name for name in amount_names if name in model_field_names),
            None,
        )
        if not amount_field:
            return Decimal("0.00")

        total = Decimal("0.00")
        for record in records.only(amount_field):
            value = getattr(record, amount_field, None)
            try:
                total += Decimal(str(value or "0"))
            except (InvalidOperation, TypeError, ValueError):
                continue
        return total

    invoice_total = recorded_total(
        "Invoice",
        ("total", "total_amount", "grand_total", "amount", "amount_due"),
    )
    expense_total = recorded_total(
        "Expense",
        ("amount", "total", "total_amount", "cost"),
    )

    return render(
        request,
        "core/forecast.html",
        {
            "business": business,
            "invoice_total": invoice_total,
            "expense_total": expense_total,
            "recorded_difference": invoice_total - expense_total,
        },
    )


# TRADELIFE_RESTORED_CRUD_HELPERS_V1
from django.contrib.auth.decorators import login_required

def _tradelife_business(request):
    from .models import Business
    return Business.objects.filter(owner=request.user).first()

def _tradelife_rows_page(request, title, description, columns, rows, add_url):
    from django.shortcuts import render
    return render(
        request,
        "core/tradelife_records.html",
        {
            "title": title,
            "description": description,
            "columns": columns,
            "rows": rows,
            "add_url": add_url,
        },
    )

def _tradelife_form_page(request, title, description, form, cancel_url):
    from django.shortcuts import render
    return render(
        request,
        "core/tradelife_form.html",
        {
            "title": title,
            "description": description,
            "form": form,
            "cancel_url": cancel_url,
        },
    )

def _tradelife_reference(prefix):
    from uuid import uuid4
    return prefix + "-" + uuid4().hex[:12].upper()
@login_required
def customer_list(request):
    from django.shortcuts import redirect
    business = _tradelife_business(request)
    if not business:
        return redirect("business_profile")

    customers = business.customers.all()
    rows = [
        {
            "cells": [
                customer.name,
                customer.contact_name or "Not provided",
                customer.phone or "Not provided",
                customer.email or "Not provided",
            ],
            "url": "",
        }
        for customer in customers
    ]
    return _tradelife_rows_page(
        request,
        "Customers",
        "Keep customer contact details together for quotes and follow-ups.",
        ["Customer", "Contact person", "Phone", "Email"],
        rows,
        "/customers/new/",
    )

@login_required
def customer_create(request):
    from django.forms import modelform_factory
    from django.shortcuts import redirect
    from .models import Customer

    business = _tradelife_business(request)
    if not business:
        return redirect("business_profile")

    CustomerForm = modelform_factory(
        Customer,
        fields=("name", "contact_name", "phone", "email", "notes"),
    )
    form = CustomerForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        customer = form.save(commit=False)
        customer.business = business
        customer.save()
        return redirect("customer_list")

    return _tradelife_form_page(
        request,
        "Add customer",
        "Save the details you need to prepare quotes and contact this customer.",
        form,
        "/customers/",
    )
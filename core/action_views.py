from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.utils import timezone

from .models import Business, BusinessUpdate, Customer, Expense, Invoice, Quote


@login_required
def action_centre(request):
    is_admin = request.user.is_staff
    today = timezone.localdate()
    seven_days = today + timedelta(days=7)
    thirty_days = today + timedelta(days=30)

    business = None
    setup_needed = False

    if is_admin:
        customers = Customer.objects.select_related("business").all()
        quotes = Quote.objects.select_related("business", "customer").all()
        invoices = Invoice.objects.select_related("business", "customer").all()
        expenses = Expense.objects.select_related("business").all()
        updates = BusinessUpdate.objects.select_related("business").all()
    else:
        business = Business.objects.filter(owner=request.user).first()
        setup_needed = business is None

        if business:
            customers = Customer.objects.filter(business=business)
            quotes = Quote.objects.filter(business=business).select_related("customer")
            invoices = Invoice.objects.filter(business=business).select_related("customer")
            expenses = Expense.objects.filter(business=business)
            updates = BusinessUpdate.objects.filter(business=business)
        else:
            customers = Customer.objects.none()
            quotes = Quote.objects.none()
            invoices = Invoice.objects.none()
            expenses = Expense.objects.none()
            updates = BusinessUpdate.objects.none()

    actions = []
    expected_receipts = Decimal("0.00")
    expected_expenses = Decimal("0.00")

    def add_action(priority, category, title, detail, due_date=None, link=None):
        actions.append({
            "priority": priority,
            "category": category,
            "title": title,
            "detail": detail,
            "due_date": due_date,
            "link": link,
        })

    if not setup_needed:
        for customer in customers.order_by("-created_at")[:100]:
            if customer.created_at.date() >= today - timedelta(days=7):
                detail = customer.name
                if is_admin:
                    detail += f" · {customer.business.name}"
                add_action(
                    "Normal",
                    "New customer",
                    "Follow up with a recently added customer",
                    detail,
                    customer.created_at.date(),
                    "/office/customers/" if is_admin else "/customers/",
                )

        for quote in quotes.order_by("valid_until", "-id")[:500]:
            status = quote.status
            reference = quote.reference
            detail = quote.customer.name
            if is_admin:
                detail += f" · {quote.business.name}"

            if status in {"accepted", "declined", "invoiced"}:
                continue

            if quote.valid_until and quote.valid_until < today:
                add_action(
                    "High", "Expired quotation", f"{reference} has expired",
                    f"{detail} · Review or issue an updated quotation.",
                    quote.valid_until, "/quotes/manage/",
                )
            elif quote.valid_until and quote.valid_until <= seven_days:
                add_action(
                    "High", "Quotation expiring", f"{reference} is nearing expiry",
                    f"{detail} · Follow up before the validity date.",
                    quote.valid_until, "/quotes/manage/",
                )
            elif status == "sent":
                add_action(
                    "Normal", "Quotation follow-up", f"Check the response to {reference}",
                    f"{detail} · The quotation is marked as sent.",
                    quote.valid_until, "/quotes/manage/",
                )

        invoice_queryset = invoices.annotate(
            paid_total=Coalesce(
                Sum("payments__amount"),
                Decimal("0.00"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        )

        for invoice in invoice_queryset.order_by("due_date", "-id")[:500]:
            outstanding = max(Decimal("0.00"), invoice.amount - invoice.paid_total)
            if outstanding <= 0:
                continue

            detail = f"Outstanding: R {outstanding:,.2f} · {invoice.customer.name}"
            if is_admin:
                detail += f" · {invoice.business.name}"

            if invoice.due_date < today:
                add_action(
                    "High", "Overdue invoice", f"{invoice.reference} is overdue",
                    detail, invoice.due_date, "/invoices/",
                )
            elif invoice.due_date <= seven_days:
                add_action(
                    "High", "Invoice due soon", f"{invoice.reference} is due soon",
                    detail, invoice.due_date, "/invoices/",
                )

            if today <= invoice.due_date <= thirty_days:
                expected_receipts += outstanding

        for expense in expenses.filter(is_paid=False).exclude(due_date__isnull=True).order_by("due_date")[:500]:
            if today <= expense.due_date <= thirty_days:
                expected_expenses += expense.amount

            if expense.due_date <= seven_days:
                detail = f"{expense.description} · R {expense.amount:,.2f}"
                if is_admin:
                    detail += f" · {expense.business.name}"

                add_action(
                    "Normal", "Upcoming expense", "Review an unpaid expense",
                    detail, expense.due_date, "/expenses/",
                )

        for update in updates.filter(
            status__in=["open", "in_progress"],
            follow_up_date__isnull=False,
            follow_up_date__lte=seven_days,
        ).order_by("follow_up_date")[:100]:
            detail = update.body[:180]
            if is_admin:
                detail = f"{update.business.name} · {detail}"

            add_action(
                "High" if update.priority == "high" else "Normal",
                "Business update",
                update.title,
                detail,
                update.follow_up_date,
                "/office/updates/" if is_admin else "/updates/",
            )

    priority_order = {"High": 0, "Normal": 1, "Low": 2}
    actions.sort(key=lambda item: (
        priority_order.get(item["priority"], 3),
        item["due_date"] or today + timedelta(days=3650),
    ))

    return render(request, "core/action_centre.html", {
        "business": business,
        "is_admin": is_admin,
        "setup_needed": setup_needed,
        "actions": actions,
        "action_count": len(actions),
        "expected_receipts": expected_receipts,
        "expected_expenses": expected_expenses,
        "expected_net": expected_receipts - expected_expenses,
        "forecast_available": not setup_needed,
    })
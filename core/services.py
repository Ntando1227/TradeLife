from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone


def readiness(business):
    checks = [
        ("Business profile has a name and sector", bool(business.name and business.sector)),
        ("Contact details are recorded", bool(business.phone or business.email)),
        ("Business registration status is recorded", business.registration_status == "registered"),
        ("A business bank account is recorded", business.has_business_bank_account),
        ("At least one customer is recorded", business.customers.exists()),
        ("At least one invoice is recorded", business.invoices.exists()),
        ("At least one payment or expense is recorded", business.payments.exists() or business.expenses.exists()),
    ]
    complete = sum(1 for _, done in checks if done)
    score = round(complete / len(checks) * 100)
    return {"score": score, "checks": checks, "complete": complete, "total": len(checks)}


def cash_forecast(business, days=30):
    today = timezone.localdate()
    end = today + timedelta(days=days)
    invoices = business.invoices.filter(due_date__gte=today, due_date__lte=end).select_related("customer").prefetch_related("payments")
    invoice_balances = [invoice.balance for invoice in invoices]
    expected_in = sum(invoice_balances, Decimal("0.00"))
    expected_out = business.expenses.filter(is_paid=False, due_date__gte=today, due_date__lte=end).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    overdue = sum((invoice.balance for invoice in business.invoices.filter(due_date__lt=today).prefetch_related("payments")), Decimal("0.00"))
    net = expected_in - expected_out
    return {"expected_in": expected_in, "expected_out": expected_out, "net": net, "overdue": overdue, "days": days, "invoice_count": sum(1 for balance in invoice_balances if balance > 0)}


def opportunity_match(business, opportunity):
    reasons = []
    if opportunity.sector and opportunity.sector.lower() != business.sector.lower():
        reasons.append("Sector does not match")
    if opportunity.region and business.region and opportunity.region.lower() not in business.region.lower():
        reasons.append("Region may not match")
    return {"matches": not reasons, "reasons": reasons}

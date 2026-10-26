from datetime import date
from calendar import month_name

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Business, Customer, Quote
from .views import owned_business


def _six_month_chart(quotes):
    today = date.today()
    months = []

    for offset in range(5, -1, -1):
        month_number = today.month - offset
        year = today.year

        while month_number <= 0:
            month_number += 12
            year -= 1

        count = 0
        for quote in quotes:
            issue_date = getattr(quote, "issue_date", None)
            if issue_date and issue_date.year == year and issue_date.month == month_number:
                count += 1

        months.append({
            "label": month_name[month_number][:3],
            "count": count,
        })

    maximum = max([month["count"] for month in months] or [0])
    for month in months:
        month["height"] = max(5, round((month["count"] / maximum) * 100)) if maximum else 5

    return months


def _status_summary(quotes):
    counts = {}

    for quote in quotes:
        try:
            label = quote.get_status_display()
        except Exception:
            label = str(getattr(quote, "status", "Unspecified")).replace("_", " ").title()

        counts[label] = counts.get(label, 0) + 1

    total = len(quotes)
    result = []

    for label, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        percent = round((count / total) * 100) if total else 0
        result.append({
            "label": label,
            "count": count,
            "percent": percent,
        })

    return result


@login_required
def summary_dashboard(request):
    business = owned_business(request.user)
    customers = Customer.objects.filter(business=business).order_by("-created_at")
    quote_records = list(
        Quote.objects.filter(business=business)
        .select_related("customer")
        .order_by("-issue_date", "-id")
    )

    return render(request, "core/summary_dashboard.html", {
        "business": business,
        "customer_count": customers.count(),
        "quote_count": len(quote_records),
        "recent_customers": customers[:6],
        "recent_quotes": quote_records[:6],
        "quote_statuses": _status_summary(quote_records),
        "monthly_activity": _six_month_chart(quote_records),
    })


@staff_member_required
def office_dashboard(request):
    businesses = Business.objects.select_related("owner").order_by("-created_at")
    customers = Customer.objects.select_related("business").order_by("-created_at")
    quote_records = list(
        Quote.objects.select_related("business", "customer")
        .order_by("-issue_date", "-id")
    )

    return render(request, "core/office_dashboard.html", {
        "business_count": businesses.count(),
        "customer_count": customers.count(),
        "quote_count": len(quote_records),
        "businesses": businesses[:8],
        "recent_customers": customers[:12],
        "recent_quotes": quote_records[:8],
        "quote_statuses": _status_summary(quote_records),
        "monthly_activity": _six_month_chart(quote_records),
    })
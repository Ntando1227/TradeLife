from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Business, Customer, Quote
from .forms import QuoteForm
from .views import owned_business


@login_required
def summary_dashboard(request):
    """Overview for the signed-in business owner."""
    business = owned_business(request.user)

    customers = Customer.objects.filter(business=business)
    quotes = Quote.objects.filter(business=business)

    context = {
        "business": business,
        "customer_count": customers.count(),
        "quote_count": quotes.count(),
        "recent_customers": customers.order_by("-created_at")[:8],
        "recent_quotes": quotes.select_related("customer").order_by("-issue_date", "-id")[:8],
    }
    return render(request, "core/summary_dashboard.html", context)


@staff_member_required
def office_dashboard(request):
    """Admin overview across all businesses and their customers."""
    businesses = Business.objects.order_by("-created_at")
    customers = Customer.objects.select_related("business").order_by("-created_at")
    quotes = Quote.objects.select_related("business", "customer").order_by("-issue_date", "-id")

    context = {
        "business_count": businesses.count(),
        "customer_count": customers.count(),
        "quote_count": quotes.count(),
        "businesses": businesses[:12],
        "recent_customers": customers[:25],
        "recent_quotes": quotes[:12],
    }
    return render(request, "core/office_dashboard.html", context)


@login_required
def quote_manage(request):
    """List this business's quotations with edit and delete actions."""
    business = owned_business(request.user)
    quotes = (
        Quote.objects.filter(business=business)
        .select_related("customer")
        .order_by("-issue_date", "-id")
    )
    return render(request, "core/quote_manage.html", {
        "business": business,
        "quotes": quotes,
    })


@login_required
def quote_edit(request, pk):
    business = owned_business(request.user)
    quote = get_object_or_404(Quote, pk=pk, business=business)

    if hasattr(quote, "invoice"):
        messages.error(request, "This quotation already has an invoice and cannot be edited.")
        return redirect("quote_manage")

    form = QuoteForm(request.POST or None, instance=quote, business=business)
    if form.is_valid():
        form.save()
        messages.success(request, "Quotation updated.")
        return redirect("quote_manage")

    return render(request, "core/quote_edit.html", {
        "form": form,
        "quote": quote,
        "page_title": "Edit quotation",
    })


@login_required
def quote_delete(request, pk):
    business = owned_business(request.user)
    quote = get_object_or_404(Quote, pk=pk, business=business)

    if hasattr(quote, "invoice"):
        messages.error(request, "This quotation already has an invoice and cannot be deleted.")
        return redirect("quote_manage")

    if request.method == "POST":
        quote.delete()
        messages.success(request, "Quotation deleted.")
        return redirect("quote_manage")

    return render(request, "core/quote_delete.html", {"quote": quote})
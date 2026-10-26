from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import QuoteForm
from .models import Business, Quote


def get_business(user):
    business, _ = Business.objects.get_or_create(
        owner=user,
        defaults={"name": f"{user.username}'s business"},
    )
    return business


@login_required
def quote_update(request, quote_id):
    business = get_business(request.user)
    quote = get_object_or_404(Quote, pk=quote_id, business=business)

    if hasattr(quote, "invoice"):
        messages.error(request, "This quotation has been invoiced and can no longer be edited.")
        return redirect("quote_list")

    form = QuoteForm(request.POST or None, instance=quote, business=business)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Quotation {quote.reference} updated.")
        return redirect("quote_list")

    return render(request, "core/form_page.html", {
        "form": form,
        "title": f"Edit quotation · {quote.reference}",
        "subtitle": "Update the quotation details or status.",
    })


@login_required
def quote_delete(request, quote_id):
    business = get_business(request.user)
    quote = get_object_or_404(Quote, pk=quote_id, business=business)

    if hasattr(quote, "invoice"):
        messages.error(request, "This quotation has an invoice and cannot be deleted.")
        return redirect("quote_list")

    if request.method == "POST":
        reference = quote.reference
        quote.delete()
        messages.success(request, f"Quotation {reference} deleted.")
        return redirect("quote_list")

    return render(request, "core/confirm_delete.html", {
        "object_name": f"quotation {quote.reference}",
        "object_description": f"{quote.customer.name} · R {quote.amount:,.2f}",
        "cancel_url": "quote_list",
    })
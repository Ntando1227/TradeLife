from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import BusinessUpdateForm
from .models import Business, BusinessUpdate, Customer

staff_required = user_passes_test(
    lambda user: user.is_active and user.is_staff,
    login_url="login",
)


@login_required
@staff_required
def office_dashboard(request):
    cutoff = timezone.now() - timedelta(days=30)
    businesses = Business.objects.select_related("owner").annotate(
        customer_count=Count("customers")
    )
    updates = BusinessUpdate.objects.filter(
        status__in=["open", "in_progress"]
    ).select_related("business")

    return render(request, "office/dashboard.html", {
        "business_count": businesses.count(),
        "new_business_count": businesses.filter(created_at__gte=cutoff).count(),
        "customer_count": Customer.objects.count(),
        "open_update_count": updates.count(),
        "new_businesses": businesses.filter(
            created_at__gte=cutoff
        ).order_by("-created_at")[:10],
        "recent_customers": Customer.objects.select_related(
            "business", "business__owner"
        ).order_by("-created_at")[:10],
        "updates": updates.order_by("follow_up_date", "-created_at")[:10],
    })


@login_required
@staff_required
def office_businesses(request):
    query = request.GET.get("q", "").strip()
    businesses = Business.objects.select_related("owner").annotate(
        customer_count=Count("customers")
    )
    if query:
        businesses = businesses.filter(
            Q(name__icontains=query)
            | Q(owner__username__icontains=query)
            | Q(owner__email__icontains=query)
            | Q(region__icontains=query)
            | Q(town__icontains=query)
        )
    return render(request, "office/businesses.html", {
        "businesses": businesses.order_by("-created_at"),
        "query": query,
    })


@login_required
@staff_required
def office_customers(request):
    query = request.GET.get("q", "").strip()
    customers = Customer.objects.select_related("business", "business__owner")
    if query:
        customers = customers.filter(
            Q(name__icontains=query)
            | Q(contact_name__icontains=query)
            | Q(email__icontains=query)
            | Q(business__name__icontains=query)
        )
    return render(request, "office/customers.html", {
        "customers": customers.order_by("-created_at"),
        "query": query,
    })


@login_required
@staff_required
def office_updates(request):
    status = request.GET.get("status", "open")
    updates = BusinessUpdate.objects.select_related("business", "created_by")
    if status in {"open", "in_progress", "resolved"}:
        updates = updates.filter(status=status)
    else:
        status = "all"

    form = BusinessUpdateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        update = form.save(commit=False)
        update.created_by = request.user
        update.save()
        messages.success(request, "Follow-up or update saved.")
        return redirect("office_updates")

    return render(request, "office/updates.html", {
        "updates": updates,
        "form": form,
        "statuses": BusinessUpdate.STATUSES,
        "status": status,
    })


@login_required
@require_POST
@staff_required
def office_update_status(request, update_id):
    update = get_object_or_404(BusinessUpdate, pk=update_id)
    new_status = request.POST.get("status")
    if new_status not in {"open", "in_progress", "resolved"}:
        messages.error(request, "Choose a valid status.")
    else:
        update.status = new_status
        update.save(update_fields=["status", "updated_at"])
        messages.success(request, "Update status changed.")
    return redirect("office_updates")


@login_required
def my_updates(request):
    business, _ = Business.objects.get_or_create(
        owner=request.user,
        defaults={"name": f"{request.user.username}'s business"},
    )
    updates = business.updates.filter(visible_to_business=True)
    return render(request, "core/my_updates.html", {
        "business": business,
        "updates": updates,
    })
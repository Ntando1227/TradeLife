from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Business, BusinessMember


@login_required
def team_manage(request):
    business = Business.objects.filter(owner=request.user).first()
    if business is None:
        messages.error(request, "Only the business owner can manage team access.")
        return redirect("dashboard")

    User = get_user_model()

    if request.method == "POST":
        action = request.POST.get("action", "")
        username = (request.POST.get("username") or "").strip()

        if action == "add":
            if not username:
                messages.error(request, "Enter the username of an existing account.")
            else:
                member_user = User.objects.filter(username__iexact=username).first()
                if member_user is None:
                    messages.error(request, "That username does not exist yet. The person must create an account first.")
                elif member_user.pk == request.user.pk:
                    messages.error(request, "You are already the business owner.")
                else:
                    _, created = BusinessMember.objects.get_or_create(
                        business=business,
                        user=member_user,
                    )
                    if created:
                        messages.success(request, f"{member_user.username} can now access and edit this business's records.")
                    else:
                        messages.info(request, f"{member_user.username} already has access.")

        elif action == "remove":
            member_id = request.POST.get("member_id")
            member = get_object_or_404(
                BusinessMember,
                pk=member_id,
                business=business,
            )
            username_to_remove = member.user.username
            member.delete()
            messages.success(request, f"Access removed for {username_to_remove}.")

        return redirect("team_manage")

    members = BusinessMember.objects.filter(
        business=business
    ).select_related("user")

    return render(request, "core/team.html", {
        "business": business,
        "members": members,
    })
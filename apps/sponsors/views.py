from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.sponsors.forms import SponsorForm
from apps.sponsors.models import Sponsor
from apps.users.permissions import organizer_required


@login_required
def sponsors_view(request):
    sponsors = Sponsor.objects.all()
    is_organizer = getattr(request.user, "role", None) == "ORGANIZER"

    if not is_organizer:
        sponsors = sponsors.filter(is_active=True)

    return render(
        request,
        "sponsors/sponsors.html",
        {
            "sponsors": sponsors,
            "can_manage": is_organizer,
        },
    )


@login_required
@organizer_required
def sponsor_create_view(request):
    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("sponsors")
    else:
        form = SponsorForm()

    return render(request, "sponsors/sponsor_form.html", {"form": form, "is_edit": False})


@login_required
@organizer_required
def sponsor_edit_view(request, sponsor_id):
    sponsor = get_object_or_404(Sponsor, pk=sponsor_id)

    if request.method == "POST":
        form = SponsorForm(request.POST, request.FILES, instance=sponsor)
        if form.is_valid():
            form.save()
            return redirect("sponsors")
    else:
        form = SponsorForm(instance=sponsor)

    return render(
        request,
        "sponsors/sponsor_form.html",
        {
            "form": form,
            "is_edit": True,
            "sponsor": sponsor,
        },
    )


@login_required
@organizer_required
def sponsor_delete_view(request, sponsor_id):
    sponsor = get_object_or_404(Sponsor, pk=sponsor_id)

    if request.method == "POST":
        sponsor.delete()
        return redirect("sponsors")

    return render(request, "sponsors/sponsor_confirm_delete.html", {"sponsor": sponsor})

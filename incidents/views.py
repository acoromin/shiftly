from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from employees.permissions import is_admin_without_company, is_company_admin_profile

from .forms import IncidentForm, IncidentResolveForm
from .models import Incident
from .selectors import incidents_for_company, incidents_for_employee


def _profile_for(user):
    return getattr(user, 'employee_profile', None)


def _can_resolve(profile):
    return is_company_admin_profile(profile)


def _incidents_for_admin(profile):
    return incidents_for_company(profile.company)


@login_required
def list_incidents(request):
    profile = _profile_for(request.user)
    if not profile:
        incidents = Incident.objects.none()
    elif _can_resolve(profile):
        incidents = incidents_for_company(profile.company)
    elif is_admin_without_company(profile):
        raise PermissionDenied
    else:
        incidents = incidents_for_employee(profile)
    incidents = incidents.select_related('employee', 'created_by', 'resolved_by')

    return render(
        request,
        'incidents/list.html',
        {
            'profile': profile,
            'can_resolve': _can_resolve(profile),
            'incidents': incidents[:100],
        },
    )


@login_required
def create_incident(request):
    profile = _profile_for(request.user)
    if not profile or not profile.is_active:
        raise PermissionDenied

    form = IncidentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        incident = form.save(commit=False)
        incident.employee = profile
        incident.company = profile.company
        incident.created_by = request.user
        incident.save()
        messages.success(request, 'Incidencia creada correctamente.')
        return redirect('incidents:list')

    return render(request, 'incidents/form.html', {'form': form})


@login_required
def resolve_incident(request, pk, status):
    profile = _profile_for(request.user)
    if not _can_resolve(profile):
        raise PermissionDenied
    incident = get_object_or_404(_incidents_for_admin(profile), pk=pk)
    if status not in {Incident.Status.APPROVED, Incident.Status.REJECTED, Incident.Status.RESOLVED}:
        raise PermissionDenied

    form = IncidentResolveForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        incident.resolve(
            status=status,
            user=request.user,
            comment=form.cleaned_data['resolution_comment'],
        )
        messages.success(request, 'Incidencia actualizada correctamente.')
        return redirect('incidents:list')

    return render(
        request,
        'incidents/resolve.html',
        {'form': form, 'incident': incident, 'status': status},
    )

# Create your views here.

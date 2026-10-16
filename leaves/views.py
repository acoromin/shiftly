from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from employees.permissions import is_admin_without_company, is_company_admin_profile

from .forms import LeaveRequestForm, LeaveReviewForm
from .models import LeaveRequest
from .selectors import leave_requests_for_company, leave_requests_for_employee


def _profile_for(user):
    return getattr(user, 'employee_profile', None)


def _can_review(profile):
    return is_company_admin_profile(profile)


def _leave_requests_for_admin(profile):
    return leave_requests_for_company(profile.company)


@login_required
def list_requests(request):
    profile = _profile_for(request.user)
    if not profile:
        requests = LeaveRequest.objects.none()
    elif _can_review(profile):
        requests = leave_requests_for_company(profile.company)
    elif is_admin_without_company(profile):
        raise PermissionDenied
    else:
        requests = leave_requests_for_employee(profile)
    requests = requests.select_related('employee', 'reviewed_by')

    return render(
        request,
        'leaves/list.html',
        {
            'profile': profile,
            'can_review': _can_review(profile),
            'leave_requests': requests[:100],
        },
    )


REQUEST_TYPE_TITLES = {
    LeaveRequest.RequestType.VACATION: ('Solicitar vacaciones', 'Indica el periodo de vacaciones que quieres solicitar.'),
    LeaveRequest.RequestType.DAY_OFF: ('Solicitar día libre', 'Indica la fecha del día libre que necesitas.'),
    LeaveRequest.RequestType.JUSTIFIED_ABSENCE: ('Comunicar ausencia', 'Comunica una ausencia justificada para que quede registrada.'),
    LeaveRequest.RequestType.MEDICAL_ABSENCE: ('Comunicar baja médica', 'Comunica el periodo de la baja médica.'),
}


@login_required
def request_menu(request):
    profile = _profile_for(request.user)
    if not profile or not profile.is_active:
        raise PermissionDenied
    return render(request, 'leaves/menu.html')


@login_required
def create_request(request, request_type):
    profile = _profile_for(request.user)
    if not profile or not profile.is_active:
        raise PermissionDenied
    if request_type not in REQUEST_TYPE_TITLES:
        raise PermissionDenied
    title, description = REQUEST_TYPE_TITLES[request_type]
    form = LeaveRequestForm(
        request.POST or None,
        employee=profile,
        request_type=request_type,
        initial={'request_type': request_type},
    )
    if request.method == 'POST' and form.is_valid():
        leave_request = form.save(commit=False)
        leave_request.employee = profile
        if profile.company_id:
            leave_request.company = profile.company
        leave_request.save()
        messages.success(request, 'Solicitud enviada correctamente.')
        return redirect('leaves:list')

    return render(
        request,
        'leaves/form.html',
        {
            'form': form,
            'title': title,
            'description': description,
        },
    )


@login_required
def cancel_request(request, pk):
    profile = _profile_for(request.user)
    if not profile or request.method != 'POST':
        raise PermissionDenied
    leave_request = get_object_or_404(LeaveRequest, pk=pk, employee=profile)
    if leave_request.status != LeaveRequest.Status.PENDING:
        messages.error(request, 'Solo puedes cancelar solicitudes pendientes.')
    else:
        leave_request.status = LeaveRequest.Status.CANCELLED
        leave_request.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Solicitud cancelada.')
    return redirect('leaves:list')


@login_required
def review_request(request, pk, status):
    profile = _profile_for(request.user)
    if not _can_review(profile):
        raise PermissionDenied
    leave_request = get_object_or_404(_leave_requests_for_admin(profile), pk=pk)
    if status not in {LeaveRequest.Status.APPROVED, LeaveRequest.Status.REJECTED}:
        raise PermissionDenied

    form = LeaveReviewForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            leave_request.review(status=status, user=request.user, comment=form.cleaned_data['admin_comment'])
        except ValidationError as error:
            messages.error(request, ' '.join(error.messages))
        else:
            messages.success(request, 'Solicitud revisada correctamente.')
        return redirect('leaves:list')

    return render(
        request,
        'leaves/review.html',
        {'form': form, 'leave_request': leave_request, 'status': status},
    )

# Create your views here.

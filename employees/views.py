from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EmployeeForm, PasswordResetForm
from .models import EmployeeProfile
from .permissions import require_company_admin
from .selectors import active_employees_for_company, employees_for_company


def _require_admin(request):
    return require_company_admin(request.user)


def _employee_queryset_for_admin(profile):
    return employees_for_company(profile.company)


@login_required
def employee_list(request):
    current_profile = _require_admin(request)
    employees = employees_for_company(current_profile.company)
    active_count = active_employees_for_company(current_profile.company).count()
    employees = employees.select_related('user').order_by('-is_active', 'full_name')
    query = request.GET.get('q', '').strip()
    if query:
        employees = employees.filter(full_name__icontains=query)
    return render(
        request,
        'employees/list.html',
        {
            'employees': employees,
            'active_count': active_count,
            'query': query,
        },
    )


@login_required
@transaction.atomic
def employee_create(request):
    current_profile = _require_admin(request)
    form = EmployeeForm(request.POST or None, company=current_profile.company)
    if request.method == 'POST' and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            email=form.cleaned_data['email'],
        )
        employee = form.save(commit=False)
        employee.user = user
        employee.company = current_profile.company
        if not employee.primary_workplace_id and (
            current_profile.primary_workplace_id
            and current_profile.primary_workplace.company_id == current_profile.company_id
        ):
            employee.primary_workplace = current_profile.primary_workplace
        employee.save()
        messages.success(request, f'{employee.full_name} se ha añadido correctamente.')
        return redirect('employees:list')
    return render(request, 'employees/form.html', {'form': form, 'creating': True})


@login_required
@transaction.atomic
def employee_edit(request, pk):
    current_profile = _require_admin(request)
    employee = get_object_or_404(_employee_queryset_for_admin(current_profile).select_related('user'), pk=pk)
    form = EmployeeForm(request.POST or None, instance=employee, user_instance=employee.user, company=current_profile.company)
    if request.method == 'POST' and form.is_valid():
        user = employee.user
        user.username = form.cleaned_data['username']
        user.email = form.cleaned_data['email']
        if form.cleaned_data['password']:
            user.set_password(form.cleaned_data['password'])
        user.save()
        form.save()
        messages.success(request, 'Los datos del trabajador se han actualizado.')
        if current_profile.pk == employee.pk and form.cleaned_data['password']:
            messages.info(request, 'Tu contraseña ha cambiado. Vuelve a iniciar sesión.')
            return redirect('login')
        return redirect('employees:list')
    return render(
        request,
        'employees/form.html',
        {'form': form, 'employee': employee, 'creating': False},
    )


@login_required
@transaction.atomic
def employee_toggle_active(request, pk):
    current_profile = _require_admin(request)
    if request.method != 'POST':
        raise PermissionDenied
    employee = get_object_or_404(_employee_queryset_for_admin(current_profile).select_related('user'), pk=pk)
    if employee.pk == current_profile.pk:
        messages.error(request, 'No puedes dar de baja tu propio usuario.')
        return redirect('employees:list')
    employee.is_active = not employee.is_active
    employee.user.is_active = employee.is_active
    employee.user.save(update_fields=['is_active'])
    employee.save(update_fields=['is_active', 'updated_at'])
    action = 'reactivado' if employee.is_active else 'dado de baja'
    messages.success(request, f'{employee.full_name} se ha {action}.')
    return redirect('employees:list')


@login_required
def employee_password(request, pk):
    current_profile = _require_admin(request)
    employee = get_object_or_404(_employee_queryset_for_admin(current_profile).select_related('user'), pk=pk)
    form = PasswordResetForm(request.POST or None, user_instance=employee.user)
    if request.method == 'POST' and form.is_valid():
        employee.user.set_password(form.cleaned_data['password'])
        employee.user.save(update_fields=['password'])
        messages.success(request, f'Contraseña actualizada para {employee.full_name}.')
        return redirect('employees:list')
    return render(request, 'employees/password.html', {'form': form, 'employee': employee})

# Create your views here.

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import EmployeeProfile


class EmployeeForm(forms.ModelForm):
    username = forms.CharField(label='Nombre de usuario', max_length=150)
    password = forms.CharField(
        label='Contraseña temporal',
        required=False,
        widget=forms.PasswordInput,
        help_text='Obligatoria al crear. El trabajador podrá usarla para iniciar sesión.',
    )
    password_confirm = forms.CharField(
        label='Repetir contraseña',
        required=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = EmployeeProfile
        fields = (
            'full_name',
            'email',
            'phone',
            'dni_nie',
            'start_date',
            'end_date',
            'role',
            'primary_position',
            'contract_type',
            'weekly_contracted_hours',
            'base_monthly_salary',
            'hourly_rate',
            'internal_notes',
        )
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'internal_notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, user_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_instance = user_instance
        if user_instance:
            self.fields['username'].initial = user_instance.username
            self.fields['password'].help_text = 'Déjala vacía para mantener la contraseña actual.'
        else:
            self.fields['password'].required = True
            self.fields['password_confirm'].required = True
        for field in self.fields.values():
            field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} form-control".strip()

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        existing = User.objects.filter(username__iexact=username)
        if self.user_instance:
            existing = existing.exclude(pk=self.user_instance.pk)
        if existing.exists():
            raise ValidationError('Ya existe un usuario con este nombre.')
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirmation = cleaned_data.get('password_confirm')
        if password or confirmation:
            if password != confirmation:
                self.add_error('password_confirm', 'Las contraseñas no coinciden.')
            else:
                try:
                    password_validation.validate_password(password, self.user_instance)
                except ValidationError as error:
                    self.add_error('password', error)
        return cleaned_data


class PasswordResetForm(forms.Form):
    password = forms.CharField(label='Nueva contraseña', widget=forms.PasswordInput)
    password_confirm = forms.CharField(label='Repetir contraseña', widget=forms.PasswordInput)

    def __init__(self, *args, user_instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_instance = user_instance
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        if password != cleaned_data.get('password_confirm'):
            self.add_error('password_confirm', 'Las contraseñas no coinciden.')
        elif password:
            try:
                password_validation.validate_password(password, self.user_instance)
            except ValidationError as error:
                self.add_error('password', error)
        return cleaned_data

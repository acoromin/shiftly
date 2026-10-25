from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone

from companies.models import Company

from .models import BusinessConfig
from .throttling import LoginThrottleMixin


class RateLimitedAuthenticationForm(LoginThrottleMixin, AuthenticationForm):
    pass


class BusinessConfigForm(forms.ModelForm):
    class Meta:
        model = BusinessConfig
        fields = (
            'maintenance_enabled',
            'maintenance_scheduled_start',
            'maintenance_scheduled_end',
            'maintenance_reason',
            'maintenance_message',
        )
        widgets = {
            'maintenance_scheduled_start': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'maintenance_scheduled_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'maintenance_message': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} form-control".strip()
        self.fields['maintenance_enabled'].widget.attrs['class'] = 'form-check-input'
        for name in ('maintenance_scheduled_start', 'maintenance_scheduled_end'):
            value = getattr(self.instance, name, None)
            if value:
                self.initial[name] = timezone.localtime(value).strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('maintenance_scheduled_start')
        end = cleaned_data.get('maintenance_scheduled_end')
        if end and not start:
            self.add_error('maintenance_scheduled_start', 'Indica cuándo debe comenzar.')
        if start and end and end <= start:
            self.add_error('maintenance_scheduled_end', 'Debe ser posterior al inicio.')
        return cleaned_data


class CompanySettingsForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ('name', 'clock_tolerance_minutes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['clock_tolerance_minutes'].help_text = (
            'Minutos de margen tras el inicio del turno antes de detectar una entrada ausente.'
        )
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

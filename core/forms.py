from django import forms
from django.utils import timezone

from .models import BusinessConfig


class BusinessConfigForm(forms.ModelForm):
    class Meta:
        model = BusinessConfig
        fields = (
            'name',
            'public_wifi_ip',
            'clock_tolerance_minutes',
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

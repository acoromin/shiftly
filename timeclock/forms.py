from django import forms
from django.utils import timezone

from employees.selectors import active_employees_for_company
from companies.models import Workplace

from .models import TimeClockEntry


class ManualTimeClockEntryForm(forms.ModelForm):
    class Meta:
        model = TimeClockEntry
        fields = ('employee', 'workplace', 'entry_type', 'timestamp', 'manual_reason')
        widgets = {
            'timestamp': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'manual_reason': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = active_employees_for_company(company)
        self.fields['workplace'].queryset = Workplace.objects.filter(company=company, is_active=True) if company else Workplace.objects.none()
        # company is intentionally excluded from the customer-facing form.
        # Set it before ModelForm runs the model's cross-company validation.
        if company is not None:
            self.instance.company = company
        self.fields['timestamp'].initial = timezone.localtime().strftime('%Y-%m-%dT%H:%M')
        for field in self.fields.values():
            current_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{current_class} form-control'.strip()


class CorrectTimeClockEntryForm(forms.ModelForm):
    manual_reason = forms.CharField(
        label='Motivo de la corrección',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    class Meta:
        model = TimeClockEntry
        fields = ('entry_type', 'timestamp', 'manual_reason')
        widgets = {
            'timestamp': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.timestamp:
            self.initial['timestamp'] = timezone.localtime(self.instance.timestamp).strftime('%Y-%m-%dT%H:%M')
        for field in self.fields.values():
            field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} form-control".strip()

from django import forms

from employees.selectors import active_employees_for_company
from companies.models import Workplace

from .models import Shift


class ShiftForm(forms.ModelForm):
    class Meta:
        model = Shift
        fields = (
            'employee',
            'workplace',
            'date',
            'start_time',
            'end_time',
            'planned_break_minutes',
            'position',
            'notes',
        )
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'type': 'time'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, company=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = active_employees_for_company(company)
        self.fields['workplace'].queryset = Workplace.objects.filter(company=company, is_active=True) if company else Workplace.objects.none()
        if company is not None:
            self.instance.company = company
        for field in self.fields.values():
            current_class = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{current_class} form-control'.strip()

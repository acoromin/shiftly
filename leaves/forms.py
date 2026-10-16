from django import forms

from .models import LeaveRequest


class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ('request_type', 'start_date', 'end_date', 'worker_comment')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'worker_comment': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, employee=None, request_type=None, **kwargs):
        super().__init__(*args, **kwargs)
        if employee:
            self.instance.employee = employee
        if request_type:
            self.fields['request_type'].initial = request_type
            self.fields['request_type'].widget = forms.HiddenInput()
        for field in self.fields.values():
            field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} form-control".strip()

    def clean_request_type(self):
        request_type = self.cleaned_data['request_type']
        initial_type = self.initial.get('request_type')
        if initial_type and request_type != initial_type:
            raise forms.ValidationError('El tipo de solicitud no es válido.')
        return request_type

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get('request_type') == LeaveRequest.RequestType.DAY_OFF
            and cleaned_data.get('start_date')
            and cleaned_data.get('end_date')
            and cleaned_data['start_date'] != cleaned_data['end_date']
        ):
            self.add_error('end_date', 'Para un día libre, la fecha de inicio y fin deben ser iguales.')
        return cleaned_data


class LeaveReviewForm(forms.Form):
    admin_comment = forms.CharField(
        label='Comentario',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
    )

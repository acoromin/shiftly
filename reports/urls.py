from django.urls import path

from . import views

app_name = 'reports'

urlpatterns = [
    path('mensual/', views.monthly_summary, name='monthly-summary'),
    path('mensual/csv/', views.payroll_csv, name='payroll-csv'),
]

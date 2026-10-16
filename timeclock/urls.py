from django.urls import path

from . import views

app_name = 'timeclock'

urlpatterns = [
    path('fichar/', views.scan, name='scan'),
    path('fichar/resultado/', views.result, name='scan-result'),
    path('fichajes/', views.history, name='history'),
    path('mis-horas/', views.hours, name='hours'),
    path('fichajes/manual/', views.manual_create, name='manual-create'),
    path('fichajes/<int:pk>/corregir/', views.correct_entry, name='correct'),
]

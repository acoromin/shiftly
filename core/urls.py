from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.settings, name='settings'),
    path('empresa/', views.company_settings, name='company-settings'),
]

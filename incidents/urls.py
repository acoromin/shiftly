from django.urls import path

from . import views

app_name = 'incidents'

urlpatterns = [
    path('', views.list_incidents, name='list'),
    path('nueva/', views.create_incident, name='create'),
    path('<int:pk>/<str:status>/', views.resolve_incident, name='resolve'),
]

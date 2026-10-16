from django.urls import path

from . import views

app_name = 'employees'

urlpatterns = [
    path('', views.employee_list, name='list'),
    path('nuevo/', views.employee_create, name='create'),
    path('<int:pk>/editar/', views.employee_edit, name='edit'),
    path('<int:pk>/estado/', views.employee_toggle_active, name='toggle-active'),
    path('<int:pk>/contrasena/', views.employee_password, name='password'),
]

from django.urls import path

from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.week, name='week'),
    path('mes/', views.month, name='month'),
    path('nuevo/', views.create_shift, name='create'),
    path('copiar-semana/', views.copy_previous_week, name='copy-week'),
    path('<int:pk>/editar/', views.edit_shift, name='edit'),
    path('<int:pk>/duplicar/', views.duplicate_shift, name='duplicate'),
    path('<int:pk>/cancelar/', views.cancel_shift, name='cancel'),
]

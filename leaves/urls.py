from django.urls import path

from . import views

app_name = 'leaves'

urlpatterns = [
    path('', views.list_requests, name='list'),
    path('nueva/', views.request_menu, name='create'),
    path('nueva/<str:request_type>/', views.create_request, name='create-typed'),
    path('<int:pk>/cancelar/', views.cancel_request, name='cancel'),
    path('<int:pk>/<str:status>/', views.review_request, name='review'),
]

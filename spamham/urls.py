from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('batch-upload/', views.batch_upload, name='batch_upload'),
    path('batch-download/<str:batch_id>/', views.batch_download, name='batch_download'),
    path('feedback/<int:prediction_id>/', views.feedback, name='feedback'),
    path('analytics/', views.analytics, name='analytics'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
]

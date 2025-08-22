from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

urlpatterns = [
    # Authentication endpoints
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # User management endpoints
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('user/', views.UserDetailView.as_view(), name='user_detail'),
    path('dashboard/', views.user_dashboard_data, name='dashboard'),
    
    # Password management endpoints
    path('password/change/', views.PasswordChangeView.as_view(), name='password_change'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Email verification endpoints
    path('email/verify/', views.EmailVerificationView.as_view(), name='email_verify'),
    path('email/resend/', views.ResendVerificationEmailView.as_view(), name='resend_verification'),
]
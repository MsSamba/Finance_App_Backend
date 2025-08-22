from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import secrets
import logging

from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserSerializer,
    UserProfileSerializer, PasswordChangeSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    EmailVerificationSerializer
)

logger = logging.getLogger(__name__)

class UserRegistrationView(APIView):
    """
    User registration endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # Generate email verification token
                self._send_verification_email(user)
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                access_token = refresh.access_token
                
                # Serialize user data
                user_serializer = UserSerializer(user)
                
                logger.info(f"New user registered: {user.email}")
                
                return Response({
                    'message': 'Registration successful. Please check your email to verify your account.',
                    'user': user_serializer.data,
                    'tokens': {
                        'access': str(access_token),
                        'refresh': str(refresh),
                    }
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                return Response({
                    'error': 'Registration failed. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_verification_email(self, user):
        """
        Send email verification token to user
        """
        try:
            # Generate verification token
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=24)
            
            EmailVerificationToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # Send email
            subject = 'Verify Your FinanceFlow Account'
            message = f"""
            Hi {user.first_name},
            
            Welcome to FinanceFlow! Please verify your email address by clicking the link below:
            
            http://localhost:3000/verify-email?token={token}
            
            This link will expire in 24 hours.
            
            If you didn't create this account, please ignore this email.
            
            Best regards,
            FinanceFlow Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            logger.info(f"Verification email sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")

class UserLoginView(APIView):
    """
    User login endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])
            
            # Serialize user data
            user_serializer = UserSerializer(user)
            
            logger.info(f"User logged in: {user.email}")
            
            return Response({
                'message': 'Login successful',
                'user': user_serializer.data,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(APIView):
    """
    User logout endpoint
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logger.info(f"User logged out: {request.user.email}")
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'error': 'Logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(RetrieveUpdateAPIView):
    """
    User profile retrieve and update endpoint
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
    
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            logger.info(f"Profile updated for user: {request.user.email}")
        return response

class UserDetailView(RetrieveUpdateAPIView):
    """
    User detail retrieve and update endpoint
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        # Only allow updating specific fields
        allowed_fields = ['first_name', 'last_name']
        data = {key: value for key, value in request.data.items() if key in allowed_fields}
        
        serializer = self.get_serializer(self.get_object(), data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        logger.info(f"User details updated: {request.user.email}")
        
        return Response(serializer.data)

class PasswordChangeView(APIView):
    """
    Password change endpoint
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            logger.info(f"Password changed for user: {user.email}")
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetRequestView(APIView):
    """
    Password reset request endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(hours=1)
            
            PasswordResetToken.objects.create(
                user=user,
                token=token,
                expires_at=expires_at
            )
            
            # Send reset email
            self._send_reset_email(user, token)
            
            return Response({
                'message': 'Password reset email sent. Please check your inbox.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_reset_email(self, user, token):
        """
        Send password reset email
        """
        try:
            subject = 'Reset Your FinanceFlow Password'
            message = f"""
            Hi {user.first_name},
            
            You requested to reset your password for your FinanceFlow account.
            
            Click the link below to reset your password:
            
            http://localhost:3000/reset-password?token={token}
            
            This link will expire in 1 hour.
            
            If you didn't request this reset, please ignore this email.
            
            Best regards,
            FinanceFlow Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            logger.info(f"Password reset email sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to send reset email: {str(e)}")

class PasswordResetConfirmView(APIView):
    """
    Password reset confirmation endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            token_obj = serializer.validated_data['token_obj']
            new_password = serializer.validated_data['new_password']
            
            # Reset password
            user = token_obj.user
            user.set_password(new_password)
            user.save()
            
            # Mark token as used
            token_obj.is_used = True
            token_obj.save()
            
            logger.info(f"Password reset completed for user: {user.email}")
            
            return Response({
                'message': 'Password reset successful. You can now login with your new password.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class EmailVerificationView(APIView):
    """
    Email verification endpoint
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        
        if serializer.is_valid():
            token_obj = serializer.validated_data['token']
            
            # Verify email
            user = token_obj.user
            user.is_verified = True
            user.save()
            
            # Mark token as used
            token_obj.is_used = True
            token_obj.save()
            
            logger.info(f"Email verified for user: {user.email}")
            
            return Response({
                'message': 'Email verification successful. Your account is now verified.'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationEmailView(APIView):
    """
    Resend email verification endpoint
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        
        if user.is_verified:
            return Response({
                'message': 'Email is already verified.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if there's a recent verification email
        recent_token = EmailVerificationToken.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timedelta(minutes=5),
            is_used=False
        ).first()
        
        if recent_token:
            return Response({
                'message': 'Verification email was sent recently. Please wait before requesting another.'
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Generate new verification token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=24)
        
        EmailVerificationToken.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        
        # Send verification email
        self._send_verification_email(user, token)
        
        return Response({
            'message': 'Verification email sent. Please check your inbox.'
        }, status=status.HTTP_200_OK)
    
    def _send_verification_email(self, user, token):
        """
        Send email verification token to user
        """
        try:
            subject = 'Verify Your FinanceFlow Account'
            message = f"""
            Hi {user.first_name},
            
            Please verify your email address by clicking the link below:
            
            http://localhost:3000/verify-email?token={token}
            
            This link will expire in 24 hours.
            
            Best regards,
            FinanceFlow Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            logger.info(f"Verification email resent to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to resend verification email: {str(e)}")

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard_data(request):
    """
    Get user dashboard data
    """
    user = request.user
    
    dashboard_data = {
        'user': UserSerializer(user).data,
        'profile': UserProfileSerializer(user.profile).data,
        'account_status': {
            'is_verified': user.is_verified,
            'member_since': user.date_joined,
            'last_login': user.last_login,
        }
    }
    
    return Response(dashboard_data, status=status.HTTP_200_OK)
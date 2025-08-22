"""
Comprehensive tests for FinanceFlow Authentication System
Includes tests for models, serializers, and API endpoints
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta
import json

from .models import UserProfile, EmailVerificationToken, PasswordResetToken
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, 
    UserProfileSerializer, PasswordChangeSerializer
)

User = get_user_model()

class UserModelTest(TestCase):
    """Test User model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'testpass123'
        }
    
    def test_create_user(self):
        """Test user creation"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'User')
        self.assertEqual(user.full_name, 'Test User')
        self.assertFalse(user.is_verified)
        self.assertTrue(user.check_password('testpass123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
    
    def test_create_superuser(self):
        """Test superuser creation"""
        superuser = User.objects.create_superuser(
            email='admin@example.com',
            username='admin',
            password='adminpass123'
        )
        
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)
    
    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        expected_str = f"{user.first_name} {user.last_name} ({user.email})"
        self.assertEqual(str(user), expected_str)
    
    def test_user_profile_auto_creation(self):
        """Test automatic profile creation via signals"""
        user = User.objects.create_user(**self.user_data)
        
        self.assertTrue(hasattr(user, 'profile'))
        self.assertIsInstance(user.profile, UserProfile)
        self.assertEqual(user.profile.user, user)
        self.assertEqual(user.profile.preferred_currency, 'KES')
        self.assertTrue(user.profile.email_notifications)

class UserProfileModelTest(TestCase):
    """Test UserProfile model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )
    
    def test_profile_creation(self):
        """Test profile creation and default values"""
        profile = self.user.profile
        
        self.assertEqual(profile.preferred_currency, 'KES')
        self.assertEqual(profile.theme_preference, 'light')
        self.assertTrue(profile.email_notifications)
        self.assertFalse(profile.sms_notifications)
        self.assertTrue(profile.budget_alerts)
        self.assertTrue(profile.bill_reminders)
        self.assertEqual(profile.savings_goal_percentage, 20.00)
    
    def test_profile_string_representation(self):
        """Test profile string representation"""
        profile = self.user.profile
        expected_str = f"{self.user.full_name}'s Profile"
        self.assertEqual(str(profile), expected_str)
    
    def test_phone_number_validation(self):
        """Test phone number validation"""
        profile = self.user.profile
        
        # Valid Kenyan phone numbers
        valid_numbers = [
            '+254712345678',
            '0712345678',
            '+254722345678',
            '0722345678'
        ]
        
        for number in valid_numbers:
            profile.phone_number = number
            try:
                profile.full_clean()
            except ValidationError:
                self.fail(f"Valid phone number {number} failed validation")
    
    def test_currency_choices(self):
        """Test currency choices"""
        profile = self.user.profile
        valid_currencies = ['KES', 'USD', 'EUR', 'GBP']
        
        for currency in valid_currencies:
            profile.preferred_currency = currency
            profile.save()
            self.assertEqual(profile.preferred_currency, currency)

class EmailVerificationTokenTest(TestCase):
    """Test EmailVerificationToken model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
    
    def test_token_creation(self):
        """Test token creation"""
        expires_at = timezone.now() + timedelta(hours=24)
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token='test-token-123',
            expires_at=expires_at
        )
        
        self.assertEqual(token.user, self.user)
        self.assertEqual(token.token, 'test-token-123')
        self.assertFalse(token.is_used)
        self.assertFalse(token.is_expired)
    
    def test_token_expiration(self):
        """Test token expiration"""
        expires_at = timezone.now() - timedelta(hours=1)  # Expired
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token='expired-token',
            expires_at=expires_at
        )
        
        self.assertTrue(token.is_expired)

class UserRegistrationSerializerTest(TestCase):
    """Test UserRegistrationSerializer"""
    
    def setUp(self):
        """Set up test data"""
        self.valid_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }
    
    def test_valid_registration_data(self):
        """Test serializer with valid data"""
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.email, 'test@example.com')
        self.assertTrue(user.check_password('SecurePass123!'))
    
    def test_password_mismatch(self):
        """Test password confirmation mismatch"""
        data = self.valid_data.copy()
        data['password_confirm'] = 'DifferentPassword123!'
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
    
    def test_duplicate_email(self):
        """Test duplicate email validation"""
        # Create user first
        User.objects.create_user(
            email='test@example.com',
            username='existinguser',
            password='password123'
        )
        
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('email', serializer.errors)
    
    def test_duplicate_username(self):
        """Test duplicate username validation"""
        # Create user first
        User.objects.create_user(
            email='existing@example.com',
            username='testuser',
            password='password123'
        )
        
        serializer = UserRegistrationSerializer(data=self.valid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('username', serializer.errors)
    
    def test_weak_password(self):
        """Test weak password validation"""
        data = self.valid_data.copy()
        data['password'] = '123'
        data['password_confirm'] = '123'
        
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

class AuthenticationAPITest(APITestCase):
    """Test Authentication API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.registration_data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!'
        }
        
        self.user = User.objects.create_user(
            email='existing@example.com',
            username='existinguser',
            first_name='Existing',
            last_name='User',
            password='ExistingPass123!'
        )
    
    def test_user_registration_success(self):
        """Test successful user registration"""
        url = reverse('authentication:register')
        response = self.client.post(url, self.registration_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('message', response.data)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        
        # Verify user was created
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertFalse(user.is_verified)
    
    def test_user_registration_invalid_data(self):
        """Test registration with invalid data"""
        url = reverse('authentication:register')
        invalid_data = self.registration_data.copy()
        invalid_data['email'] = 'invalid-email'
        
        response = self.client.post(url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_user_login_success(self):
        """Test successful user login"""
        url = reverse('authentication:login')
        login_data = {
            'email': 'existing@example.com',
            'password': 'ExistingPass123!'
        }
        
        response = self.client.post(url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('user', response.data)
        self.assertIn('tokens', response.data)
        
        # Check user data
        user_data = response.data['user']
        self.assertEqual(user_data['email'], 'existing@example.com')
        self.assertEqual(user_data['full_name'], 'Existing User')
    
    def test_user_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        url = reverse('authentication:login')
        login_data = {
            'email': 'existing@example.com',
            'password': 'WrongPassword123!'
        }
        
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login_nonexistent_user(self):
        """Test login with non-existent user"""
        url = reverse('authentication:login')
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'SomePassword123!'
        }
        
        response = self.client.post(url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_protected_endpoint_without_auth(self):
        """Test accessing protected endpoint without authentication"""
        url = reverse('authentication:user_detail')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_protected_endpoint_with_auth(self):
        """Test accessing protected endpoint with authentication"""
        # Get access token
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Set authentication header
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:user_detail')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)
    
    def test_user_profile_retrieve(self):
        """Test user profile retrieval"""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user_email'], self.user.email)
        self.assertEqual(response.data['preferred_currency'], 'KES')
    
    def test_user_profile_update(self):
        """Test user profile update"""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:profile')
        update_data = {
            'phone_number': '+254712345678',
            'preferred_currency': 'USD',
            'email_notifications': False,
            'budget_alerts': True
        }
        
        response = self.client.patch(url, update_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '+254712345678')
        self.assertEqual(response.data['preferred_currency'], 'USD')
        self.assertFalse(response.data['email_notifications'])
    
    def test_password_change_success(self):
        """Test successful password change"""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:password_change')
        password_data = {
            'old_password': 'ExistingPass123!',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!'
        }
        
        response = self.client.post(url, password_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass123!'))
    
    def test_password_change_wrong_old_password(self):
        """Test password change with wrong old password"""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:password_change')
        password_data = {
            'old_password': 'WrongOldPass123!',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!'
        }
        
        response = self.client.post(url, password_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)
    
    def test_user_logout(self):
        """Test user logout"""
        # Get tokens
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        # Authenticate user
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:logout')
        logout_data = {
            'refresh_token': str(refresh)
        }
        
        response = self.client.post(url, logout_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
    
    def test_dashboard_data(self):
        """Test dashboard data endpoint"""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:dashboard')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('profile', response.data)
        self.assertIn('account_status', response.data)
        
        # Check account status
        account_status = response.data['account_status']
        self.assertIn('is_verified', account_status)
        self.assertIn('member_since', account_status)

class EmailVerificationTest(TransactionTestCase):
    """Test email verification functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
    
    def test_email_verification_success(self):
        """Test successful email verification"""
        # Create verification token
        expires_at = timezone.now() + timedelta(hours=24)
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token='test-verification-token',
            expires_at=expires_at
        )
        
        url = reverse('authentication:email_verify')
        data = {'token': 'test-verification-token'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify user is now verified
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_verified)
        
        # Verify token is marked as used
        token.refresh_from_db()
        self.assertTrue(token.is_used)
    
    def test_email_verification_invalid_token(self):
        """Test email verification with invalid token"""
        url = reverse('authentication:email_verify')
        data = {'token': 'invalid-token'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data)
    
    def test_email_verification_expired_token(self):
        """Test email verification with expired token"""
        # Create expired token
        expires_at = timezone.now() - timedelta(hours=1)
        token = EmailVerificationToken.objects.create(
            user=self.user,
            token='expired-token',
            expires_at=expires_at
        )
        
        url = reverse('authentication:email_verify')
        data = {'token': 'expired-token'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data)
    
    def test_resend_verification_email(self):
        """Test resending verification email"""
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:resend_verification')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Verify Your FinanceFlow Account', mail.outbox[0].subject)
    
    def test_resend_verification_already_verified(self):
        """Test resending verification for already verified user"""
        # Mark user as verified
        self.user.is_verified = True
        self.user.save()
        
        # Authenticate user
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('authentication:resend_verification')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)

class PasswordResetTest(TransactionTestCase):
    """Test password reset functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='oldpass123'
        )
    
    def test_password_reset_request_success(self):
        """Test successful password reset request"""
        url = reverse('authentication:password_reset')
        data = {'email': 'test@example.com'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Reset Your FinanceFlow Password', mail.outbox[0].subject)
        
        # Verify token was created
        self.assertTrue(
            PasswordResetToken.objects.filter(user=self.user).exists()
        )
    
    def test_password_reset_request_invalid_email(self):
        """Test password reset request with invalid email"""
        url = reverse('authentication:password_reset')
        data = {'email': 'nonexistent@example.com'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
    
    def test_password_reset_confirm_success(self):
        """Test successful password reset confirmation"""
        # Create reset token
        expires_at = timezone.now() + timedelta(hours=1)
        token = PasswordResetToken.objects.create(
            user=self.user,
            token='reset-token-123',
            expires_at=expires_at
        )
        
        url = reverse('authentication:password_reset_confirm')
        data = {
            'token': 'reset-token-123',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewSecurePass123!'))
        
        # Verify token is marked as used
        token.refresh_from_db()
        self.assertTrue(token.is_used)
    
    def test_password_reset_confirm_invalid_token(self):
        """Test password reset confirmation with invalid token"""
        url = reverse('authentication:password_reset_confirm')
        data = {
            'token': 'invalid-token',
            'new_password': 'NewSecurePass123!',
            'new_password_confirm': 'NewSecurePass123!'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

# Custom test runner for colored output
class ColoredTextTestResult:
    """Add colored output to test results"""
    
    def __init__(self):
        self.success_count = 0
        self.failure_count = 0
        self.error_count = 0
    
    def print_results(self):
        """Print colored test results summary"""
        total = self.success_count + self.failure_count + self.error_count
        
        print(f"\n{'='*60}")
        print(f"🧪 TEST RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Passed: {self.success_count}")
        print(f"❌ Failed: {self.failure_count}")
        print(f"🚨 Errors: {self.error_count}")
        print(f"📊 Total: {total}")
        
        if self.failure_count == 0 and self.error_count == 0:
            print(f"\n🎉 All tests passed successfully!")
        else:
            print(f"\n⚠️  Some tests failed. Please review the output above.")
        
        print(f"{'='*60}")
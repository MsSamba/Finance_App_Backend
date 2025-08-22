from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken
import re

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password', 'password_confirm')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_email(self, value):
        """
        Validate email format and uniqueness
        """
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_username(self, value):
        """
        Validate username format and uniqueness
        """
        if User.objects.filter(username=value.lower()).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        
        # Username should be alphanumeric with underscores
        if not re.match(r'^[a-zA-Z0-9_]+$', value):
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, and underscores."
            )
        
        return value.lower()
    
    def validate_password(self, value):
        """
        Validate password strength
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """
        Validate password confirmation
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs
    
    def create(self, validated_data):
        """
        Create user with validated data
        """
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    email = serializers.EmailField()
    password = serializers.CharField(
        style={'input_type': 'password'},
        trim_whitespace=False
    )
    
    def validate(self, attrs):
        """
        Validate login credentials
        """
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            # Authenticate using email instead of username
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )
            
            if not user:
                # Try to find user by email and check if they exist
                try:
                    user_obj = User.objects.get(email=email)
                    raise serializers.ValidationError(
                        'Invalid password. Please check your password and try again.'
                    )
                except User.DoesNotExist:
                    raise serializers.ValidationError(
                        'No account found with this email address.'
                    )
            
            if not user.is_active:
                raise serializers.ValidationError(
                    'User account is disabled. Please contact support.'
                )
            
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(
                'Must include "email" and "password".'
            )

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile
    """
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_date_joined = serializers.DateTimeField(source='user.date_created', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = (
            'user_email', 'user_full_name', 'user_date_joined',
            'phone_number', 'date_of_birth', 'avatar',
            'preferred_currency', 'theme_preference',
            'email_notifications', 'sms_notifications',
            'budget_alerts', 'bill_reminders',
            'monthly_budget_limit', 'savings_goal_percentage',
            'created_at', 'updated_at'
        )
        read_only_fields = ('created_at', 'updated_at')
    
    def validate_phone_number(self, value):
        """
        Validate Kenyan phone number format
        """
        if value:
            # Remove spaces and dashes
            cleaned_number = re.sub(r'[\s\-]', '', value)
            
            # Check if it matches Kenyan format
            kenyan_pattern = r'^(\+254|254|0)[17]\d{8}$'
            if not re.match(kenyan_pattern, cleaned_number):
                raise serializers.ValidationError(
                    "Please enter a valid Kenyan phone number (e.g., +254712345678 or 0712345678)"
                )
            
            # Normalize to international format
            if cleaned_number.startswith('0'):
                cleaned_number = '+254' + cleaned_number[1:]
            elif cleaned_number.startswith('254'):
                cleaned_number = '+' + cleaned_number
            
            return cleaned_number
        return value

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for user information
    """
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'is_verified', 'date_joined', 'profile'
        )
        read_only_fields = ('id', 'username', 'date_joined', 'is_verified')

class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change
    """
    old_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(
        style={'input_type': 'password'},
        min_length=8
    )
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})
    
    def validate_old_password(self, value):
        """
        Validate old password
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value
    
    def validate_new_password(self, value):
        """
        Validate new password strength
        """
        try:
            validate_password(value, user=self.context['request'].user)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """
        Validate password confirmation
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords do not match.")
        
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError("New password must be different from old password.")
        
        return attrs

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request
    """
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """
        Validate that user exists with this email
        """
        try:
            User.objects.get(email=value.lower())
        except User.DoesNotExist:
            raise serializers.ValidationError("No account found with this email address.")
        return value.lower()

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation
    """
    token = serializers.CharField()
    new_password = serializers.CharField(
        style={'input_type': 'password'},
        min_length=8
    )
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})
    
    def validate_new_password(self, value):
        """
        Validate new password strength
        """
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value
    
    def validate(self, attrs):
        """
        Validate password confirmation and token
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("Passwords do not match.")
        
        # Validate token
        try:
            token_obj = PasswordResetToken.objects.get(
                token=attrs['token'],
                is_used=False
            )
            if token_obj.is_expired:
                raise serializers.ValidationError("Password reset token has expired.")
            attrs['token_obj'] = token_obj
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired password reset token.")
        
        return attrs

class EmailVerificationSerializer(serializers.Serializer):
    """
    Serializer for email verification
    """
    token = serializers.CharField()
    
    def validate_token(self, value):
        """
        Validate verification token
        """
        try:
            token_obj = EmailVerificationToken.objects.get(
                token=value,
                is_used=False
            )
            if token_obj.is_expired:
                raise serializers.ValidationError("Email verification token has expired.")
            return token_obj
        except EmailVerificationToken.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired verification token.")
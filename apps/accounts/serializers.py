from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User

GMAIL_DOMAINS = {'gmail.com', 'googlemail.com'}


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        # No barangay: it is taken from the farmer's first farm pin (apps/farms/barangays.py)
        fields = ['email', 'password', 'password2', 'first_name', 'last_name',
                  'municipality', 'province']

    def validate_email(self, value):
        # Forgot-password codes go by email, so the address must be a real inbox. Farmers
        # without Gmail get an account from an agriculturist through the admin site instead.
        if value.rsplit('@', 1)[-1].lower() not in GMAIL_DOMAINS:
            raise serializers.ValidationError('Please use a Gmail address (ending in @gmail.com).')
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered.')
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        # AUTH_PASSWORD_VALIDATORS: length, common passwords, all-numeric, similar to name/email
        candidate = User(email=data.get('email', ''), first_name=data.get('first_name', ''),
                         last_name=data.get('last_name', ''))
        try:
            validate_password(data['password'], user=candidate)
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        # Auto-generate unique username from phone
        base = (validated_data.get('phone', '') or '').replace('+', '').replace(' ', '')
        if not base:
            base = validated_data.get('email', 'user').split('@')[0]
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{n}'
            n += 1
        validated_data['username'] = username
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


ACCOUNT_DISABLED = 'Your account is disabled. Please contact the RiceFlow office for help.'


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        try:
            user_obj = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials.')
        # authenticate() returns None for a deactivated account even with the right
        # password, so it could never be told apart from a wrong password. Say it is
        # disabled only to someone who knows the password: no hint which emails exist.
        if not user_obj.is_active and user_obj.check_password(data['password']):
            raise serializers.ValidationError(ACCOUNT_DISABLED)
        user = authenticate(username=user_obj.username, password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        update_last_login(None, user)      # for the admin's Users page
        refresh = RefreshToken.for_user(user)
        return {
            'user':          UserSerializer(user).data,
            'access_token':  str(refresh.access_token),
            'refresh_token': str(refresh),
        }


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email         = serializers.EmailField()
    code          = serializers.RegexField(r'^\d{6}$', error_messages={'invalid': 'Enter the 6-digit code.'})
    new_password  = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password2']:
            raise serializers.ValidationError({'new_password': 'Passwords do not match.'})
        return data


class UserSerializer(serializers.ModelSerializer):
    has_farm = serializers.SerializerMethodField()

    class Meta:
        model  = User
        # is_superuser distinguishes a full admin from an agriculturist:
        # both are staff, only the admin is a superuser.
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'phone', 'barangay', 'municipality', 'province', 'is_staff',
                  'is_superuser', 'has_farm']
        # Roles are only changed through the admin user endpoints, never by a user on themselves
        read_only_fields = ['id', 'is_staff', 'is_superuser']

    def get_has_farm(self, obj):
        return obj.farms.filter(is_active=True).exists()

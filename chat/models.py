import os
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone, crypto
from .utils import send_otp, generate_qr_code

class ChatMessage(models.Model):
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Message sent at {self.timestamp}'

class CustomUserManager(BaseUserManager):
    def _generate_otp(self):
        return crypto.get_random_string(length=4, allowed_chars='0123456789')


    def create_user(self, mobile, **extra_fields):
        if not mobile:
            raise ValueError('The Mobile number must be set')
        user = self.model(mobile=mobile, **extra_fields)
        user.set_unusable_password()  
        user.otp = self._generate_otp()
        user.otp_created = timezone.now()
        user.is_active = False # User is inactive till he verifies OTP
        user.save(using=self._db)
        generate_qr_code(user)
        user.save(using=self._db)  # Save the user again with QR code
        return user

    def create_superuser(self, mobile, password=None, **extra_fields):
            extra_fields.setdefault('is_staff', True)
            extra_fields.setdefault('is_superuser', True)
            extra_fields.setdefault('username', mobile)
            extra_fields.setdefault('qr_code', None)
            extra_fields.setdefault('is_active', True)
            extra_fields.setdefault('otp', None)
            extra_fields.setdefault('otp_created', timezone.now())

            user = self.create_user(mobile, **extra_fields)
            
            user.set_password(password)
            user.save(using=self._db)
            return user
        


    def login(self, mobile):
        try:
            user = self.get(mobile=mobile)
        except self.model.DoesNotExist:
            user = self.create_user(mobile)
        user.otp = self._generate_otp()
        user.otp_created = timezone.now()
        user.save()

        # Logic to send OTP
        send_otp(mobile, user.otp)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    mobile = models.CharField(max_length=15, unique=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    otp = models.CharField(max_length=6, blank=True, null=True)
    otp_created = models.DateTimeField(null=True, blank=True)
    username = models.CharField(max_length=50, blank=True, null=True)


    groups = models.ManyToManyField(
        'auth.Group',
        blank=True,
        related_name="customuser_groups",  # Changed related_name
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        related_name="customuser_permissions",  # Changed related_name
        related_query_name="customuser",
    )


    objects = CustomUserManager()

    USERNAME_FIELD = 'mobile'
    REQUIRED_FIELDS = []


    def verify_otp(self, otp):
        # Logic to verify OTP and activate user
        if self.otp == otp and self.otp_created + timezone.timedelta(minutes=5) > timezone.now():
            self.is_active = True
            self.otp = None  # Clear the OTP once verified
            self.save()
            return True
        return False

    def __str__(self):
        return self.mobile


class ConnectionRequest(models.Model):
    sender = models.ForeignKey(CustomUser, related_name='sent_requests', on_delete=models.CASCADE)
    receiver = models.ForeignKey(CustomUser, related_name='received_requests', on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender} -> {self.receiver}: {self.status}'

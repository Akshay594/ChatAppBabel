from django.contrib.auth.backends import ModelBackend
from chat.models import CustomUser

class OTPAuthenticationBackend(ModelBackend):
    def authenticate(self, request, mobile=None, otp=None, **kwargs):
        try:
            user = CustomUser.objects.get(mobile=mobile, otp=otp)
            return user
        except CustomUser.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None
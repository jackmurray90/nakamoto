from django.db import models
from django.contrib.auth.models import User


class SignUp(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=23)
    otp_key = models.CharField(max_length=32)
    expiry = models.DateTimeField()


class Settings(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp_key = models.CharField(max_length=32)

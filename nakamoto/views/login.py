from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from nakamoto.models import Settings
import pyotp


class LoginView(View):
    def get(self, request):
        return render(request, "login.html")

    def post(self, request):
        # Verify email and password
        email = request.POST["email"].strip().lower()
        password = request.POST["password"]
        user = authenticate(request, username=email, password=password)
        if not user:
            messages.error(request, "Invalid email or password")
            return redirect("login")

        # Verify second factor code
        settings = Settings.objects.filter(user=user).first()
        if not settings or not pyotp.TOTP(settings.otp_key).verify(request.POST["otp"]):
            messages.error(request, "Invalid second factor code")
            return redirect("login")

        # Login the user and redirect to index
        login(request, user)
        return redirect("index")


class LogoutView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request):
        logout(request)
        return redirect("index")

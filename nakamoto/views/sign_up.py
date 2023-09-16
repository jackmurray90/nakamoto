from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from nakamoto.util import random_128_bit_string
from nakamoto.models import SignUp, Settings
from datetime import datetime, timezone, timedelta
import os
import pyotp
import qrcode
import base64


class SignUpView(View):
    def get(self, request):
        return render(request, "sign_up.html")

    def post(self, request):
        # Get the email, strip it, and lowercase it
        email = request.POST["email"].strip().lower()

        # Check that a user with that email doesn't already exist
        user = User.objects.filter(email=email).first()
        if user:
            messages.error(request, "A user with that email already exists")
            return redirect("sign-up")

        # Create the email verification code
        sign_up = SignUp.objects.create(
            email=email,
            code=random_128_bit_string(),
            otp_key=pyotp.random_base32(),
            expiry=datetime.now(timezone.utc) + timedelta(days=1),
        )

        # Generate the email
        plaintext = get_template("sign_up_email.txt")
        html = get_template("sign_up_email.html")
        subject = "Welcome to Nakamoto Market"
        from_email = "no-reply@nakamoto.market"
        to = email
        text_content = plaintext.render({"code": sign_up.code})
        html_content = html.render({"code": sign_up.code})

        # Create the email message with the content and send it
        message = EmailMultiAlternatives(subject, text_content, from_email, [to])
        message.attach_alternative(html_content, "text/html")
        message.send()

        # Respond to the user with a success message
        messages.success(request, "Check your inbox for a verification link")
        return redirect("sign-up")


class SignUpVerifyView(View):
    def get(self, request, code):
        # If the sign up verification process is finished, just display the success message
        if code == "finished":
            return render(request, "sign_up_verify.html", {"no_passwords": True})

        # Verify the sign up code is correct
        sign_up = SignUp.objects.filter(
            code=code, expiry__gte=datetime.now(timezone.utc)
        ).first()
        if not sign_up:
            messages.error(request, "Invalid verification code")
            return render(request, "sign_up_verify.html", {"no_passwords": True})

        # Verify a user with that email doesn't already exist
        if User.objects.filter(email=sign_up.email).first():
            messages.error(request, "That email address is already signed up")
            return render(request, "sign_up_verify.html", {"no_passwords": True})

        # Generate the qrcode image string
        totp_auth = pyotp.totp.TOTP(sign_up.otp_key).provisioning_uri(
            name=sign_up.email, issuer_name="Nakamoto"
        )
        tempfile = f"/tmp/{random_128_bit_string()}.png"
        qrcode.make(totp_auth).save(tempfile)
        with open(tempfile, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        os.remove(tempfile)
        data_url = f"data:image/png;base64,{data}"

        # Render the template to set password
        return render(request, "sign_up_verify.html", {"qrcode": data_url})

    def post(self, request, code):
        # Verify the sign up code is correct
        sign_up = SignUp.objects.filter(
            code=code, expiry__gte=datetime.now(timezone.utc)
        ).first()
        if not sign_up:
            return redirect("sign-up-verify", code=code)

        # Verify a user with that email doesn't already exist
        if User.objects.filter(email=sign_up.email).first():
            return redirect("sign-up-verify", code=code)

        # Verify passwords match
        if not request.POST["password"] == request.POST["password_verify"]:
            messages.error(request, "Passwords do not match")
            return redirect("sign-up-verify", code=code)

        # Verify second factor code
        totp = pyotp.TOTP(sign_up.otp_key)
        if not totp.verify(request.POST["otp"]):
            messages.error(request, "Invalid second factor code")
            return redirect("sign-up-verify", code=code)

        # Create the user and set their password
        user = User.objects.create(username=sign_up.email, email=sign_up.email)
        user.set_password(request.POST["password"])
        user.save()

        # Create Settings object for user, assigning otp_key
        Settings.objects.create(user=user, otp_key=sign_up.otp_key)

        # Delete the SignUp object
        sign_up.delete()

        # Respond to the user with a success message
        messages.success(
            request, "Successfully verified email. Your user account has been created."
        )
        return redirect("sign-up-verify", code="finished")

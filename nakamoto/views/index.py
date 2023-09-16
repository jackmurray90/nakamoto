from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.contrib import messages


class IndexView(LoginRequiredMixin, View):
    login_url = "/login"

    def get(self, request):
        return render(request, "index.html")

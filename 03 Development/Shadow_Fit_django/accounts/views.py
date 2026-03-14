from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, LoginForm
from django.contrib import messages


# Dashboard accessible to everyone
def dashboard(request):
    return render(request, 'accounts/dashboard.html')


# Register
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)

        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'Member'
            user.save()

            messages.success(request, "Registration successful!")
            login(request, user)

            return redirect('dashboard')

        else:
            messages.error(request, "Registration failed. Please fix the errors below.")

    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


# Login
def login_view(request):

    if request.method == 'POST':

        form = LoginForm(request, data=request.POST)

        if form.is_valid():

            login(request, form.get_user())
            messages.success(request, "Login successful!")

            return redirect('dashboard')

        else:
            messages.error(request, "Invalid username or password.")

    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


# Logout
def logout_view(request):
    logout(request)
    return redirect('dashboard')
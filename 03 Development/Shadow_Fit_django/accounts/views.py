from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.forms import PasswordResetForm
from .forms import RegisterForm, LoginForm
from django.contrib import messages


# Dashboard accessible to everyone
def dashboard(request):
    return redirect('client_dashboard')

# Register
def register_view(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.role == 'Admin':
            return redirect('admin_dashboard')
        elif request.user.role == 'Trainer':
            return redirect('dashboard')
        else:
            return redirect('client_dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'Member'
            user.first_name = form.cleaned_data.get('first_name')
            user.last_name = form.cleaned_data.get('last_name')
            user.save()
            messages.success(request, "Registration successful!")
            login(request, user)
            return redirect('client_dashboard')
        else:
            messages.error(request, "Registration failed. Please fix the errors below.")
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})

# Login
def login_view(request):
    # Redirect if already logged in
    if request.user.is_authenticated:
        if request.user.role == 'Admin':
            return redirect('admin_dashboard')
        elif request.user.role == 'Trainer':
            return redirect('dashboard')
        else:
            return redirect('client_dashboard')
        
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Handle Remember Me — session expires on browser close if unchecked
            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(120)  # 2 minutes for clients
            else:
                request.session.set_expiry(1209600)  # 2 weeks if Remember Me checked

            messages.success(request, "Login successful!")
            if user.role == 'Admin':
                return redirect('admin_dashboard')
            elif user.role == 'Trainer':
                return redirect('trainer_dashboard')
            else:
                return redirect('client_dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

# Forgot Password
def forgot_password(request):
    """
    Sends password reset email to user.
    """
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if not email:
            messages.error(request, "Please enter your email address.")
            return render(request, 'accounts/forgot_password.html')

        try:
            from accounts.models import CustomUser
            from client_portal.notifications import send_email
            import secrets

            # Check if user exists
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                # Don't reveal if email exists — security best practice
                messages.success(
                    request,
                    "If that email is registered, a reset link will be sent."
                )
                return redirect('login')

            # Generate a temporary password
            temp_password = secrets.token_urlsafe(8)
            user.set_password(temp_password)
            user.save()

            # Send temporary password via email
            send_email(
                subject="Shadow Fit — Password Reset",
                message=(
                    f"Hi {user.get_full_name()},\n\n"
                    f"Your password has been reset.\n\n"
                    f"Temporary Password: {temp_password}\n\n"
                    f"Please login and change your password immediately.\n"
                    f"Login at: http://127.0.0.1:8000/login/\n\n"
                    f"Shadow Fit Team"
                ),
                recipient_email=email,
            )

            messages.success(
                request,
                "A temporary password has been sent to your email."
            )
            return redirect('login')

        except Exception as e:
            messages.error(request, "Failed to process request. Please try again.")

    return render(request, 'accounts/forgot_password.html')

# Logout
def logout_view(request):
    logout(request)
    return redirect('client_dashboard')
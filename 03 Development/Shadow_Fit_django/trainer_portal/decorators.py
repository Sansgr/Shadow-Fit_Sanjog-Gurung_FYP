from django.shortcuts import redirect
from django.contrib import messages


def trainer_required(view_func):
    """
    Restricts access to Trainer role users only.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this page.")
            return redirect('login')
        if request.user.role != 'Trainer':
            messages.error(request, "You do not have permission to access this page.")
            return redirect('client_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
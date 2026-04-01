from django.shortcuts import render
from admin_panel.decorators import admin_required

# Create your views here.
@admin_required
def admin_dashboard(request):
    return render(request, 'admin_panel/dashboard.html')
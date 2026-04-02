from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from admin_panel.decorators import admin_required
from accounts.models import CustomUser
from gym.models import MembershipPlan
from admin_panel.forms import ClientForm, MembershipPlanForm


# ADMIN DASHBOARD 
@admin_required
def admin_dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


# ClIENT MANAGEMENT VIEWS
# CLIENT LIST
@admin_required
def client_list(request):
    clients = CustomUser.objects.filter(role='Member').order_by('-date_joined')
    return render(request, 'admin_panel/clients/client_list.html', {'clients': clients})


# CLIENT ADD
@admin_required
def client_add(request):
    if request.method == 'POST':
        form = ClientForm(request.POST, request.FILES)
        if form.is_valid():
            client = form.save(commit=False)
            client.role = 'Member'
            client.set_password(f"{form.cleaned_data.get('username')}@123")  # default password
            client.save()
            messages.success(request, "Client added successfully!")
            return redirect('client_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ClientForm()
    return render(request, 'admin_panel/clients/client_add.html', {'form': form})


# CLIENT UPDATE 
@admin_required
def client_update(request, pk):
    client = get_object_or_404(CustomUser, pk=pk, role='Member')
    if request.method == 'POST':
        form = ClientForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Client updated successfully!")
            return redirect('client_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ClientForm(instance=client)
    return render(request, 'admin_panel/clients/client_update.html', {'form': form, 'client': client})


# CLIENT DELETE 
@admin_required
def client_delete(request, pk):
    client = get_object_or_404(CustomUser, pk=pk, role='Member')
    if request.method == 'POST':
        client.delete()
        messages.success(request, "Client deleted successfully!")
        return redirect('client_list')
    return render(request, 'admin_panel/clients/client_delete.html', {'client': client})


# MEMBERSHIP PLAN MANAGEMENT VIEWS
# PLAN LIST 
@admin_required
def plan_list(request):
    plans = MembershipPlan.objects.all().order_by('price')
    return render(request, 'admin_panel/plans/plan_list.html', {'plans': plans})


# PLAN ADD 
@admin_required
def plan_add(request):
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Membership plan added successfully!")
            return redirect('plan_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = MembershipPlanForm()
    return render(request, 'admin_panel/plans/plan_add.html', {'form': form})


# PLAN UPDATE 
@admin_required
def plan_update(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        form = MembershipPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, "Membership plan updated successfully!")
            return redirect('plan_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = MembershipPlanForm(instance=plan)
    return render(request, 'admin_panel/plans/plan_update.html', {'form': form, 'plan': plan})


# PLAN DELETE 
@admin_required
def plan_delete(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, "Membership plan deleted successfully!")
        return redirect('plan_list')
    return render(request, 'admin_panel/plans/plan_delete.html', {'plan': plan})
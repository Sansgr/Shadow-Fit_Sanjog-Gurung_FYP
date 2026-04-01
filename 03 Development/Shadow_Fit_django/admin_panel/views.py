from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from admin_panel.decorators import admin_required
from accounts.models import CustomUser
from admin_panel.forms import ClientForm


# ADMIN DASHBOARD 
@admin_required
def admin_dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


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
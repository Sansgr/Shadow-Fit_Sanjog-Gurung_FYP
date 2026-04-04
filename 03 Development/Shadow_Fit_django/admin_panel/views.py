from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from admin_panel.decorators import admin_required
from accounts.models import CustomUser
from gym.models import MembershipPlan, Schedule, Trainer
from admin_panel.forms import ClientForm, MembershipPlanForm, ScheduleForm, TrainerUserForm, TrainerProfileForm


# 1) ADMIN DASHBOARD 
@admin_required
def admin_dashboard(request):
    return render(request, 'admin_panel/dashboard.html')


# 2) CLIENT MANAGEMENT VIEWS
# a) CLIENT LIST
@admin_required
def client_list(request):
    clients = CustomUser.objects.filter(role='Member').order_by('-date_joined')
    return render(request, 'admin_panel/clients/client_list.html', {'clients': clients})


# b) CLIENT ADD
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


# c) CLIENT UPDATE 
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


# d) CLIENT DELETE 
@admin_required
def client_delete(request, pk):
    client = get_object_or_404(CustomUser, pk=pk, role='Member')
    if request.method == 'POST':
        client.delete()
        messages.success(request, "Client deleted successfully!")
        return redirect('client_list')
    return render(request, 'admin_panel/clients/client_delete.html', {'client': client})


# 3) MEMBERSHIP PLAN MANAGEMENT VIEWS
# a) PLAN LIST 
@admin_required
def plan_list(request):
    plans = MembershipPlan.objects.all().order_by('price')
    return render(request, 'admin_panel/plans/plan_list.html', {'plans': plans})


# b) PLAN ADD 
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


# c) PLAN UPDATE 
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


# d) PLAN DELETE 
@admin_required
def plan_delete(request, pk):
    plan = get_object_or_404(MembershipPlan, pk=pk)
    if request.method == 'POST':
        plan.delete()
        messages.success(request, "Membership plan deleted successfully!")
        return redirect('plan_list')
    return render(request, 'admin_panel/plans/plan_delete.html', {'plan': plan})


# 4) TRAINER MANAGEMENT VIEWS
# a) TRAINER LIST 
@admin_required
def trainer_list(request):
    trainers = Trainer.objects.select_related('user').all().order_by('user__first_name')
    return render(request, 'admin_panel/trainers/trainer_list.html', {'trainers': trainers})


# b) TRAINER ADD 
@admin_required
def trainer_add(request):
    if request.method == 'POST':
        user_form = TrainerUserForm(request.POST, request.FILES)
        profile_form = TrainerProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            # Save user first
            user = user_form.save(commit=False)
            user.role = 'Trainer'
            user.set_password(f"{user_form.cleaned_data.get('username')}@123")
            user.save()
            # Save trainer profile
            trainer = profile_form.save(commit=False)
            trainer.user = user
            trainer.save()
            messages.success(request, "Trainer added successfully!")
            return redirect('trainer_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        user_form = TrainerUserForm()
        profile_form = TrainerProfileForm()
    return render(request, 'admin_panel/trainers/trainer_add.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })


# c) TRAINER UPDATE 
@admin_required
def trainer_update(request, pk):
    trainer = get_object_or_404(Trainer, pk=pk)
    if request.method == 'POST':
        user_form = TrainerUserForm(request.POST, request.FILES, instance=trainer.user)
        profile_form = TrainerProfileForm(request.POST, instance=trainer)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Trainer updated successfully!")
            return redirect('trainer_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        user_form = TrainerUserForm(instance=trainer.user)
        profile_form = TrainerProfileForm(instance=trainer)
    return render(request, 'admin_panel/trainers/trainer_update.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'trainer': trainer
    })


# d) TRAINER DELETE 
@admin_required
def trainer_delete(request, pk):
    trainer = get_object_or_404(Trainer, pk=pk)
    if request.method == 'POST':
        trainer.user.delete()   # deletes CustomUser which cascades to Trainer
        messages.success(request, "Trainer deleted successfully!")
        return redirect('trainer_list')
    return render(request, 'admin_panel/trainers/trainer_delete.html', {'trainer': trainer})


# 5) SCHEDULE MANAGEMENT VIEWS
# a) SCHEDULE LIST
@admin_required
def schedule_list(request):
    schedules = Schedule.objects.select_related('trainer__user').all().order_by('trainer__user__first_name', 'day_of_week')
    return render(request, 'admin_panel/schedules/schedule_list.html', {'schedules': schedules})


# b) SCHEDULE ADD
@admin_required
def schedule_add(request):
    if request.method == 'POST':
        form = ScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Schedule added successfully!")
            return redirect('schedule_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ScheduleForm()
    return render(request, 'admin_panel/schedules/schedule_add.html', {'form': form})


# c) SCHEDULE UPDATE
@admin_required
def schedule_update(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, "Schedule updated successfully!")
            return redirect('schedule_list')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = ScheduleForm(instance=schedule)
    return render(request, 'admin_panel/schedules/schedule_update.html', {'form': form, 'schedule': schedule})


# d) SCHEDULE DELETE
@admin_required
def schedule_delete(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, "Schedule deleted successfully!")
        return redirect('schedule_list')
    return render(request, 'admin_panel/schedules/schedule_delete.html', {'schedule': schedule})
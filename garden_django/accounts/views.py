from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .forms import SignUpForm, LoginForm

from django.contrib.auth.decorators import login_required
from .forms import ApiKeyForm

def signup_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if form.cleaned_data['email']:
                user.email = form.cleaned_data['email']
            user.save()
            login(request, user)  # Log in the user directly after signing up
            return redirect('seeds_list')  # Redirect to a home page or dashboard
    else:
        form = SignUpForm()
    return render(request, 'accounts/signup.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('seeds_list')  # Redirect to home or some profile page
        else:
            form.add_error(None, "Username or Password is not correct")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def update_api_key(request):
    if request.method == 'POST':
        form = ApiKeyForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('home')  # Assuming there's a profile view to return to
    else:
        form = ApiKeyForm(instance=request.user)

    return render(request, 'accounts/update_api_key.html', {'form': form})

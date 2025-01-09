from django.shortcuts import render, redirect

# Create your views here.

# home
def home(request):
    return render(request, 'tournament/home.html')
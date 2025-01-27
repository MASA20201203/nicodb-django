from django.shortcuts import render


def index(request):
    return render(request, "streamings/index.html")

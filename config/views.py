"""Landing page and login views for nl2cad.de."""
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render


def landing(request):
    """Public landing page for nl2cad.de."""
    if request.user.is_authenticated:
        return redirect("ifc:dashboard")
    return render(request, "landing.html")


def login_view(request):
    """Custom login page."""
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "ifc:dashboard")
            return redirect(next_url)
        return render(request, "login.html", {"error": "Ungültige Anmeldedaten."})
    return render(request, "login.html")

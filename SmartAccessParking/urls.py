"""
URL configuration for SmartAccessParking project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from django.urls import include, path, reverse


def home(request):
    """Abre el módulo principal o solicita autenticación desde la raíz."""
    target = "registros:registro_list" if request.user.is_authenticated else "login"
    return redirect(reverse(target))

urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path(
        "acceso/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("usuarios/", include("usuarios.urls")),
    path("estacionamientos/", include("estacionamientos.urls")),
    path("registros/", include("registros.urls")),
]

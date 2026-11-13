"""URL configuration for SmartAccess Parking."""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, reverse
from django.views.generic import RedirectView

from common.views import (
    AccessAwareLoginView,
    NoModuleAccessView,
    get_landing_url,
)


class HomeRedirectView(RedirectView):
    """Redirige a la pantalla principal o al acceso, según la sesión."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return reverse("login")
        return get_landing_url(self.request.user)


urlpatterns = [
    path("", HomeRedirectView.as_view(), name="home"),
    path("admin/", admin.site.urls),
    path(
        "acceso/",
        AccessAwareLoginView.as_view(
            template_name="registration/login.html",
        ),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("sin-acceso/", NoModuleAccessView.as_view(), name="sin_acceso"),
    path("usuarios/", include("usuarios.urls")),
    path("estacionamientos/", include("estacionamientos.urls")),
    path("registros/", include("registros.urls")),
]

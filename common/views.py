from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import ProtectedError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, TemplateView


PLAZA_SCOPE_LOOKUPS = {
    "estacionamientos.plaza": None,
    "estacionamientos.estacionamiento": "plaza_id__in",
    "estacionamientos.sensor": "estacionamiento__plaza_id__in",
    "usuarios.usuario": "plazas__id__in",
    "usuarios.vehiculo": "usuario__plazas__id__in",
    "usuarios.acreditacion": "usuario__plazas__id__in",
    "registros.registrouso": "estacionamiento__plaza_id__in",
    "registros.capturaplaca": "registro_uso__estacionamiento__plaza_id__in",
    "registros.incidencia": "registro_uso__estacionamiento__plaza_id__in",
    "registros.intentoacceso": "plaza_id__in",
    "registros.boleto": "registro_uso__estacionamiento__plaza_id__in",
    "registros.pago": "boleto__registro_uso__estacionamiento__plaza_id__in",
}


def managed_plazas(user):
    """Return active plazas assigned to the signed-in operational role."""
    from estacionamientos.models import Plaza

    plazas = Plaza.objects.all()
    if user.is_superuser:
        return plazas
    return plazas.filter(
        Q(administradores=user) | Q(personal_acceso=user),
        activa=True,
    ).distinct()


def scope_to_managed_plazas(queryset, user):
    """Limit app querysets to plazas assigned to this account."""
    if user.is_superuser:
        return queryset
    lookup = PLAZA_SCOPE_LOOKUPS.get(queryset.model._meta.label_lower, "__unscoped__")
    if lookup == "__unscoped__":
        return queryset
    plazas = managed_plazas(user).values_list("pk", flat=True)
    if lookup is None:
        return queryset.filter(pk__in=plazas)
    return queryset.filter(**{lookup: plazas}).distinct()


def can_manage_plaza(user, plaza):
    """Check that an operator is assigned to the requested plaza."""
    return managed_plazas(user).filter(pk=plaza.pk).exists()


LANDING_DESTINATIONS = (
    ("registros.view_registrouso", "registros:registro_list"),
    ("registros.view_capturaplaca", "registros:captura_list"),
    ("registros.view_incidencia", "registros:incidencia_list"),
    (
        "estacionamientos.view_estacionamiento",
        "estacionamientos:estacionamiento_list",
    ),
    ("usuarios.view_usuario", "usuarios:usuario_list"),
    ("usuarios.view_acreditacion", "usuarios:acreditacion_list"),
)


def get_landing_url(user):
    """Return the first module the signed-in user is allowed to open."""
    if user.is_superuser:
        return reverse("admin:index")

    if user.has_perm("registros.validate_plate_access"):
        return reverse("registros:intento_create")

    if user.has_perm("estacionamientos.view_operational_dashboard"):
        return reverse("estacionamientos:panel_operacion")

    try:
        user.perfil_estacionamiento
    except ObjectDoesNotExist:
        pass
    else:
        return reverse("usuarios:mi_cuenta")

    for permission, route in LANDING_DESTINATIONS:
        if user.has_perm(permission):
            return reverse(route)
    if user.is_staff:
        return reverse("admin:index")
    return reverse("sin_acceso")


class AccessAwareLoginView(LoginView):
    """Send users to an area they can actually access after login."""

    def dispatch(self, request, *args, **kwargs):
        # Avoid a second login in an already authenticated browser session.
        # Re-authenticating rotates the CSRF token and invalidates open forms
        # in other tabs, which is expected Django security behavior.
        if request.user.is_authenticated:
            return redirect(get_landing_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        return redirect_to or get_landing_url(self.request.user)


def csrf_failure(request, reason=""):
    """Explain safely when a form belongs to an older login session."""
    return render(request, "csrf_failure.html", status=403)


class NoModuleAccessView(LoginRequiredMixin, TemplateView):
    """Explain that a signed-in account has no module permissions."""

    template_name = "403.html"
    login_url = reverse_lazy("login")

    def render_to_response(self, context, **response_kwargs):
        response_kwargs.setdefault("status", 403)
        return super().render_to_response(context, **response_kwargs)


class LoginPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Require a signed-in user and a declared model or view permission."""

    login_url = reverse_lazy("login")


class ModelPermissionMixin(LoginPermissionMixin):
    """Require authentication and expose the model's CRUD permissions."""

    def get_queryset(self):
        queryset = super().get_queryset()
        return scope_to_managed_plazas(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        options = self.model._meta
        for action in ("add", "change", "delete"):
            context[f"can_{action}"] = self.request.user.has_perm(
                f"{options.app_label}.{action}_{options.model_name}"
            )
        context["permission_controlled"] = True
        return context


class ManagedPlazaFormMixin:
    """Pass the current operator so form choices stay inside assigned plazas."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class ProtectedDeleteView(DeleteView):
    """Delete an object and show a message when related records protect it."""

    def form_valid(self, form):
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar porque hay registros relacionados.",
            )
        else:
            messages.success(self.request, "Registro eliminado correctamente.")
        return HttpResponseRedirect(self.get_success_url())

import mimetypes

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView

from common.views import (
    ManagedPlazaFormMixin,
    ModelPermissionMixin,
    ProtectedDeleteView,
    managed_plazas,
)
from .forms import (
    AcreditacionForm,
    RegistroPublicoForm,
    UsuarioForm,
    VehiculoCuentaForm,
    VehiculoForm,
)
from .models import Acreditacion, Usuario, Vehiculo
from estacionamientos.models import Plaza


class AccesoUsuariosMixin(ModelPermissionMixin):
    """Exige autenticación y permisos de modelo para el CRUD de usuarios."""


class RegistroPublicoView(FormView):
    """Registra una cuenta de estacionamiento sin permisos administrativos."""

    form_class = RegistroPublicoForm
    template_name = "usuarios/registro_publico.html"

    def form_valid(self, form):
        try:
            with transaction.atomic():
                account = form.save()
                profile = Usuario.objects.create(
                    cuenta=account,
                    nombre=form.cleaned_data["nombre"].strip(),
                    apellido_paterno=form.cleaned_data["apellido_paterno"].strip(),
                    apellido_materno=form.cleaned_data["apellido_materno"].strip(),
                    correo_electronico=form.cleaned_data["email"],
                    telefono=form.cleaned_data["telefono"].strip(),
                    fecha_registro=timezone.now(),
                )
                profile.plazas.set(form.cleaned_data["plazas"])
                Vehiculo.objects.create(
                    placa=form.cleaned_data["placa"],
                    usuario=profile,
                    marca=form.cleaned_data["marca"].strip(),
                    modelo=form.cleaned_data["modelo"].strip(),
                    color=form.cleaned_data["color"].strip(),
                )
                Acreditacion.objects.create(
                    usuario=profile,
                    tipo=Acreditacion.Tipo.DISCAPACIDAD,
                    documento="",
                    documento_imagen=form.cleaned_data["documento_imagen"],
                    estado=False,
                )
        except IntegrityError:
            form.add_error(
                None,
                "La cuenta o la placa ya se registró. Revisa los datos e inténtalo de nuevo.",
            )
            return self.form_invalid(form)

        auth_login(self.request, account)
        messages.info(
            self.request,
            "Tu cuenta quedó creada. La acreditación está pendiente de revisión administrativa.",
        )
        return redirect("usuarios:mi_cuenta")


class MiCuentaView(LoginRequiredMixin, TemplateView):
    """Muestra únicamente el perfil vinculado a la sesión actual."""

    template_name = "usuarios/mi_cuenta.html"
    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = get_object_or_404(
            Usuario.objects.prefetch_related("vehiculos"),
            cuenta=self.request.user,
        )
        vehicles = list(profile.vehiculos.all())
        accreditation = Acreditacion.objects.filter(usuario=profile).first()
        plazas = list(profile.plazas.filter(activa=True))
        context.update(
            {
                "profile": profile,
                "vehicles": vehicles,
                "vehicle_count": len(vehicles),
                "can_add_vehicle": len(vehicles) < 3,
                "plazas": plazas,
                "accreditation": accreditation,
                "can_use_accessible_parking": (
                    profile.estado
                    and any(vehicle.estado for vehicle in vehicles)
                    and bool(plazas)
                    and accreditation is not None
                    and accreditation.esta_vigente()
                ),
            }
        )
        return context


class MiVehiculoCreateView(LoginRequiredMixin, CreateView):
    """Adds a car only to the signed-in person's own profile, up to three."""

    form_class = VehiculoCuentaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:mi_cuenta")
    login_url = reverse_lazy("login")
    extra_context = {"title": "Agregar vehículo a mi cuenta"}

    def get_profile(self):
        return get_object_or_404(Usuario, cuenta=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["profile"] = self.get_profile()
        return kwargs

    def form_valid(self, form):
        form.instance.usuario = self.get_profile()
        try:
            response = super().form_valid(form)
        except ValidationError as error:
            form.add_error(None, error)
            return self.form_invalid(form)
        messages.success(self.request, "El vehículo se agregó a tu cuenta.")
        return response


class PlazasDisponiblesView(View):
    """Lista solo plazas activas que coinciden con ubicación elegida."""

    def get(self, request):
        state = request.GET.get("estado", "")
        municipality = request.GET.get("municipio", "")
        plazas = Plaza.objects.filter(
            estado=state,
            municipio=municipality,
            activa=True,
        ).order_by("nombre")
        return JsonResponse(
            {
                "plazas": [
                    {"id": plaza.pk, "nombre": plaza.nombre}
                    for plaza in plazas
                ]
            }
        )


class DocumentoAcreditacionView(LoginRequiredMixin, View):
    """Sirve el documento solo a su titular o a un operador de sus plazas."""

    login_url = reverse_lazy("login")

    def get(self, request, pk):
        accreditation = get_object_or_404(
            Acreditacion.objects.select_related("usuario", "usuario__cuenta")
            .prefetch_related("usuario__plazas"),
            pk=pk,
        )
        is_owner = accreditation.usuario.cuenta_id == request.user.pk
        can_review = (
            request.user.is_superuser
            or (
                request.user.has_perm("usuarios.view_acreditacion")
                and accreditation.usuario.plazas.filter(
                    pk__in=managed_plazas(request.user)
                ).exists()
            )
        )
        if not (is_owner or can_review):
            raise PermissionDenied("No puedes consultar este documento.")
        if not accreditation.documento_imagen:
            raise Http404

        response = FileResponse(
            accreditation.documento_imagen.open("rb"),
            content_type=mimetypes.guess_type(accreditation.documento_imagen.name)[0]
            or "application/octet-stream",
        )
        response["Content-Disposition"] = "inline"
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response


class UsuarioListView(AccesoUsuariosMixin, ListView):
    """Lista usuarios para quien tenga permiso de lectura."""
    model = Usuario
    permission_required = "usuarios.view_usuario"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    extra_context = {
        "title": "Usuarios",
        "create_url": "usuarios:usuario_create",
        "update_url": "usuarios:usuario_update",
        "delete_url": "usuarios:usuario_delete",
    }


class UsuarioCreateView(ManagedPlazaFormMixin, AccesoUsuariosMixin, CreateView):
    """Crea usuarios con el permiso de alta del modelo."""
    model = Usuario
    permission_required = "usuarios.add_usuario"
    form_class = UsuarioForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "Crear usuario"}


class UsuarioUpdateView(ManagedPlazaFormMixin, AccesoUsuariosMixin, UpdateView):
    """Edita usuarios con el permiso de cambio del modelo."""
    model = Usuario
    permission_required = "usuarios.change_usuario"
    form_class = UsuarioForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "Editar usuario"}


class UsuarioDeleteView(AccesoUsuariosMixin, ProtectedDeleteView):
    """Elimina usuarios con el permiso de borrado del modelo."""
    model = Usuario
    permission_required = "usuarios.delete_usuario"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "usuario"}


class VehiculoListView(AccesoUsuariosMixin, ListView):
    """Lista vehículos para quien tenga permiso de lectura."""
    model = Vehiculo
    permission_required = "usuarios.view_vehiculo"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    queryset = Vehiculo.objects.select_related("usuario")
    extra_context = {
        "title": "Vehículos",
        "create_url": "usuarios:vehiculo_create",
        "update_url": "usuarios:vehiculo_update",
        "delete_url": "usuarios:vehiculo_delete",
    }


class VehiculoCreateView(ManagedPlazaFormMixin, AccesoUsuariosMixin, CreateView):
    """Crea vehículos con el permiso de alta del modelo."""
    model = Vehiculo
    permission_required = "usuarios.add_vehiculo"
    form_class = VehiculoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "Crear vehículo"}


class VehiculoUpdateView(ManagedPlazaFormMixin, AccesoUsuariosMixin, UpdateView):
    """Edita vehículos con el permiso de cambio del modelo."""
    model = Vehiculo
    permission_required = "usuarios.change_vehiculo"
    form_class = VehiculoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "Editar vehículo"}


class VehiculoDeleteView(AccesoUsuariosMixin, ProtectedDeleteView):
    """Elimina vehículos con el permiso de borrado del modelo."""
    model = Vehiculo
    permission_required = "usuarios.delete_vehiculo"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "vehículo"}


class AcreditacionListView(AccesoUsuariosMixin, ListView):
    """Lista acreditaciones necesarias para autorizar accesos."""

    model = Acreditacion
    permission_required = "usuarios.view_acreditacion"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    queryset = Acreditacion.objects.select_related("usuario")
    extra_context = {
        "title": "Acreditaciones",
        "create_url": "usuarios:acreditacion_create",
        "update_url": "usuarios:acreditacion_update",
        "delete_url": "usuarios:acreditacion_delete",
    }


class AcreditacionCreateView(ManagedPlazaFormMixin, AccesoUsuariosMixin, CreateView):
    """Registra y aprueba acreditaciones con los permisos del modelo."""

    model = Acreditacion
    permission_required = "usuarios.add_acreditacion"
    form_class = AcreditacionForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:acreditacion_list")
    extra_context = {"title": "Crear acreditación"}


class AcreditacionUpdateView(ManagedPlazaFormMixin, AccesoUsuariosMixin, UpdateView):
    """Actualiza el estado y vigencia de una acreditación."""

    model = Acreditacion
    permission_required = "usuarios.change_acreditacion"
    form_class = AcreditacionForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:acreditacion_list")
    extra_context = {"title": "Editar acreditación"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["accreditation_document_url"] = (
            reverse("usuarios:acreditacion_documento", args=[self.object.pk])
            if self.object.documento_imagen
            else None
        )
        context["legacy_document_reference"] = self.object.documento
        context["review_plazas"] = self.object.usuario.plazas.filter(
            pk__in=managed_plazas(self.request.user)
        )
        return context


class AcreditacionDeleteView(AccesoUsuariosMixin, ProtectedDeleteView):
    """Elimina acreditaciones que no estén protegidas por el historial."""

    model = Acreditacion
    permission_required = "usuarios.delete_acreditacion"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("usuarios:acreditacion_list")
    extra_context = {"title": "acreditación"}

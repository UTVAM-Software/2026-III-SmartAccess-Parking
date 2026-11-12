"""Vistas CRUD protegidas del módulo Registros e Incidencias."""

import mimetypes

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import ProtectedError
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, FormView, ListView, UpdateView

from .forms import CapturaPlacaForm, IncidenciaForm, IntentoAccesoForm, RegistroUsoForm
from .models import CapturaPlaca, Incidencia, IntentoAcceso, RegistroUso
from .services import process_manual_access, register_exit


class AccesoRegistrosMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Exige autenticación y permiso del modelo antes de atender una vista."""

    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        """Expone permisos de CRUD para controlar las acciones de las listas."""
        context = super().get_context_data(**kwargs)
        options = self.model._meta
        user = self.request.user

        context["permission_controlled"] = True
        for action in ("add", "change", "delete"):
            context[f"can_{action}"] = user.has_perm(
                f"{options.app_label}.{action}_{options.model_name}"
            )

        return context


class EliminacionProtegidaView(DeleteView):
    """Gestiona eliminaciones y reporta relaciones protegidas."""

    def form_valid(self, form):
        """Elimina el objeto o informa si una relación protegida lo impide."""
        try:
            self.object.delete()
        except ProtectedError:
            messages.error(
                self.request,
                "No se puede eliminar porque existen registros relacionados que lo protegen.",
            )
        else:
            messages.success(self.request, "Registro eliminado correctamente.")

        return HttpResponseRedirect(self.get_success_url())


class RegistroUsoListView(AccesoRegistrosMixin, ListView):
    """Lista los registros de uso para usuarios con permiso de lectura."""
    model = RegistroUso
    permission_required = "registros.view_registrouso"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Registros de uso",
        "create_url": "registros:registro_create",
        "update_url": "registros:registro_update",
        "delete_url": "registros:registro_delete",
        "exit_url": "registros:registro_salida",
    }

    def get_context_data(self, **kwargs):
        """Separa permisos de operación de los de mantenimiento histórico."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["create_url"] = "registros:intento_create"
        context["can_add"] = user.has_perm("registros.add_intentoacceso")
        context["can_change"] = user.has_perm(
            "registros.change_registrouso_history"
        )
        context["can_delete"] = user.has_perm(
            "registros.delete_registrouso_history"
        )
        context["can_exit"] = user.has_perm("registros.change_registrouso")
        return context


class RegistroUsoCreateView(AccesoRegistrosMixin, View):
    """Redirige altas al flujo que valida acceso, crea boleto y auditoría."""

    model = RegistroUso
    permission_required = "registros.add_intentoacceso"

    def get(self, request, *args, **kwargs):
        """Inicia la captura manual de un intento, no una entrada directa."""
        return HttpResponseRedirect(reverse_lazy("registros:intento_create"))

    def post(self, request, *args, **kwargs):
        """No acepta altas directas que omitan acreditación y autorización."""
        messages.info(
            request,
            "Los registros de uso se generan tras autorizar un intento de acceso.",
        )
        return HttpResponseRedirect(reverse_lazy("registros:intento_create"))


class RegistroUsoUpdateView(AccesoRegistrosMixin, SuccessMessageMixin, UpdateView):
    """Actualiza un registro de uso con permiso de cambio."""
    model = RegistroUso
    permission_required = "registros.change_registrouso_history"
    form_class = RegistroUsoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:registro_list")
    success_message = "Registro de uso actualizado correctamente."
    extra_context = {"title": "Editar registro de uso"}


class RegistroUsoDeleteView(AccesoRegistrosMixin, EliminacionProtegidaView):
    """Elimina un registro de uso con permiso de borrado."""
    model = RegistroUso
    permission_required = "registros.delete_registrouso_history"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:registro_list")
    extra_context = {"title": "registro de uso"}


class CapturaPlacaListView(AccesoRegistrosMixin, ListView):
    """Lista capturas de placa para usuarios con permiso de lectura."""
    model = CapturaPlaca
    permission_required = "registros.view_capturaplaca"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Capturas de placa",
        "create_url": "registros:captura_create",
        "update_url": "registros:captura_update",
        "delete_url": "registros:captura_delete",
    }


class CapturaPlacaCreateView(AccesoRegistrosMixin, SuccessMessageMixin, CreateView):
    """Crea una captura de placa con permiso de alta."""
    model = CapturaPlaca
    permission_required = "registros.add_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa creada correctamente."
    extra_context = {"title": "Crear captura de placa"}


class CapturaPlacaUpdateView(AccesoRegistrosMixin, SuccessMessageMixin, UpdateView):
    """Actualiza una captura de placa con permiso de cambio."""
    model = CapturaPlaca
    permission_required = "registros.change_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa actualizada correctamente."
    extra_context = {"title": "Editar captura de placa"}


class CapturaPlacaDeleteView(AccesoRegistrosMixin, EliminacionProtegidaView):
    """Elimina una captura de placa con permiso de borrado."""
    model = CapturaPlaca
    permission_required = "registros.delete_capturaplaca"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:captura_list")
    extra_context = {"title": "captura de placa"}


class IncidenciaListView(AccesoRegistrosMixin, ListView):
    """Lista incidencias para usuarios con permiso de lectura."""
    model = Incidencia
    permission_required = "registros.view_incidencia"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Incidencias",
        "create_url": "registros:incidencia_create",
        "update_url": "registros:incidencia_update",
        "delete_url": "registros:incidencia_delete",
    }


class IncidenciaCreateView(AccesoRegistrosMixin, SuccessMessageMixin, CreateView):
    """Crea una incidencia con permiso de alta."""
    model = Incidencia
    permission_required = "registros.add_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia creada correctamente."
    extra_context = {"title": "Crear incidencia"}


class IncidenciaUpdateView(AccesoRegistrosMixin, SuccessMessageMixin, UpdateView):
    """Actualiza una incidencia con permiso de cambio."""
    model = Incidencia
    permission_required = "registros.change_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia actualizada correctamente."
    extra_context = {"title": "Editar incidencia"}


class IncidenciaDeleteView(AccesoRegistrosMixin, EliminacionProtegidaView):
    """Elimina una incidencia con permiso de borrado."""
    model = Incidencia
    permission_required = "registros.delete_incidencia"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:incidencia_list")
    extra_context = {"title": "incidencia"}


class IntentoAccesoListView(AccesoRegistrosMixin, ListView):
    """Lista decisiones de acceso a operadores con permiso de lectura."""

    model = IntentoAcceso
    permission_required = "registros.view_intentoacceso"
    template_name = "registros/intentos_lista.html"
    context_object_name = "objects"
    ordering = ("-fecha_hora", "-id_intento")
    def get_queryset(self):
        """Carga relaciones para presentar el historial sin consultas repetidas."""
        return super().get_queryset().select_related(
            "operador",
            "acreditacion",
        )

    extra_context = {
        "title": "Intentos de acceso",
        "create_url": "registros:intento_create",
    }


class IntentoAccesoCreateView(AccesoRegistrosMixin, FormView):
    """Registra una simulación manual sin cámara ni OCR."""

    model = IntentoAcceso
    permission_required = "registros.add_intentoacceso"
    form_class = IntentoAccesoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:intento_list")
    extra_context = {"title": "Simulación manual de acceso"}

    def form_valid(self, form):
        """Ejecuta la regla de negocio y comunica autorización o rechazo."""
        attempt = process_manual_access(
            operator=self.request.user,
            placa_capturada=form.cleaned_data["placa_capturada"],
            imagen=form.cleaned_data.get("imagen"),
        )
        if attempt.resultado == IntentoAcceso.Resultado.AUTORIZADO:
            messages.success(
                self.request,
                f"Acceso autorizado. Boleto {attempt.boleto.numero_boleto}.",
            )
        else:
            messages.warning(
                self.request,
                f"Acceso rechazado: {attempt.motivo_rechazo}",
            )
        return super().form_valid(form)


class IntentoAccesoImagenView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Entrega una foto privada solo a operadores con permiso de lectura."""

    permission_required = "registros.view_intentoacceso"
    login_url = reverse_lazy("login")

    def get(self, request, pk):
        """Devuelve la fotografía sin exponerla por MEDIA_URL."""
        attempt = get_object_or_404(IntentoAcceso, pk=pk)
        if not attempt.imagen:
            raise Http404
        content_type = mimetypes.guess_type(attempt.imagen.name)[0]
        response = FileResponse(
            attempt.imagen.open("rb"),
            content_type=content_type or "application/octet-stream",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response


class CapturaPlacaImagenView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Entrega evidencia privada a usuarios con permiso de lectura de capturas."""

    permission_required = "registros.view_capturaplaca"
    login_url = reverse_lazy("login")

    def get(self, request, pk):
        """Devuelve la fotografía sin exponerla por MEDIA_URL."""
        capture = get_object_or_404(CapturaPlaca, pk=pk)
        if not capture.imagen:
            raise Http404
        content_type = mimetypes.guess_type(capture.imagen.name)[0]
        response = FileResponse(
            capture.imagen.open("rb"),
            content_type=content_type or "application/octet-stream",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response


class RegistroSalidaView(AccesoRegistrosMixin, View):
    """Registra por POST la salida de un vehículo autorizado."""

    model = RegistroUso
    permission_required = "registros.change_registrouso"
    success_url = reverse_lazy("registros:registro_list")

    def post(self, request, pk):
        """Cierra el uso y libera el cajón transaccionalmente."""
        register_exit(operator=request.user, registro_id=pk)
        messages.success(request, "Salida registrada y cajón liberado.")
        return HttpResponseRedirect(self.success_url)

"""Vistas CRUD protegidas del módulo Registros e Incidencias."""

import mimetypes
import hashlib
import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

"""Vistas CRUD protegidas del módulo Registros e Incidencias."""

import mimetypes
import hashlib
import time
from decimal import Decimal

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

from common.views import (
    LoginPermissionMixin,
    ManagedPlazaFormMixin,
    ModelPermissionMixin,
    ProtectedDeleteView,
    managed_plazas,
    scope_to_managed_plazas,
)
from .forms import CapturaPlacaForm, IncidenciaForm, IntentoAccesoForm, RegistroUsoForm
from .models import CapturaPlaca, Incidencia, IntentoAcceso, RegistroUso
from .ocr import OCRUnavailable, read_plate
from .services import register_exit, validate_disability_plate


class AccesoRegistrosMixin(ModelPermissionMixin):
    """Exige autenticación y permiso del modelo antes de atender una vista."""

class RegistroUsoListView(AccesoRegistrosMixin, ListView):
    """Lista los registros de uso para usuarios con permiso de lectura."""
    model = RegistroUso
    permission_required = "registros.view_registrouso"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    queryset = RegistroUso.objects.select_related("vehiculo", "estacionamiento")
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


class RegistroUsoUpdateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Actualiza un registro de uso con permiso de cambio."""
    model = RegistroUso
    permission_required = "registros.change_registrouso_history"
    form_class = RegistroUsoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:registro_list")
    success_message = "Registro de uso actualizado correctamente."
    extra_context = {"title": "Editar registro de uso"}


class RegistroUsoDeleteView(AccesoRegistrosMixin, ProtectedDeleteView):
    """Elimina un registro de uso con permiso de borrado."""
    model = RegistroUso
    permission_required = "registros.delete_registrouso_history"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:registro_list")
    extra_context = {"title": "registro de uso"}

    def form_valid(self, form):
        if self.object.hora_salida is None:
            messages.error(
                self.request,
                "No se puede eliminar una entrada activa; registra su salida primero.",
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)


class CapturaPlacaListView(AccesoRegistrosMixin, ListView):
    """Lista capturas de placa para usuarios con permiso de lectura."""
    model = CapturaPlaca
    permission_required = "registros.view_capturaplaca"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    queryset = CapturaPlaca.objects.select_related(
        "registro_uso",
        "registro_uso__vehiculo",
    )
    extra_context = {
        "title": "Capturas de placa",
        "create_url": "registros:captura_create",
        "update_url": "registros:captura_update",
        "delete_url": "registros:captura_delete",
    }


class CapturaPlacaCreateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Crea una captura de placa con permiso de alta."""
    model = CapturaPlaca
    permission_required = "registros.add_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa creada correctamente."
    extra_context = {"title": "Crear captura de placa"}


class CapturaPlacaUpdateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Actualiza una captura de placa con permiso de cambio."""
    model = CapturaPlaca
    permission_required = "registros.change_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa actualizada correctamente."
    extra_context = {"title": "Editar captura de placa"}


class CapturaPlacaDeleteView(AccesoRegistrosMixin, ProtectedDeleteView):
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
    paginate_by = 25
    queryset = Incidencia.objects.select_related(
        "registro_uso",
        "registro_uso__vehiculo",
    )
    extra_context = {
        "title": "Incidencias",
        "create_url": "registros:incidencia_create",
        "update_url": "registros:incidencia_update",
        "delete_url": "registros:incidencia_delete",
    }


class IncidenciaCreateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Crea una incidencia con permiso de alta."""
    model = Incidencia
    permission_required = "registros.add_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia creada correctamente."
    extra_context = {"title": "Crear incidencia"}


class IncidenciaUpdateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Actualiza una incidencia con permiso de cambio."""
    model = Incidencia
    permission_required = "registros.change_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia actualizada correctamente."
    extra_context = {"title": "Editar incidencia"}


class IncidenciaDeleteView(AccesoRegistrosMixin, ProtectedDeleteView):
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
    paginate_by = 25
    def get_queryset(self):
        """Carga relaciones para presentar el historial sin consultas repetidas."""
        return super().get_queryset().select_related(
            "operador",
            "acreditacion",
            "plaza",
        )

    extra_context = {
        "title": "Intentos de acceso",
        "create_url": "registros:intento_create",
    }


class IntentoAccesoCreateView(ManagedPlazaFormMixin, AccesoRegistrosMixin, FormView):
    """Let plaza access staff check whether a vehicle is currently authorized."""

    model = IntentoAcceso
    permission_required = "registros.validate_plate_access"
    form_class = IntentoAccesoForm
    template_name = "registros/validacion_placa.html"
    success_url = reverse_lazy("registros:intento_create")
    extra_context = {"title": "Revisión de placas"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["assigned_plazas"] = managed_plazas(self.request.user)
        context["last_plate_check"] = self.request.session.pop(
            "last_plate_check",
            None,
        )
        return context

    def form_valid(self, form):
        """Ejecuta la regla de negocio y comunica autorización o rechazo."""
        plate = form.cleaned_data["placa_capturada"]
        plaza = form.cleaned_data["plaza"]
        image = form.cleaned_data.get("imagen")
        capture_source = IntentoAcceso.FuenteCaptura.MANUAL
        ocr_confidence = None
        pending_key = f"ocr_pending_{self.request.user.pk}"

        if not plate and image:
            try:
                reading = read_plate(image)
            except OCRUnavailable as error:
                form.add_error("imagen", str(error))
                return self.form_invalid(form)
            if not reading:
                form.add_error(
                    "placa_capturada",
                    "No se distinguió una placa. Escribe la placa manualmente.",
                )
                return self.form_invalid(form)
            if reading.confianza < 60:
                form.add_error(
                    "placa_capturada",
                    f"La lectura sugirió {reading.placa} con confianza baja "
                    f"({reading.confianza:.0f}%). Revísala y escríbela manualmente.",
                )
                return self.form_invalid(form)

            image.seek(0)
            image_hash = hashlib.sha256(image.read()).hexdigest()
            image.seek(0)
            self.request.session[pending_key] = {
                "plate": reading.placa,
                "plaza_id": plaza.pk,
                "confidence": str(round(reading.confianza, 2)),
                "image_hash": image_hash,
                "created": time.time(),
            }
            form.add_error(
                "placa_capturada",
                f"OCR propuso {reading.placa} ({reading.confianza:.0f}%). "
                "Revisa la foto, escribe la placa para confirmarla y vuelve a adjuntar la misma imagen.",
            )
            return self.form_invalid(form)

        if plate and image:
            pending = self.request.session.pop(pending_key, None)
            image.seek(0)
            image_hash = hashlib.sha256(image.read()).hexdigest()
            image.seek(0)
            if (
                pending
                and time.time() - pending["created"] <= 600
                and pending["plate"] == plate
                and pending["plaza_id"] == plaza.pk
                and pending["image_hash"] == image_hash
            ):
                capture_source = IntentoAcceso.FuenteCaptura.OCR
                ocr_confidence = Decimal(pending["confidence"])
                messages.info(
                    self.request,
                    f"Confirmaste la lectura OCR de {plate} "
                    f"({ocr_confidence:.0f}% de confianza).",
                )

        attempt = validate_disability_plate(
            operator=self.request.user,
            plaza=plaza,
            placa_capturada=plate,
            imagen=image,
            fuente_captura=capture_source,
            confianza_ocr=ocr_confidence,
        )
        authorized = attempt.resultado == IntentoAcceso.Resultado.AUTORIZADO
        self.request.session["last_plate_check"] = {
            "authorized": authorized,
            "plate": attempt.placa_capturada,
            "plaza": plaza.nombre,
            "message": (
                "La placa está vinculada a una acreditación vigente para esta plaza."
                if authorized
                else attempt.motivo_rechazo
            ),
        }
        return super().form_valid(form)


class IntentoAccesoImagenView(LoginPermissionMixin, View):
    """Entrega una foto privada solo a operadores con permiso de lectura."""

    permission_required = "registros.view_intentoacceso"
    login_url = reverse_lazy("login")

    def get(self, request, pk):
        """Devuelve la fotografía sin exponerla por MEDIA_URL."""
        attempt = get_object_or_404(
            scope_to_managed_plazas(IntentoAcceso.objects.all(), request.user),
            pk=pk,
        )
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


class CapturaPlacaImagenView(LoginPermissionMixin, View):
    """Entrega evidencia privada a usuarios con permiso de lectura de capturas."""

    permission_required = "registros.view_capturaplaca"
    login_url = reverse_lazy("login")

    def get(self, request, pk):
        """Devuelve la fotografía sin exponerla por MEDIA_URL."""
        capture = get_object_or_404(
            scope_to_managed_plazas(CapturaPlaca.objects.all(), request.user),
            pk=pk,
        )
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
        try:
            use = register_exit(operator=request.user, registro_id=pk)
        except RegistroUso.DoesNotExist as error:
            raise Http404("No existe ese registro de uso.") from error
        except ValidationError as error:
            messages.warning(request, " ".join(error.messages))
            return HttpResponseRedirect(self.success_url)

        use.estacionamiento.refresh_from_db(fields=("estado",))
        if use.estacionamiento.estado:
            messages.success(request, "Salida registrada y cajón disponible.")
        else:
            messages.success(
                request,
                "Salida registrada. El cajón sigue bloqueado por su estado o sensor.",
            )
        return HttpResponseRedirect(self.success_url)
from .forms import CapturaPlacaForm, IncidenciaForm, IntentoAccesoForm, RegistroUsoForm
from .models import CapturaPlaca, Incidencia, IntentoAcceso, RegistroUso
from .ocr import OCRUnavailable, read_plate
from .services import register_exit, validate_disability_plate


class AccesoRegistrosMixin(ModelPermissionMixin):
    """Exige autenticación y permiso del modelo antes de atender una vista."""

class RegistroUsoListView(AccesoRegistrosMixin, ListView):
    """Lista los registros de uso para usuarios con permiso de lectura."""
    model = RegistroUso
    permission_required = "registros.view_registrouso"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    queryset = RegistroUso.objects.select_related("vehiculo", "estacionamiento")
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


class RegistroUsoUpdateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Actualiza un registro de uso con permiso de cambio."""
    model = RegistroUso
    permission_required = "registros.change_registrouso_history"
    form_class = RegistroUsoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:registro_list")
    success_message = "Registro de uso actualizado correctamente."
    extra_context = {"title": "Editar registro de uso"}


class RegistroUsoDeleteView(AccesoRegistrosMixin, ProtectedDeleteView):
    """Elimina un registro de uso con permiso de borrado."""
    model = RegistroUso
    permission_required = "registros.delete_registrouso_history"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("registros:registro_list")
    extra_context = {"title": "registro de uso"}

    def form_valid(self, form):
        if self.object.hora_salida is None:
            messages.error(
                self.request,
                "No se puede eliminar una entrada activa; registra su salida primero.",
            )
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)


class CapturaPlacaListView(AccesoRegistrosMixin, ListView):
    """Lista capturas de placa para usuarios con permiso de lectura."""
    model = CapturaPlaca
    permission_required = "registros.view_capturaplaca"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    queryset = CapturaPlaca.objects.select_related(
        "registro_uso",
        "registro_uso__vehiculo",
    )
    extra_context = {
        "title": "Capturas de placa",
        "create_url": "registros:captura_create",
        "update_url": "registros:captura_update",
        "delete_url": "registros:captura_delete",
    }


class CapturaPlacaCreateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Crea una captura de placa con permiso de alta."""
    model = CapturaPlaca
    permission_required = "registros.add_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa creada correctamente."
    extra_context = {"title": "Crear captura de placa"}


class CapturaPlacaUpdateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Actualiza una captura de placa con permiso de cambio."""
    model = CapturaPlaca
    permission_required = "registros.change_capturaplaca"
    form_class = CapturaPlacaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:captura_list")
    success_message = "Captura de placa actualizada correctamente."
    extra_context = {"title": "Editar captura de placa"}


class CapturaPlacaDeleteView(AccesoRegistrosMixin, ProtectedDeleteView):
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
    paginate_by = 25
    queryset = Incidencia.objects.select_related(
        "registro_uso",
        "registro_uso__vehiculo",
    )
    extra_context = {
        "title": "Incidencias",
        "create_url": "registros:incidencia_create",
        "update_url": "registros:incidencia_update",
        "delete_url": "registros:incidencia_delete",
    }


class IncidenciaCreateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    CreateView,
):
    """Crea una incidencia con permiso de alta."""
    model = Incidencia
    permission_required = "registros.add_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia creada correctamente."
    extra_context = {"title": "Crear incidencia"}


class IncidenciaUpdateView(
    ManagedPlazaFormMixin,
    AccesoRegistrosMixin,
    SuccessMessageMixin,
    UpdateView,
):
    """Actualiza una incidencia con permiso de cambio."""
    model = Incidencia
    permission_required = "registros.change_incidencia"
    form_class = IncidenciaForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("registros:incidencia_list")
    success_message = "Incidencia actualizada correctamente."
    extra_context = {"title": "Editar incidencia"}


class IncidenciaDeleteView(AccesoRegistrosMixin, ProtectedDeleteView):
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
    paginate_by = 25
    def get_queryset(self):
        """Carga relaciones para presentar el historial sin consultas repetidas."""
        return super().get_queryset().select_related(
            "operador",
            "acreditacion",
            "plaza",
        )

    extra_context = {
        "title": "Intentos de acceso",
        "create_url": "registros:intento_create",
    }


class IntentoAccesoCreateView(ManagedPlazaFormMixin, AccesoRegistrosMixin, FormView):
    """Let plaza access staff check whether a vehicle is currently authorized."""

    model = IntentoAcceso
    permission_required = "registros.validate_plate_access"
    form_class = IntentoAccesoForm
    template_name = "registros/validacion_placa.html"
    success_url = reverse_lazy("registros:intento_create")
    extra_context = {"title": "Revisión de placas"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["assigned_plazas"] = managed_plazas(self.request.user)
        context["last_plate_check"] = self.request.session.pop(
            "last_plate_check",
            None,
        )
        return context

    def form_valid(self, form):
        """Ejecuta la regla de negocio y comunica autorización o rechazo."""
        plate = form.cleaned_data["placa_capturada"]
        plaza = form.cleaned_data["plaza"]
        image = form.cleaned_data.get("imagen")
        capture_source = IntentoAcceso.FuenteCaptura.MANUAL
        ocr_confidence = None
        pending_key = f"ocr_pending_{self.request.user.pk}"

        if not plate and image:
            try:
                reading = read_plate(image)
            except OCRUnavailable as error:
                form.add_error("imagen", str(error))
                return self.form_invalid(form)
            if not reading:
                form.add_error(
                    "placa_capturada",
                    "No se distinguió una placa. Escribe la placa manualmente.",
                )
                return self.form_invalid(form)
            if reading.confianza < 60:
                form.add_error(
                    "placa_capturada",
                    f"La lectura sugirió {reading.placa} con confianza baja "
                    f"({reading.confianza:.0f}%). Revísala y escríbela manualmente.",
                )
                return self.form_invalid(form)

            image.seek(0)
            image_hash = hashlib.sha256(image.read()).hexdigest()
            image.seek(0)
            self.request.session[pending_key] = {
                "plate": reading.placa,
                "plaza_id": plaza.pk,
                "confidence": str(round(reading.confianza, 2)),
                "image_hash": image_hash,
                "created": time.time(),
            }
            form.add_error(
                "placa_capturada",
                f"OCR propuso {reading.placa} ({reading.confianza:.0f}%). "
                "Revisa la foto, escribe la placa para confirmarla y vuelve a adjuntar la misma imagen.",
            )
            return self.form_invalid(form)

        if plate and image:
            pending = self.request.session.pop(pending_key, None)
            image.seek(0)
            image_hash = hashlib.sha256(image.read()).hexdigest()
            image.seek(0)
            if (
                pending
                and time.time() - pending["created"] <= 600
                and pending["plate"] == plate
                and pending["plaza_id"] == plaza.pk
                and pending["image_hash"] == image_hash
            ):
                capture_source = IntentoAcceso.FuenteCaptura.OCR
                ocr_confidence = Decimal(pending["confidence"])
                messages.info(
                    self.request,
                    f"Confirmaste la lectura OCR de {plate} "
                    f"({ocr_confidence:.0f}% de confianza).",
                )

        attempt = validate_disability_plate(
            operator=self.request.user,
            plaza=plaza,
            placa_capturada=plate,
            imagen=image,
            fuente_captura=capture_source,
            confianza_ocr=ocr_confidence,
        )
        authorized = attempt.resultado == IntentoAcceso.Resultado.AUTORIZADO
        self.request.session["last_plate_check"] = {
            "authorized": authorized,
            "plate": attempt.placa_capturada,
            "plaza": plaza.nombre,
            "message": (
                "La placa está vinculada a una acreditación vigente para esta plaza."
                if authorized
                else attempt.motivo_rechazo
            ),
        }
        return super().form_valid(form)


class IntentoAccesoImagenView(LoginPermissionMixin, View):
    """Entrega una foto privada solo a operadores con permiso de lectura."""

    permission_required = "registros.view_intentoacceso"
    login_url = reverse_lazy("login")

    def get(self, request, pk):
        """Devuelve la fotografía sin exponerla por MEDIA_URL."""
        attempt = get_object_or_404(
            scope_to_managed_plazas(IntentoAcceso.objects.all(), request.user),
            pk=pk,
        )
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


class CapturaPlacaImagenView(LoginPermissionMixin, View):
    """Entrega evidencia privada a usuarios con permiso de lectura de capturas."""

    permission_required = "registros.view_capturaplaca"
    login_url = reverse_lazy("login")

    def get(self, request, pk):
        """Devuelve la fotografía sin exponerla por MEDIA_URL."""
        capture = get_object_or_404(
            scope_to_managed_plazas(CapturaPlaca.objects.all(), request.user),
            pk=pk,
        )
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
        try:
            use = register_exit(operator=request.user, registro_id=pk)
        except RegistroUso.DoesNotExist as error:
            raise Http404("No existe ese registro de uso.") from error
        except ValidationError as error:
            messages.warning(request, " ".join(error.messages))
            return HttpResponseRedirect(self.success_url)

        use.estacionamiento.refresh_from_db(fields=("estado",))
        if use.estacionamiento.estado:
            messages.success(request, "Salida registrada y cajón disponible.")
        else:
            messages.success(
                request,
                "Salida registrada. El cajón sigue bloqueado por su estado o sensor.",
            )
        return HttpResponseRedirect(self.success_url)

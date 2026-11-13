from django.urls import reverse_lazy
from django.db.models import Prefetch
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from common.views import (
    LoginPermissionMixin,
    ManagedPlazaFormMixin,
    ModelPermissionMixin,
    ProtectedDeleteView,
    managed_plazas,
)
from .forms import EstacionamientoForm, SensorForm
from .models import Estacionamiento, Plaza, Sensor
from .services import synchronize_availability


class AccesoEstacionamientosMixin(ModelPermissionMixin):
    """Exige autenticación y permisos CRUD para cajones y sensores."""


class SynchronizeSpaceAfterSaveMixin:
    """Recalcula disponibilidad al guardar la configuración del cajón."""

    def form_valid(self, form):
        response = super().form_valid(form)
        synchronize_availability(self.object.pk)
        self.object.refresh_from_db(fields=("estado",))
        return response


class SynchronizeSensorAfterSaveMixin:
    """Recalcula los cajones al crear, mover o editar un sensor."""

    def form_valid(self, form):
        old_space_id = (
            self.object.estacionamiento_id if getattr(self, "object", None) else None
        )
        response = super().form_valid(form)
        space_ids = {old_space_id, self.object.estacionamiento_id} - {None}
        for space_id in space_ids:
            synchronize_availability(space_id)
        return response


class EstacionamientoListView(AccesoEstacionamientosMixin, ListView):
    """Lista cajones para usuarios con permiso de lectura."""
    model = Estacionamiento
    permission_required = "estacionamientos.view_estacionamiento"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    extra_context = {
        "title": "Estacionamientos",
        "create_url": "estacionamientos:estacionamiento_create",
        "update_url": "estacionamientos:estacionamiento_update",
        "delete_url": "estacionamientos:estacionamiento_delete",
    }


class EstacionamientoCreateView(
    SynchronizeSpaceAfterSaveMixin,
    ManagedPlazaFormMixin,
    AccesoEstacionamientosMixin,
    CreateView,
):
    """Crea cajones con el permiso de alta del modelo."""
    model = Estacionamiento
    permission_required = "estacionamientos.add_estacionamiento"
    form_class = EstacionamientoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "Crear estacionamiento"}


class EstacionamientoUpdateView(
    SynchronizeSpaceAfterSaveMixin,
    ManagedPlazaFormMixin,
    AccesoEstacionamientosMixin,
    UpdateView,
):
    """Edita cajones con el permiso de cambio del modelo."""
    model = Estacionamiento
    permission_required = "estacionamientos.change_estacionamiento"
    form_class = EstacionamientoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "Editar estacionamiento"}


class EstacionamientoDeleteView(AccesoEstacionamientosMixin, ProtectedDeleteView):
    """Elimina cajones con el permiso de borrado del modelo."""
    model = Estacionamiento
    permission_required = "estacionamientos.delete_estacionamiento"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("estacionamientos:estacionamiento_list")
    extra_context = {"title": "estacionamiento"}


class SensorListView(AccesoEstacionamientosMixin, ListView):
    """Lista sensores para usuarios con permiso de lectura."""
    model = Sensor
    permission_required = "estacionamientos.view_sensor"
    template_name = "crud/list.html"
    context_object_name = "objects"
    paginate_by = 25
    queryset = Sensor.objects.select_related("estacionamiento")
    extra_context = {
        "title": "Sensores",
        "create_url": "estacionamientos:sensor_create",
        "update_url": "estacionamientos:sensor_update",
        "delete_url": "estacionamientos:sensor_delete",
    }


class SensorCreateView(
    SynchronizeSensorAfterSaveMixin,
    ManagedPlazaFormMixin,
    AccesoEstacionamientosMixin,
    CreateView,
):
    """Crea sensores con el permiso de alta del modelo."""
    model = Sensor
    permission_required = "estacionamientos.add_sensor"
    form_class = SensorForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "Crear sensor"}


class SensorUpdateView(
    SynchronizeSensorAfterSaveMixin,
    ManagedPlazaFormMixin,
    AccesoEstacionamientosMixin,
    UpdateView,
):
    """Edita sensores con el permiso de cambio del modelo."""
    model = Sensor
    permission_required = "estacionamientos.change_sensor"
    form_class = SensorForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "Editar sensor"}


class SensorDeleteView(AccesoEstacionamientosMixin, ProtectedDeleteView):
    """Elimina sensores con el permiso de borrado del modelo."""
    model = Sensor
    permission_required = "estacionamientos.delete_sensor"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("estacionamientos:sensor_list")
    extra_context = {"title": "sensor"}

    def form_valid(self, form):
        space_id = self.object.estacionamiento_id
        response = super().form_valid(form)
        if not Sensor.objects.filter(pk=self.object.pk).exists():
            synchronize_availability(space_id)
        return response


class PanelOperacionView(LoginPermissionMixin, TemplateView):
    """Dashboard de operación con datos limitados a las plazas asignadas."""

    permission_required = "estacionamientos.view_operational_dashboard"
    template_name = "estacionamientos/panel_operacion.html"

    def get_context_data(self, **kwargs):
        from registros.models import Incidencia, IntentoAcceso
        from usuarios.models import Acreditacion

        context = super().get_context_data(**kwargs)
        plazas = managed_plazas(self.request.user)
        selected_id = self.request.GET.get("plaza")
        selected = plazas.filter(pk=selected_id).first() if selected_id else None
        scope = plazas.filter(pk=selected.pk) if selected else plazas

        spaces = Estacionamiento.objects.filter(plaza__in=scope)
        attempts = IntentoAcceso.objects.filter(plaza__in=scope)
        pending_accreditations = (
            Acreditacion.objects.filter(
                usuario__plazas__in=scope,
                estado=False,
            )
            .select_related("usuario")
            .prefetch_related(
                Prefetch("usuario__plazas", queryset=scope)
            )
            .distinct()
            .order_by("pk")
        )
        recent_incidents = (
            Incidencia.objects.filter(
                registro_uso__estacionamiento__plaza__in=scope,
            )
            .select_related(
                "registro_uso",
                "registro_uso__estacionamiento",
                "registro_uso__vehiculo",
            )
            .order_by("-fecha_hora")[:8]
        )
        recent_attempts = attempts.select_related(
            "usuario",
            "vehiculo",
            "operador",
            "plaza",
        ).order_by("-fecha_hora", "-pk")[:8]

        context.update(
            {
                "plazas": plazas,
                "selected_plaza": selected,
                "space_count": spaces.count(),
                "available_count": spaces.filter(activo=True, estado=True).count(),
                "occupied_count": spaces.filter(activo=True, estado=False).count(),
                "pending_accreditations": pending_accreditations[:8],
                "pending_accreditation_count": pending_accreditations.count(),
                "incident_count": Incidencia.objects.filter(
                    registro_uso__estacionamiento__plaza__in=scope,
                    estado=True,
                ).count(),
                "recent_incidents": recent_incidents,
                "recent_attempts": recent_attempts,
                "attempt_count": attempts.count(),
            }
        )
        return context

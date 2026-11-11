from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import AcreditacionForm, UsuarioForm, VehiculoForm
from .models import Acreditacion, Usuario, Vehiculo


class AccesoUsuariosMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Exige autenticación y permisos de modelo para el CRUD de usuarios."""

    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        """Expone permisos CRUD para que la lista oculte acciones no autorizadas."""
        context = super().get_context_data(**kwargs)
        options = self.model._meta
        for action in ("add", "change", "delete"):
            context[f"can_{action}"] = self.request.user.has_perm(
                f"{options.app_label}.{action}_{options.model_name}"
            )
        context["permission_controlled"] = True
        return context


class EliminacionProtegidaView(DeleteView):
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


class UsuarioListView(AccesoUsuariosMixin, ListView):
    """Lista usuarios para quien tenga permiso de lectura."""
    model = Usuario
    permission_required = "usuarios.view_usuario"
    template_name = "crud/list.html"
    context_object_name = "objects"
    extra_context = {
        "title": "Usuarios",
        "create_url": "usuarios:usuario_create",
        "update_url": "usuarios:usuario_update",
        "delete_url": "usuarios:usuario_delete",
    }


class UsuarioCreateView(AccesoUsuariosMixin, CreateView):
    """Crea usuarios con el permiso de alta del modelo."""
    model = Usuario
    permission_required = "usuarios.add_usuario"
    form_class = UsuarioForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "Crear usuario"}


class UsuarioUpdateView(AccesoUsuariosMixin, UpdateView):
    """Edita usuarios con el permiso de cambio del modelo."""
    model = Usuario
    permission_required = "usuarios.change_usuario"
    form_class = UsuarioForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:usuario_list")
    extra_context = {"title": "Editar usuario"}


class UsuarioDeleteView(AccesoUsuariosMixin, EliminacionProtegidaView):
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
    extra_context = {
        "title": "Vehículos",
        "create_url": "usuarios:vehiculo_create",
        "update_url": "usuarios:vehiculo_update",
        "delete_url": "usuarios:vehiculo_delete",
    }


class VehiculoCreateView(AccesoUsuariosMixin, CreateView):
    """Crea vehículos con el permiso de alta del modelo."""
    model = Vehiculo
    permission_required = "usuarios.add_vehiculo"
    form_class = VehiculoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "Crear vehículo"}


class VehiculoUpdateView(AccesoUsuariosMixin, UpdateView):
    """Edita vehículos con el permiso de cambio del modelo."""
    model = Vehiculo
    permission_required = "usuarios.change_vehiculo"
    form_class = VehiculoForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:vehiculo_list")
    extra_context = {"title": "Editar vehículo"}


class VehiculoDeleteView(AccesoUsuariosMixin, EliminacionProtegidaView):
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
    queryset = Acreditacion.objects.select_related("usuario")
    extra_context = {
        "title": "Acreditaciones",
        "create_url": "usuarios:acreditacion_create",
        "update_url": "usuarios:acreditacion_update",
        "delete_url": "usuarios:acreditacion_delete",
    }


class AcreditacionCreateView(AccesoUsuariosMixin, CreateView):
    """Registra y aprueba acreditaciones con los permisos del modelo."""

    model = Acreditacion
    permission_required = "usuarios.add_acreditacion"
    form_class = AcreditacionForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:acreditacion_list")
    extra_context = {"title": "Crear acreditación"}


class AcreditacionUpdateView(AccesoUsuariosMixin, UpdateView):
    """Actualiza el estado y vigencia de una acreditación."""

    model = Acreditacion
    permission_required = "usuarios.change_acreditacion"
    form_class = AcreditacionForm
    template_name = "crud/form.html"
    success_url = reverse_lazy("usuarios:acreditacion_list")
    extra_context = {"title": "Editar acreditación"}


class AcreditacionDeleteView(AccesoUsuariosMixin, EliminacionProtegidaView):
    """Elimina acreditaciones que no estén protegidas por el historial."""

    model = Acreditacion
    permission_required = "usuarios.delete_acreditacion"
    template_name = "crud/confirm_delete.html"
    success_url = reverse_lazy("usuarios:acreditacion_list")
    extra_context = {"title": "acreditación"}

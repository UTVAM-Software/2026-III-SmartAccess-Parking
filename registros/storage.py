"""Almacenamiento de evidencia de placa fuera de la ruta pública de media."""

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.exceptions import SuspiciousOperation
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateCaptureStorage(FileSystemStorage):
    """Guarda fotografías en un directorio que no expone MEDIA_URL."""

    def __init__(self):
        super().__init__()

    @property
    def location(self):
        """Lee la ruta privada activa para admitir settings y temporales de test."""
        return str(settings.PRIVATE_MEDIA_ROOT)

    def url(self, name):
        """Impide crear URLs públicas; servir requiere vista autenticada."""
        raise SuspiciousOperation("Las fotografías privadas no tienen URL pública.")
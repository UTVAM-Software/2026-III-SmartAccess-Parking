"""Almacenamiento privado para documentos de acreditación."""

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateDocumentStorage(FileSystemStorage):
    """Guarda las acreditaciones fuera de MEDIA_URL y exige una vista protegida."""

    def __init__(self):
        super().__init__()

    @property
    def location(self):
        return str(settings.PRIVATE_MEDIA_ROOT)

    def url(self, name):
        raise SuspiciousOperation(
            "Los documentos de acreditación no tienen URL pública."
        )

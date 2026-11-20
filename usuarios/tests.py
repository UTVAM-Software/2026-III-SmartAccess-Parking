"""Pruebas de autenticación y permisos de usuarios y vehículos."""

from io import BytesIO
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from django.utils import timezone
from PIL import Image

from estacionamientos.models import Plaza
from .models import Acreditacion, Usuario, Vehiculo


class UsuariosPermisosTests(TestCase):
	"""Verifica acceso directo y permisos parciales del módulo usuarios."""

	@classmethod
	def setUpTestData(cls):
		cls.usuario = Usuario.objects.create(
			nombre="Operador de prueba",
			correo_electronico="operator@example.test",
			telefono="5550000000",
		)
		cls.vehiculo = Vehiculo.objects.create(
			placa="TST123",
			usuario=cls.usuario,
			modelo="Prueba",
		)

	def test_crud_urls_require_model_permissions(self):
		"""Bloquea vistas de usuario y vehículo ante acceso directo sin permiso."""
		user = get_user_model().objects.create_user(
			username="sin-permisos-usuarios",
			password="test-password",
		)
		self.client.force_login(user)
		urls = (
			reverse("usuarios:usuario_list"),
			reverse("usuarios:usuario_create"),
			reverse("usuarios:usuario_update", args=[self.usuario.pk]),
			reverse("usuarios:usuario_delete", args=[self.usuario.pk]),
			reverse("usuarios:vehiculo_list"),
			reverse("usuarios:vehiculo_create"),
			reverse("usuarios:vehiculo_update", args=[self.vehiculo.pk]),
			reverse("usuarios:vehiculo_delete", args=[self.vehiculo.pk]),
		)
		for url in urls:
			with self.subTest(url=url):
				self.assertEqual(self.client.get(url).status_code, 403)

	def test_read_only_user_sees_lists_without_mutation_actions(self):
		"""Permite leer listas, pero oculta enlaces CRUD y bloquea sus URLs."""
		user = get_user_model().objects.create_user(
			username="solo-lectura-usuarios",
			password="test-password",
		)
		user.user_permissions.add(
			*Permission.objects.filter(
				content_type__app_label="usuarios",
				codename__startswith="view_",
			)
		)
		self.client.force_login(user)
		actions = (
			(
				"usuarios:usuario_list",
				(
					reverse("usuarios:usuario_create"),
					reverse("usuarios:usuario_update", args=[self.usuario.pk]),
					reverse("usuarios:usuario_delete", args=[self.usuario.pk]),
				),
			),
			(
				"usuarios:vehiculo_list",
				(
					reverse("usuarios:vehiculo_create"),
					reverse("usuarios:vehiculo_update", args=[self.vehiculo.pk]),
					reverse("usuarios:vehiculo_delete", args=[self.vehiculo.pk]),
				),
			),
		)
		for list_name, urls in actions:
			response = self.client.get(reverse(list_name))
			self.assertEqual(response.status_code, 200)
			for url in urls:
				self.assertNotContains(response, url)
				self.assertEqual(self.client.get(url).status_code, 403)


class AcreditacionVigenciaTests(TestCase):
	"""Comprueba la categoría y fechas necesarias para autorizar accesos."""

	def test_requires_approval_validation_and_unexpired_date(self):
		usuario = Usuario.objects.create(
			nombre="Acreditada de prueba",
			correo_electronico="acreditacion@example.test",
			telefono="5550000001",
		)
		today = timezone.localdate()
		acreditacion = Acreditacion.objects.create(
			usuario=usuario,
			tipo=Acreditacion.Tipo.DISCAPACIDAD,
			documento="fixture-test",
			fecha_validacion=today,
			estado=False,
		)
		self.assertFalse(acreditacion.esta_vigente(today))

		acreditacion.estado = True
		acreditacion.fecha_validacion = None
		acreditacion.save(update_fields=("estado", "fecha_validacion"))
		self.assertFalse(acreditacion.esta_vigente(today))

		acreditacion.fecha_validacion = today
		acreditacion.fecha_vencimiento = None
		acreditacion.save(update_fields=("fecha_validacion", "fecha_vencimiento"))
		self.assertTrue(acreditacion.esta_vigente(today))

		acreditacion.fecha_vencimiento = today
		acreditacion.save(update_fields=("fecha_vencimiento",))
		self.assertTrue(acreditacion.esta_vigente(today))

		acreditacion.fecha_vencimiento = today - timedelta(days=1)
		acreditacion.save(update_fields=("fecha_vencimiento",))
		self.assertFalse(acreditacion.esta_vigente(today))

	def test_only_disability_category_is_accepted_by_database(self):
		"""La restricción de BD rechaza categorías fuera de la clasificación."""
		usuario = Usuario.objects.create(
			nombre="Categoría inválida",
			correo_electronico="categoria@example.test",
			telefono="5550000002",
		)
		with self.assertRaises(IntegrityError):
			with transaction.atomic():
				Acreditacion.objects.create(
					usuario=usuario,
					tipo="GENERAL",
					documento="fixture-test",
					fecha_validacion=timezone.localdate(),
					estado=True,
				)


class RegistroPublicoAcreditacionTests(TestCase):
	"""Una solicitud nueva queda visible para el revisor de su plaza."""

	@classmethod
	def setUpTestData(cls):
		cls.plaza = Plaza.objects.create(nombre="Plaza de revisión")
		cls.reviewer = get_user_model().objects.create_user(
			username="revisor",
			password="test-password",
		)
		cls.reviewer.user_permissions.add(
			*Permission.objects.filter(
				content_type__app_label="usuarios",
				codename__in=("view_acreditacion", "change_acreditacion"),
			)
		)
		cls.reviewer.user_permissions.add(
			*Permission.objects.filter(
				content_type__app_label="estacionamientos",
				codename="view_operational_dashboard",
			)
		)
		cls.plaza.administradores.add(cls.reviewer)

	def test_new_registration_appears_in_assigned_reviewer_list(self):
		image = BytesIO()
		Image.new("RGB", (2, 2), color="white").save(image, format="PNG")
		image.seek(0)
		registration = {
			"username": "persona-nueva",
			"email": "persona-nueva@example.test",
			"nombre": "Persona Nueva",
			"apellido_paterno": "Prueba",
			"apellido_materno": "",
			"telefono": "5551234567",
			"estado": "Hidalgo",
			"municipio": "Tizayuca",
			"plazas": [str(self.plaza.pk)],
			"placa": "NVA123",
			"marca": "",
			"modelo": "Auto de prueba",
			"color": "",
			"documento_imagen": SimpleUploadedFile(
				"documento.png",
				image.getvalue(),
				content_type="image/png",
			),
			"password1": "strong-test-password-872!",
			"password2": "strong-test-password-872!",
		}

		with TemporaryDirectory() as private_root, override_settings(
			PRIVATE_MEDIA_ROOT=private_root
		):
			response = self.client.post(
				reverse("usuarios:registro_publico"), registration
			)

		self.assertRedirects(response, reverse("usuarios:mi_cuenta"))
		new_profile = Usuario.objects.get(cuenta__username="persona-nueva")
		self.assertFalse(new_profile.acreditacion.estado)
		self.assertIn(self.plaza, new_profile.plazas.all())

		self.client.force_login(self.reviewer)
		response = self.client.get(reverse("usuarios:acreditacion_list"))

		self.assertContains(response, "Persona Nueva Prueba")
		response = self.client.get(reverse("estacionamientos:panel_operacion"))
		self.assertContains(response, "Persona Nueva Prueba")

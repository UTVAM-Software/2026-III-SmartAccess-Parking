from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from estacionamientos.models import Estacionamiento
from usuarios.models import Usuario, Vehiculo
from .models import CapturaPlaca, Incidencia, RegistroUso


class RegistrosCRUDTests(TestCase):
	@classmethod
	def setUpTestData(cls):
		cls.usuario = Usuario.objects.create(
			nombre="Ana Pérez",
			correo_electronico="ana@example.com",
			telefono="5551234567",
		)
		cls.vehiculo = Vehiculo.objects.create(
			placa="ABC123",
			usuario=cls.usuario,
			modelo="Sedán",
		)
		cls.estacionamiento = Estacionamiento.objects.create(numero_cajon="A-01")

	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="operador",
			password="test-password",
		)
		self.user.user_permissions.add(
			*Permission.objects.filter(content_type__app_label="registros")
		)
		self.client.force_login(self.user)

	def test_all_entities_support_create_update_and_delete(self):
		response = self.client.post(
			reverse("registros:registro_create"),
			{
				"vehiculo": self.vehiculo.pk,
				"estacionamiento": self.estacionamiento.pk,
				"fecha": "2026-10-23",
				"hora_entrada": "08:00",
				"hora_salida": "",
				"estado_acreditacion": "Autorizado",
			},
		)
		self.assertRedirects(response, reverse("registros:registro_list"))
		registro = RegistroUso.objects.get()
		self.assertIsNone(registro.hora_salida)

		response = self.client.post(
			reverse("registros:captura_create"),
			{
				"registro_uso": registro.pk,
				"placa_detectada": "ABC123",
				"fecha_hora": "2026-10-23T08:01",
				"imagen": "",
			},
		)
		self.assertRedirects(response, reverse("registros:captura_list"))
		captura = CapturaPlaca.objects.get()
		self.assertFalse(captura.imagen)

		image_buffer = BytesIO()
		Image.new("RGB", (1, 1)).save(image_buffer, format="PNG")
		with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
			response = self.client.post(
				reverse("registros:captura_create"),
				{
					"registro_uso": registro.pk,
					"placa_detectada": "ABC123",
					"fecha_hora": "2026-10-23T08:01",
					"imagen": SimpleUploadedFile(
						"captura.png",
						image_buffer.getvalue(),
						content_type="image/png",
					),
				},
			)
			self.assertRedirects(response, reverse("registros:captura_list"))
			captura_con_imagen = CapturaPlaca.objects.exclude(imagen="").get()
			self.assertTrue(captura_con_imagen.imagen)
			self.assertTrue(
				captura_con_imagen.imagen.storage.exists(captura_con_imagen.imagen.name)
			)

		response = self.client.post(
			reverse("registros:incidencia_create"),
			{
				"registro_uso": registro.pk,
				"tipo": "Acceso no autorizado",
				"descripcion": "Se detectó un intento de acceso.",
				"fecha_hora": "2026-10-23T08:02",
				"estado": "on",
			},
		)
		self.assertRedirects(response, reverse("registros:incidencia_list"))
		incidencia = Incidencia.objects.get()

		response = self.client.post(
			reverse("registros:registro_update", args=[registro.pk]),
			{
				"vehiculo": self.vehiculo.pk,
				"estacionamiento": self.estacionamiento.pk,
				"fecha": "2026-10-23",
				"hora_entrada": "08:00",
				"hora_salida": "09:00",
				"estado_acreditacion": "Finalizado",
			},
		)
		self.assertRedirects(response, reverse("registros:registro_list"))
		registro.refresh_from_db()
		self.assertEqual(registro.estado_acreditacion, "Finalizado")

		response = self.client.post(
			reverse("registros:captura_update", args=[captura.pk]),
			{
				"registro_uso": registro.pk,
				"placa_detectada": "XYZ789",
				"fecha_hora": "2026-10-23T08:03",
				"imagen": "",
			},
		)
		self.assertRedirects(response, reverse("registros:captura_list"))
		captura.refresh_from_db()
		self.assertEqual(captura.placa_detectada, "XYZ789")

		response = self.client.post(
			reverse("registros:incidencia_update", args=[incidencia.pk]),
			{
				"registro_uso": registro.pk,
				"tipo": "Revisión manual",
				"descripcion": "Se revisó la evidencia.",
				"fecha_hora": "2026-10-23T08:04",
				"estado": "on",
			},
		)
		self.assertRedirects(response, reverse("registros:incidencia_list"))
		incidencia.refresh_from_db()
		self.assertEqual(incidencia.tipo, "Revisión manual")

		response = self.client.post(
			reverse("registros:registro_delete", args=[registro.pk]),
			follow=True,
		)
		self.assertTrue(RegistroUso.objects.filter(pk=registro.pk).exists())
		self.assertContains(response, "No se puede eliminar")

		for entidad, delete_url, listado in (
			(captura, "registros:captura_delete", "registros:captura_list"),
			(captura_con_imagen, "registros:captura_delete", "registros:captura_list"),
			(incidencia, "registros:incidencia_delete", "registros:incidencia_list"),
			(registro, "registros:registro_delete", "registros:registro_list"),
		):
			response = self.client.post(
				reverse(delete_url, args=[entidad.pk]),
				follow=True,
			)
			self.assertRedirects(response, reverse(listado))
			self.assertFalse(type(entidad).objects.filter(pk=entidad.pk).exists())

	def test_views_require_login_and_model_permissions(self):
		self.client.logout()
		response = self.client.get(reverse("registros:registro_list"))
		self.assertEqual(response.status_code, 302)
		self.assertIn("/admin/login/", response.url)

		unauthorized = get_user_model().objects.create_user(
			username="sin-permisos",
			password="test-password",
		)
		self.client.force_login(unauthorized)
		response = self.client.get(reverse("registros:registro_list"))
		self.assertEqual(response.status_code, 403)

	def test_named_routes_exist_for_each_crud(self):
		for name in (
			"registro_list",
			"registro_create",
			"captura_list",
			"captura_create",
			"incidencia_list",
			"incidencia_create",
		):
			with self.subTest(name=name):
				self.assertTrue(reverse(f"registros:{name}"))

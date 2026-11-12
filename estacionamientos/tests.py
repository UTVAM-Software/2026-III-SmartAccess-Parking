"""Pruebas de permisos para estacionamientos y sensores."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from .models import Estacionamiento, Sensor


class EstacionamientosPermisosTests(TestCase):
	"""Verifica que los CRUD exijan permisos también en URLs directas."""

	@classmethod
	def setUpTestData(cls):
		cls.estacionamiento = Estacionamiento.objects.create(numero_cajon="T-01")
		cls.sensor = Sensor.objects.create(
			estacionamiento=cls.estacionamiento,
			tipo_sensor="Presencia",
		)

	def test_crud_urls_require_model_permissions(self):
		"""Bloquea listas y mutaciones si falta el permiso del modelo."""
		user = get_user_model().objects.create_user(
			username="sin-permisos-estacionamientos",
			password="test-password",
		)
		self.client.force_login(user)
		urls = (
			reverse("estacionamientos:estacionamiento_list"),
			reverse("estacionamientos:estacionamiento_create"),
			reverse("estacionamientos:estacionamiento_update", args=[self.estacionamiento.pk]),
			reverse("estacionamientos:estacionamiento_delete", args=[self.estacionamiento.pk]),
			reverse("estacionamientos:sensor_list"),
			reverse("estacionamientos:sensor_create"),
			reverse("estacionamientos:sensor_update", args=[self.sensor.pk]),
			reverse("estacionamientos:sensor_delete", args=[self.sensor.pk]),
		)
		for url in urls:
			with self.subTest(url=url):
				self.assertEqual(self.client.get(url).status_code, 403)

	def test_read_only_user_cannot_create_or_mutate_spaces(self):
		"""Muestra las listas autorizadas, ocultando las acciones de escritura."""
		user = get_user_model().objects.create_user(
			username="solo-lectura-estacionamientos",
			password="test-password",
		)
		user.user_permissions.add(
			*Permission.objects.filter(
				content_type__app_label="estacionamientos",
				codename__startswith="view_",
			)
		)
		self.client.force_login(user)
		actions = (
			(
				"estacionamientos:estacionamiento_list",
				(
					reverse("estacionamientos:estacionamiento_create"),
					reverse("estacionamientos:estacionamiento_update", args=[self.estacionamiento.pk]),
					reverse("estacionamientos:estacionamiento_delete", args=[self.estacionamiento.pk]),
				),
			),
			(
				"estacionamientos:sensor_list",
				(
					reverse("estacionamientos:sensor_create"),
					reverse("estacionamientos:sensor_update", args=[self.sensor.pk]),
					reverse("estacionamientos:sensor_delete", args=[self.sensor.pk]),
				),
			),
		)
		for list_name, urls in actions:
			response = self.client.get(reverse(list_name))
			self.assertEqual(response.status_code, 200)
			for url in urls:
				self.assertNotContains(response, url)
				self.assertEqual(self.client.get(url).status_code, 403)

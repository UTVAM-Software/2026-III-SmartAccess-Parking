"""Pruebas de permisos para estacionamientos y sensores."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .admin import PlazaAdmin
from .models import Estacionamiento, Plaza, Sensor


class PlazaRoleAssignmentTests(TestCase):
	"""A newly created operator can be assigned from the plaza editor."""

	@classmethod
	def setUpTestData(cls):
		cls.plaza = Plaza.objects.create(nombre="Plaza de asignación")
		cls.root = get_user_model().objects.create_superuser(
			username="root-plaza",
			password="test-password",
			email="root-plaza@example.test",
		)

	def test_new_normal_account_is_available_for_role_assignment(self):
		account = get_user_model().objects.create_user(
			username="nuevo-operador",
			password="test-password",
		)
		request = RequestFactory().get("/admin/")
		request.user = self.root
		plaza_admin = PlazaAdmin(Plaza, admin.site)

		field = plaza_admin.formfield_for_manytomany(
			Plaza._meta.get_field("administradores"), request
		)

		self.assertIn(account, field.queryset)

	def test_assigning_account_grants_the_matching_reviewer_role(self):
		account = get_user_model().objects.create_user(
			username="nuevo-revisor",
			password="test-password",
		)
		request = RequestFactory().post("/admin/")
		request.user = self.root
		plaza_admin = PlazaAdmin(Plaza, admin.site)
		form = type("AssignmentForm", (), {})()
		form.save_m2m = lambda: self.plaza.administradores.add(account)

		plaza_admin.save_related(request, form, [], change=True)

		self.assertTrue(
			account.groups.filter(name="Administrador de estacionamiento").exists()
		)
		self.assertTrue(
			account.has_perm("usuarios.view_acreditacion")
		)

		form.save_m2m = lambda: self.plaza.administradores.clear()
		plaza_admin.save_related(request, form, [], change=True)

		self.assertFalse(
			account.groups.filter(name="Administrador de estacionamiento").exists()
		)

	def test_access_assignment_grants_and_revokes_plate_validation(self):
		account = get_user_model().objects.create_user(
			username="nuevo-personal-acceso",
			password="test-password",
		)
		request = RequestFactory().post("/admin/")
		request.user = self.root
		plaza_admin = PlazaAdmin(Plaza, admin.site)
		form = type("AssignmentForm", (), {})()
		form.save_m2m = lambda: self.plaza.personal_acceso.add(account)

		plaza_admin.save_related(request, form, [], change=True)

		assigned_account = get_user_model().objects.get(pk=account.pk)
		self.assertTrue(assigned_account.has_perm("registros.validate_plate_access"))

		form.save_m2m = lambda: self.plaza.personal_acceso.clear()
		plaza_admin.save_related(request, form, [], change=True)

		unassigned_account = get_user_model().objects.get(pk=account.pk)
		self.assertFalse(unassigned_account.has_perm("registros.validate_plate_access"))


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

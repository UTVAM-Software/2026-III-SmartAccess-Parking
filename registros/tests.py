"""Pruebas del módulo Registros e Incidencias."""

from io import BytesIO
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import SuspiciousOperation
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from django.urls import reverse
from PIL import Image

from estacionamientos.models import Estacionamiento, Plaza, Sensor
from usuarios.models import Usuario, Vehiculo
from .models import Boleto, CapturaPlaca, Incidencia, IntentoAcceso, RegistroUso
from .services import process_manual_access
from usuarios.models import Acreditacion


class RegistrosCRUDTests(TestCase):
    """Pruebas de CRUD, permisos y relaciones del módulo de registros."""

    @classmethod
    def setUpTestData(cls):
        """Crear datos compartidos para los casos del módulo."""
        cls.plaza = Plaza.objects.create(nombre="Plaza de prueba")
        cls.usuario = Usuario.objects.create(
            nombre="Ana Pérez",
            correo_electronico="ana@example.com",
            telefono="5551234567",
        )
        cls.usuario.plazas.add(cls.plaza)
        cls.vehiculo = Vehiculo.objects.create(
            placa="ABC123",
            usuario=cls.usuario,
            modelo="Sedán",
        )
        cls.estacionamiento = Estacionamiento.objects.create(
            numero_cajon="A-01",
            plaza=cls.plaza,
            accesible=True,
        )

    def setUp(self):
        """Autenticar un usuario con permisos del módulo."""
        self.user = get_user_model().objects.create_user(
            username="operador",
            password="test-password",
        )
        self.user.user_permissions.add(
            *Permission.objects.filter(content_type__app_label="registros")
        )
        # El permiso histórico es personalizado y debe asignarse explícitamente:
        # no es equivalente al permiso estándar change_registrouso.
        registro_content_type = ContentType.objects.get_for_model(RegistroUso)
        permisos_historicos = []
        for codigo, nombre in (
            ("change_registrouso_history", "Can edit historical usage records"),
            ("delete_registrouso_history", "Can delete historical usage records"),
        ):
            permiso, _ = Permission.objects.get_or_create(
                content_type=registro_content_type,
                codename=codigo,
                defaults={"name": nombre},
            )
            permisos_historicos.append(permiso)
        self.user.user_permissions.add(*permisos_historicos)
        self.plaza.personal_acceso.add(self.user)
        self.client.force_login(self.user)

    def test_all_entities_support_create_update_and_delete(self):
        """Validar acceso autorizado, CRUD de evidencia/incidencias y protección."""
        Acreditacion.objects.create(
            usuario=self.usuario,
            tipo=Acreditacion.Tipo.DISCAPACIDAD,
            documento="fixture-test",
            fecha_validacion=timezone.localdate(),
            estado=True,
        )
        response = self.client.post(
            reverse("registros:intento_create"),
            {
                "placa_capturada": self.vehiculo.placa,
                "plaza": self.plaza.pk,
            },
        )
        self.assertRedirects(response, reverse("registros:intento_create"))
        intento = IntentoAcceso.objects.get()
        self.assertEqual(intento.resultado, IntentoAcceso.Resultado.AUTORIZADO)
        self.assertEqual(RegistroUso.objects.count(), 0)
        self.assertEqual(Boleto.objects.count(), 0)

        registro = RegistroUso.objects.create(
            vehiculo=self.vehiculo,
            estacionamiento=self.estacionamiento,
            fecha="2026-10-23",
            hora_entrada="08:00",
            estado_acreditacion="Fixture autorizado",
        )

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
        with TemporaryDirectory() as media_root, override_settings(
            MEDIA_ROOT=media_root,
            PRIVATE_MEDIA_ROOT=media_root,
        ):
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
                captura_con_imagen.imagen.storage.exists(
                    captura_con_imagen.imagen.name)
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
        ):
            response = self.client.post(
                reverse(delete_url, args=[entidad.pk]),
                follow=True,
            )
            self.assertRedirects(response, reverse(listado))
            self.assertFalse(type(entidad).objects.filter(
                pk=entidad.pk).exists())

        response = self.client.post(
            reverse("registros:registro_delete", args=[registro.pk]),
            follow=True,
        )
        self.assertTrue(RegistroUso.objects.filter(pk=registro.pk).exists())
        self.assertContains(response, "No se puede eliminar")

    def test_views_require_login_and_model_permissions(self):
        """Comprobar autenticación y permisos de las vistas."""
        self.client.logout()
        response = self.client.get(reverse("registros:registro_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

        unauthorized = get_user_model().objects.create_user(
            username="sin-permisos",
            password="test-password",
        )
        unauthorized.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="registros",
                codename__startswith="view_",
            )
        )
        self.client.force_login(unauthorized)
        registro = RegistroUso.objects.create(
            vehiculo=self.vehiculo,
            estacionamiento=self.estacionamiento,
            fecha="2026-10-23",
            hora_entrada="08:00",
            estado_acreditacion="Autorizado",
        )
        captura = CapturaPlaca.objects.create(
            registro_uso=registro,
            placa_detectada="ABC123",
            fecha_hora="2026-10-23T08:01:00Z",
        )
        incidencia = Incidencia.objects.create(
            registro_uso=registro,
            tipo="Acceso no autorizado",
            descripcion="Se detectó un intento de acceso.",
            fecha_hora="2026-10-23T08:02:00Z",
        )

        protected_urls = (
            reverse("registros:registro_create"),
            reverse("registros:registro_update", args=[registro.pk]),
            reverse("registros:registro_delete", args=[registro.pk]),
            reverse("registros:captura_create"),
            reverse("registros:captura_update", args=[captura.pk]),
            reverse("registros:captura_delete", args=[captura.pk]),
            reverse("registros:incidencia_create"),
            reverse("registros:incidencia_update", args=[incidencia.pk]),
            reverse("registros:incidencia_delete", args=[incidencia.pk]),
        )
        for url in protected_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

        for list_url, action_urls in (
            (
                "registros:registro_list",
                (
                    reverse("registros:registro_create"),
                    reverse("registros:registro_update", args=[registro.pk]),
                    reverse("registros:registro_delete", args=[registro.pk]),
                ),
            ),
            (
                "registros:captura_list",
                (
                    reverse("registros:captura_create"),
                    reverse("registros:captura_update", args=[captura.pk]),
                    reverse("registros:captura_delete", args=[captura.pk]),
                ),
            ),
            (
                "registros:incidencia_list",
                (
                    reverse("registros:incidencia_create"),
                    reverse("registros:incidencia_update", args=[incidencia.pk]),
                    reverse("registros:incidencia_delete", args=[incidencia.pk]),
                ),
            ),
        ):
            response = self.client.get(reverse(list_url))
            self.assertEqual(response.status_code, 200)
            for action_url in action_urls:
                self.assertNotContains(response, action_url)

    def test_operator_login_and_logout_do_not_require_admin_staff(self):
        """Permite entrar y salir a operadores no administradores de Django."""
        self.client.logout()
        self.assertFalse(self.user.is_staff)

        response = self.client.post(
            reverse("login"),
            {"username": "operador", "password": "test-password"},
        )
        self.assertRedirects(response, reverse("registros:intento_create"))

        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_named_routes_exist_for_each_crud(self):
        """Verificar que las rutas principales se resuelvan por nombre."""
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

    def test_unknown_plate_is_rejected_without_use_or_ticket(self):
        """Registra el rechazo de una placa desconocida sin crear ocupación."""
        attempt = process_manual_access(
            operator=self.user,
            plaza=self.plaza,
            placa_capturada="DESCONOCIDA-01",
        )

        self.assertEqual(attempt.resultado, IntentoAcceso.Resultado.RECHAZADO)
        self.assertIn("No hay un vehículo", attempt.motivo_rechazo)
        self.assertIsNone(attempt.vehiculo)
        self.assertIsNone(attempt.estacionamiento)
        self.assertEqual(RegistroUso.objects.count(), 0)
        self.assertEqual(Boleto.objects.count(), 0)

    def test_manual_attempt_view_persists_rejection_without_ticket(self):
        """La vista manual registra el resultado sin aceptar uno del cliente."""
        response = self.client.post(
            reverse("registros:intento_create"),
            {
                "placa_capturada": "NO-REGISTRADA",
                "plaza": self.plaza.pk,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NO AUTORIZADO")
        self.assertContains(response, "La placa no est\u00e1 registrada en el sistema.")
        attempt = IntentoAcceso.objects.get()
        self.assertEqual(attempt.resultado, IntentoAcceso.Resultado.RECHAZADO)
        self.assertEqual(RegistroUso.objects.count(), 0)
        self.assertEqual(Boleto.objects.count(), 0)

    def test_attempt_image_requires_view_permission(self):
        """El endpoint privado exige permiso incluso para URL directa."""
        attempt = IntentoAcceso.objects.create(
            operador=self.user,
            placa_capturada="NO-REGISTRADA",
            resultado=IntentoAcceso.Resultado.RECHAZADO,
            motivo_rechazo="Placa desconocida.",
        )
        user = get_user_model().objects.create_user(
            username="sin-permiso-imagen",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(
            reverse("registros:intento_imagen", args=[attempt.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_expired_accreditation_is_rejected(self):
        """Una acreditación vencida no autoriza ni ocupa un cajón."""
        today = timezone.localdate()
        Acreditacion.objects.create(
            usuario=self.usuario,
            tipo=Acreditacion.Tipo.DISCAPACIDAD,
            documento="fixture-test",
            fecha_validacion=today - timedelta(days=30),
            fecha_vencimiento=today - timedelta(days=1),
            estado=True,
        )

        attempt = process_manual_access(
            operator=self.user,
            plaza=self.plaza,
            placa_capturada=self.vehiculo.placa,
        )

        self.assertEqual(attempt.resultado, IntentoAcceso.Resultado.RECHAZADO)
        self.assertIn("aprobada y vigente", attempt.motivo_rechazo)
        self.assertEqual(RegistroUso.objects.count(), 0)
        self.assertEqual(Boleto.objects.count(), 0)

    def test_occupied_sensor_never_authorizes_or_assigns_a_space(self):
        """Un sensor puede bloquear un cajón, pero nunca autoriza el vehículo."""
        today = timezone.localdate()
        Acreditacion.objects.create(
            usuario=self.usuario,
            tipo=Acreditacion.Tipo.DISCAPACIDAD,
            documento="fixture-test",
            fecha_validacion=today,
            estado=True,
        )
        Sensor.objects.create(
            estacionamiento=self.estacionamiento,
            tipo_sensor="Presencia",
            estado=True,
            estado_ocupacion=True,
        )

        attempt = process_manual_access(
            operator=self.user,
            plaza=self.plaza,
            placa_capturada=self.vehiculo.placa,
        )

        self.assertEqual(attempt.resultado, IntentoAcceso.Resultado.RECHAZADO)
        self.assertIn("sensor reporta ocupación", attempt.motivo_rechazo)
        self.assertEqual(RegistroUso.objects.count(), 0)
        self.assertEqual(Boleto.objects.count(), 0)

    def test_authorized_access_creates_zero_cost_ticket_and_exit_releases_space(self):
        """Autoriza con acreditación vigente, evita duplicado y libera al salir."""
        today = timezone.localdate()
        Acreditacion.objects.create(
            usuario=self.usuario,
            tipo=Acreditacion.Tipo.DISCAPACIDAD,
            documento="fixture-test",
            fecha_validacion=today,
            fecha_vencimiento=None,
            estado=True,
        )
        self.estacionamiento.exclusivo_discapacidad = True
        self.estacionamiento.save(update_fields=("exclusivo_discapacidad",))

        attempt = process_manual_access(
            operator=self.user,
            plaza=self.plaza,
            placa_capturada=self.vehiculo.placa.lower(),
        )

        self.assertEqual(attempt.resultado, IntentoAcceso.Resultado.AUTORIZADO)
        self.assertIsNotNone(attempt.registro_uso)
        self.assertEqual(attempt.boleto.monto, 0)
        self.assertEqual(attempt.boleto.cargo_adicional, 0)
        self.assertFalse(attempt.boleto.pagado)
        self.estacionamiento.refresh_from_db()
        self.assertFalse(self.estacionamiento.estado)

        Estacionamiento.objects.create(numero_cajon="A-02")
        duplicate = process_manual_access(
            operator=self.user,
            plaza=self.plaza,
            placa_capturada=self.vehiculo.placa,
        )
        self.assertEqual(duplicate.resultado, IntentoAcceso.Resultado.RECHAZADO)
        self.assertEqual(RegistroUso.objects.count(), 1)
        self.assertEqual(Boleto.objects.count(), 1)

        exit_url = reverse(
            "registros:registro_salida",
            args=[attempt.registro_uso_id],
        )
        self.assertEqual(self.client.get(exit_url).status_code, 405)
        response = self.client.post(exit_url)
        self.assertRedirects(response, reverse("registros:registro_list"))
        use = RegistroUso.objects.get(pk=attempt.registro_uso_id)
        self.assertIsNotNone(use.hora_salida)
        attempt.boleto.refresh_from_db()
        self.assertIsNotNone(attempt.boleto.fecha_salida)
        self.estacionamiento.refresh_from_db()
        self.assertTrue(self.estacionamiento.estado)

    def test_database_constraint_prevents_two_active_uses_of_one_space(self):
        """La restricción SQL impide ocupaciones simultáneas del mismo cajón."""
        RegistroUso.objects.create(
            vehiculo=self.vehiculo,
            estacionamiento=self.estacionamiento,
            fecha="2026-10-23",
            hora_entrada="08:00",
            estado_acreditacion="Fixture",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RegistroUso.objects.create(
                    vehiculo=self.vehiculo,
                    estacionamiento=self.estacionamiento,
                    fecha="2026-10-23",
                    hora_entrada="08:01",
                    estado_acreditacion="Fixture",
                )

    def test_attempt_image_is_private_and_requires_authorized_view(self):
        """La fotografía se entrega con permiso y no existe URL pública."""
        image_buffer = BytesIO()
        Image.new("RGB", (1, 1)).save(image_buffer, format="PNG")
        image_bytes = image_buffer.getvalue()
        with TemporaryDirectory() as private_root, override_settings(
            PRIVATE_MEDIA_ROOT=private_root
        ):
            attempt = process_manual_access(
                operator=self.user,
                plaza=self.plaza,
                placa_capturada="DESCONOCIDA-IMAGEN",
                imagen=SimpleUploadedFile(
                    "placa.png",
                    image_bytes,
                    content_type="image/png",
                ),
            )
            self.assertTrue(attempt.imagen.storage.exists(attempt.imagen.name))
            with self.assertRaises(SuspiciousOperation):
                str(attempt.imagen.url)

            response = self.client.get(
                reverse("registros:intento_imagen", args=[attempt.pk])
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertEqual(b"".join(response.streaming_content), image_bytes)
            self.assertEqual(
                self.client.get(f"/media/{attempt.imagen.name}").status_code,
                404,
            )

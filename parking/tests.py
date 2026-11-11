"""Pruebas de preservación de tablas legacy parking."""

from django.apps import apps
from django.db import connection
from django.test import TestCase

from estacionamientos.models import Estacionamiento
from registros.models import Boleto, CapturaPlaca, Pago, RegistroUso
from usuarios.models import Acreditacion, Usuario, Vehiculo
from . import models as legacy_models


class ParkingLegacyStateTests(TestCase):
	"""Comprueba que parking no duplica modelos y conserva sus tablas físicas."""

	def test_legacy_models_are_aliases_and_tables_remain_archived(self):
		canonical_aliases = (
			(legacy_models.Usuario, Usuario),
			(legacy_models.Acreditacion, Acreditacion),
			(legacy_models.Vehiculo, Vehiculo),
			(legacy_models.Estacionamiento, Estacionamiento),
			(legacy_models.Boleto, Boleto),
			(legacy_models.RegistroUso, RegistroUso),
			(legacy_models.CapturaPlaca, CapturaPlaca),
			(legacy_models.Pago, Pago),
		)
		for legacy, canonical in canonical_aliases:
			with self.subTest(model=canonical.__name__):
				self.assertIs(legacy, canonical)
				self.assertNotEqual(legacy._meta.app_label, "parking")

		self.assertEqual(list(apps.get_app_config("parking").get_models()), [])
		tables = set(connection.introspection.table_names())
		archived_tables = {
			"parking_usuario",
			"parking_acreditacion",
			"parking_vehiculo",
			"parking_estacionamiento",
			"parking_boleto",
			"parking_registrouso",
			"parking_capturaplaca",
			"parking_pago",
		}
		self.assertTrue(archived_tables.issubset(tables))

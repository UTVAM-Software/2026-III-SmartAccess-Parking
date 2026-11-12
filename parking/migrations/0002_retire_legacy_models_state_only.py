"""Retira modelos legacy del estado Django sin tocar sus tablas físicas."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("parking", "0001_initial"),
        ("usuarios", "0004_acreditacion_acreditacion_solo_discapacidad"),
        ("estacionamientos", "0003_transfer_legacy_stalls"),
        ("registros", "0004_transfer_legacy_records"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name="CapturaPlaca"),
                migrations.DeleteModel(name="RegistroUso"),
                migrations.DeleteModel(name="Pago"),
                migrations.DeleteModel(name="Boleto"),
                migrations.DeleteModel(name="Acreditacion"),
                migrations.DeleteModel(name="Vehiculo"),
                migrations.DeleteModel(name="Estacionamiento"),
                migrations.DeleteModel(name="Usuario"),
            ],
        ),
    ]
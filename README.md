# SmartAccess Parking

Sistema web Django para administrar usuarios, vehículos, acreditaciones, cajones, sensores y registros de acceso.

## Instalación local en Windows

Requiere una versión de Python compatible con Django 6.1.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`. Django usa SQLite de forma predeterminada. Las migraciones crean también los permisos estándar de cada modelo.

Para habilitar la lectura OCR de placas en Windows, instala por separado el motor Tesseract siguiendo la [guía de instalación](https://tesseract-ocr.github.io/tessdoc/Installation.html). `pytesseract` es el conector de Python; no instala el motor. Si Tesseract no está en `PATH`, configura su ruta antes de iniciar Django:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

## Cuentas y permisos

La cuenta que inicia sesión es una cuenta de autenticación de Django. El perfil de negocio `usuarios.Usuario` es un registro distinto y se relaciona con los vehículos y acreditaciones.

Cualquier persona puede crear una cuenta desde `/usuarios/registro/`. El formulario registra el perfil, un vehículo, el estado, el municipio y una o varias plazas disponibles en esa ubicación. Para este piloto las opciones son Hidalgo, Tizayuca y Tizara. La persona también adjunta una fotografía del documento de acreditación; queda pendiente hasta que un administrador la revise y registre la aprobación y su fecha. Desde **Mi cuenta** puede agregar placas propias hasta un máximo de tres vehículos por perfil.

Las imágenes de acreditación se guardan en almacenamiento privado, fuera de `MEDIA_URL`. Solo la persona titular y el personal con permiso de revisión asignado a una de sus plazas pueden abrirlas.

### Operadores de estacionamiento

El sistema prepara los grupos **Administrador de estacionamiento** y **Viene viene** al aplicar las migraciones. Una cuenta raíz crea cuentas normales en `/admin/`, las agrega al grupo que corresponde y las asigna a una o varias plazas desde **Plazas**. Mantén `is_staff` y `is_superuser` desactivados en ambas cuentas: el administrador entra por `/acceso/` al **Panel de operación**, y el personal de acceso entra directamente a **Validar placa**. Sus permisos y plazas quedan limitados a las funciones y ubicaciones asignadas. La cuenta raíz conserva la administración global de Django.

El panel del administrador muestra acreditaciones pendientes, fotos privadas para revisar, cajones, revisiones de placa e incidencias de sus plazas. El administrador aprueba una acreditación tras revisar el documento y establece su fecha de validación y, si aplica, la fecha de vencimiento. El personal **Viene viene** solo puede subir una foto o escribir la placa en una plaza asignada; recibe una respuesta clara sobre si la persona, el vehículo y la acreditación están vigentes para esa plaza. Esta consulta no crea boletos ni ocupa cajones.

Asigna permisos a personas o grupos desde `/admin/`. Las vistas verifican los permisos del lado del servidor, también al abrir una URL directamente; el menú oculta los módulos que la cuenta no puede consultar.

| Área | Permisos de operación | Permiso de consulta |
| --- | --- | --- |
| Validar placas (Viene viene) | `registros.validate_plate_access` | — |
| Personas y acreditaciones (administrador) | `change_usuario`, `change_acreditacion` | `view_usuario`, `view_acreditacion` |
| Registros de uso | `change_registrouso` permite registrar salidas | `view_registrouso` |
| Mantenimiento histórico | `change_registrouso_history`, `delete_registrouso_history` | — |
| Capturas, incidencias e intentos | Permisos `add_*`, `change_*`, `delete_*` de cada modelo | Permisos `view_*` de cada modelo |

Los grupos de aplicación se sincronizan con permisos de mínimo privilegio al ejecutar las migraciones. El grupo **Administrador de estacionamiento** no incluye acceso a vehículos, sensores ni CRUD de cajones. **Viene viene** solo tiene permiso para validar placas, y requiere asignación explícita a una plaza.

## Flujo de acceso actual

- El personal de acceso puede escribir la placa o adjuntar una fotografía. OCR solo propone la lectura: el personal debe revisar y confirmar la placa. Las lecturas con confianza baja requieren captura manual.
- La respuesta requiere vehículo y perfil activos, solicitud de la persona para la plaza seleccionada y acreditación de discapacidad aprobada y vigente.
- Cada consulta queda en el historial para que el administrador pueda supervisar la actividad. Validar una placa no abre una entrada, no crea boleto y no ocupa un cajón.
- Las fotografías de documentos y de evidencia se guardan en almacenamiento privado y se sirven mediante vistas con autorización limitada a la persona titular o a operadores de la plaza correspondiente.
- Todavía no hay integración automática con cámara o sensores físicos; el personal de acceso carga la fotografía manualmente o escribe la placa.
- Los datos de pago existentes son históricos; no se procesan cobros.

## Configuración fuera de desarrollo

Al desplegar, define `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` y `DJANGO_EMAIL_BACKEND`. Configura también `DJANGO_CSRF_TRUSTED_ORIGINS` si el sitio recibe solicitudes desde un dominio HTTPS. En modo de producción, el proyecto activa redirección HTTPS y cookies seguras de forma predeterminada.

# SmartAccess Parking

Sistema web Django para administrar usuarios, vehículos, acreditaciones, cajones, sensores y registros de acceso.

## Requisitos

- Python **3.12, 3.13 o 3.14**; el proyecto se verificó con Python 3.12.6.
- Django **6.1.1**, versión instalada en el entorno del proyecto y fijada en `requirements.txt`.
- Pillow **12.3.0** estaba instalado en el entorno revisado; `requirements.txt` conserva el requisito `Pillow>=9.2`. Se utiliza para validar y procesar imágenes de los campos de imagen y para preparar imágenes del OCR.
- Tesseract OCR es opcional y se instala por separado si se habilita la lectura OCR de placas. `pytesseract` es el conector de Python, no instala el motor.
- PostgreSQL 15 o superior es opcional para despliegue; sus variables y el controlador se describen abajo.

## Instalación local en Windows

Desde la raíz del repositorio, crea y activa un entorno virtual:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instala las dependencias declaradas. Esto instala también Pillow y el conector `pytesseract`:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Pillow ya está declarado en `requirements.txt`; si se necesita instalarlo por separado:

```powershell
python -m pip install "Pillow>=9.2"
```

## Diagnósticos de desarrollo

La configuración de Pylint del repositorio activa el plugin `pylint_django` y usa `SmartAccessParking.settings`. Instala las herramientas de desarrollo con:

```powershell
python -m pip install -r requirements-dev.txt
python -m pylint manage.py SmartAccessParking common estacionamientos parking registros usuarios
```

En Linux o macOS, crea y activa el entorno con `python3.12 -m venv .venv` y `source .venv/bin/activate`; los demás comandos `python -m pip` y `python manage.py` son iguales.

La configuración local de VS Code también especificaba el plugin `pylint_django` y el módulo Django `SmartAccessParking.settings`. Es una opción de editor, no una dependencia del sistema, y no está incluida en `requirements.txt`.

## Variables de entorno

Django lee la configuración directamente del entorno del proceso. En desarrollo, SQLite es la base predeterminada y `DEBUG` es `true`; se puede omitir `DJANGO_SECRET_KEY` localmente y Django generará una clave temporal al iniciar. `.env.example` es una plantilla sin secretos reales; Django no carga archivos `.env` automáticamente, así que define sus valores en el entorno del proceso o en la plataforma de despliegue. Para definir explícitamente las variables en PowerShell, antes de ejecutar comandos Django:

```powershell
$env:DJANGO_DEBUG = "true"
$env:DJANGO_SECRET_KEY = (python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1,testserver"
```

Cada integrante debe generar y mantener su propia `DJANGO_SECRET_KEY`; no se debe compartir ni subir al repositorio. En producción, configura una clave privada, `DJANGO_DEBUG=false` y `DJANGO_ALLOWED_HOSTS` con los nombres de host reales. Configura también `DJANGO_EMAIL_BACKEND`; el valor usado localmente por defecto es la consola de Django. Si se despliega detrás de un proxy HTTPS, revisa `DJANGO_CSRF_TRUSTED_ORIGINS` y `DJANGO_BEHIND_HTTPS_PROXY`.

## Base de datos

La conexión se configura sin editar `SmartAccessParking/settings.py` mediante estas variables:

| Variable | Uso |
| --- | --- |
| `DJANGO_DB_ENGINE` | Motor Django; predeterminado `django.db.backends.sqlite3`. También acepta `sqlite`, `sqlite3`, `postgres` o `postgresql`. |
| `DJANGO_DB_NAME` | Ruta del archivo SQLite o nombre de la base PostgreSQL. Si se omite con SQLite, se usa `db.sqlite3` en la raíz. |
| `DJANGO_DB_USER` | Usuario PostgreSQL. |
| `DJANGO_DB_PASSWORD` | Contraseña PostgreSQL. |
| `DJANGO_DB_HOST` | Host PostgreSQL. |
| `DJANGO_DB_PORT` | Puerto PostgreSQL. |

El desarrollo local conserva SQLite sin configuración adicional. Para un servidor PostgreSQL, instala PostgreSQL y define en el entorno del servicio Django los valores proporcionados por quien administra ese servidor. Ejemplo en PowerShell (sustituye los marcadores por los datos reales; no guardes la contraseña en el repositorio):

```powershell
$env:DJANGO_DB_ENGINE = "django.db.backends.postgresql"
$env:DJANGO_DB_NAME = "smartaccess"
$env:DJANGO_DB_USER = "usuario_del_servidor"
$env:DJANGO_DB_PASSWORD = "contraseña_del_servidor"
$env:DJANGO_DB_HOST = "servidor.ejemplo"
$env:DJANGO_DB_PORT = "5432"
```

`psycopg[binary]` está declarado en `requirements.txt` para que Django pueda conectarse a PostgreSQL. No se requiere al usar SQLite.

## Migraciones y ejecución

Una vez configuradas las variables de entorno, desde la raíz del proyecto:

```powershell
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`createsuperuser` es necesario para crear una cuenta administradora inicial y se ejecuta solo cuando corresponda. Abre `http://127.0.0.1:8000/` para acceder al sistema.

Para habilitar OCR de placas en Windows, instala por separado el [motor Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html). Si no está en `PATH`, define la ruta antes de iniciar Django:

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

Las migraciones preparan también los permisos estándar de cada modelo y los grupos de operación del sistema.

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

En producción, Django activa redirección HTTPS y cookies seguras por defecto cuando `DJANGO_DEBUG=false`; revisa esos valores con la configuración del proxy y del servidor antes del despliegue.

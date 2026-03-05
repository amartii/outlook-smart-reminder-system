# Outlook Smart Reminder System — Guía de instalación y despliegue

---

## Requisitos previos

Antes de empezar, asegúrate de tener:

- **Python 3.10 o superior** — [descargar](https://www.python.org/downloads/)
- **Git** — [descargar](https://git-scm.com/)
- **Cuenta de Office 365 / Microsoft 365** con buzón activo
- **Acceso de administrador a Azure Active Directory** de tu organización (para registrar la app)

---

## Paso 1 — Registrar la aplicación en Azure AD

> Este paso lo debe hacer un administrador de Azure Active Directory de la organización.

### 1.1 Ir al portal de Azure

1. Abrir [https://portal.azure.com](https://portal.azure.com)
2. Iniciar sesión con la cuenta corporativa que tenga rol de administrador

### 1.2 Registrar nueva aplicación

1. Buscar **"Azure Active Directory"** en el buscador superior
2. En el menú lateral: **App registrations** → **New registration**
3. Rellenar:
   - **Name:** `Outlook Smart Reminder`
   - **Supported account types:** *Accounts in this organizational directory only*
   - **Redirect URI:** dejar vacío
4. Click **Register**

### 1.3 Copiar credenciales

En la página de la aplicación recién creada, copiar y guardar:

- **Application (client) ID** → será `OUTLOOK_CLIENT_ID`
- **Directory (tenant) ID** → será `OUTLOOK_TENANT_ID`

### 1.4 Crear Client Secret

1. En el menú lateral: **Certificates & secrets** → **New client secret**
2. Rellenar:
   - **Description:** `Outlook Smart Reminder Secret`
   - **Expires:** 24 months
3. Click **Add**
4. **Copiar inmediatamente el campo "Value"** → será `OUTLOOK_CLIENT_SECRET`

> ⚠️ El valor del secret solo se muestra una vez. Si lo pierdes, tendrás que crear uno nuevo.

### 1.5 Configurar permisos de API

1. En el menú lateral: **API permissions** → **Add a permission**
2. Seleccionar **Microsoft Graph** → **Application permissions**
3. Buscar y añadir los siguientes permisos:
   - `Mail.Send`
   - `Mail.Read`
   - `Contacts.Read`
   - `User.Read.All`
4. Click **Add permissions**
5. Click **"Grant admin consent for [nombre de la organización]"** → Confirmar
6. Verificar que todos los permisos muestran el check verde ✓

---

## Paso 2 — Clonar el repositorio

```bash
git clone https://github.com/amartii/outlook-smart-reminder-system.git
cd outlook-smart-reminder-system
```

---

## Paso 3 — Crear el entorno virtual

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

Verifica que el entorno esté activo — el prompt debería mostrar `(venv)`.

---

## Paso 4 — Instalar dependencias

```bash
pip install -r requirements.txt
```

Dependencias principales que se instalarán:

| Paquete | Versión mínima | Para qué sirve |
|---------|---------------|----------------|
| Flask | 3.0 | Framework web |
| Flask-SQLAlchemy | 3.0 | ORM base de datos |
| Flask-Migrate | 4.0 | Migraciones DB |
| APScheduler | 3.10 | Jobs automáticos |
| msal | 1.20 | Autenticación Microsoft OAuth2 |
| requests | 2.31 | Llamadas a Microsoft Graph API |
| python-dateutil | 2.8 | Cálculo de fechas |
| cryptography | 41.0 | Cifrado Fernet de credenciales |

---

## Paso 5 — Configurar variables de entorno

### 5.1 Crear el archivo `.env`

```bash
cp .env.example .env
```

### 5.2 Editar `.env`

Abrir `.env` con cualquier editor y rellenar:

```env
# Flask
SECRET_KEY=cambia-esto-por-una-clave-secreta-larga-y-aleatoria
FLASK_ENV=development

# Base de datos (dejar así para SQLite local)
DATABASE_URL=sqlite:///agent.db

# Cifrado de credenciales (dejar vacío = se genera automáticamente)
# Si lo generas manualmente: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=

# Microsoft Graph API
GRAPH_API_ENDPOINT=https://graph.microsoft.com/v1.0

# Azure AD — rellenar con los valores del Paso 1
OUTLOOK_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
OUTLOOK_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
OUTLOOK_CLIENT_SECRET=tu-client-secret-aqui
```

> **Nota sobre `FERNET_KEY`:** Si se deja vacío, la clave se genera automáticamente en el primer arranque. Esto es cómodo para desarrollo pero en producción debes generar una clave fija y guardarla, o las credenciales almacenadas en DB quedarán inutilizables si el servidor se reinicia.

Para generar una clave Fernet fija:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Paso 6 — Inicializar la base de datos

```bash
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

Esto creará el archivo `instance/agent.db` con todas las tablas.

> Si ves el error `"Target database is not up to date"`, ejecuta solo `flask db upgrade`.

---

## Paso 7 — Arrancar la aplicación

### Desarrollo (Windows)

```bash
python run.py
```

### Desarrollo (macOS / Linux)

```bash
python run.py
```

### Producción con Gunicorn (Linux/Mac)

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"
```

La aplicación estará disponible en **[http://localhost:5000](http://localhost:5000)**

---

## Paso 8 — Configuración inicial en la interfaz

Al abrir la aplicación por primera vez serás redirigido a **`/setup`**.

### 8.1 Wizard de configuración

**Paso 1 — Credenciales:**
1. Introducir los valores del Paso 1 de esta guía:
   - Tenant ID
   - Client ID
   - Client Secret
   - Email del buzón del agente (el buzón desde el que se enviarán los emails)
2. Click **"Test Connection"** — esperar confirmación verde

**Paso 2 — Verificar:**
- La app mostrará el nombre del usuario recuperado de Azure AD
- Si hay error, revisar los permisos de API del Paso 1.5

**Paso 3 — Guardar:**
- Click **"Guardar Conexión"**
- La app creará automáticamente las 4 categorías por defecto (Blue, Manager, Senior Manager, VIP)

---

## Paso 9 — Verificar que funciona

### Comprobar la conexión

```bash
curl http://localhost:5000/api/connection
```

Debería devolver los datos de la conexión activa.

### Comprobar las categorías

```bash
curl http://localhost:5000/api/categories
```

Debería devolver las 4 categorías por defecto.

### Comprobar el scheduler

En los logs del servidor deberías ver líneas como:

```
[INFO] scheduler: sync_contacts_job arrancado
[INFO] scheduler: check_responses_job arrancado
[INFO] scheduler: send_reminders_job arrancado
```

---

## Paso 10 — Uso básico

1. Ir a **`/categories`** — ajustar las horas de recordatorio por categoría si es necesario
2. Ir a **`/dashboard`** — usar el botón **"Nuevo Email"** para enviar el primer email
3. Seleccionar un contacto (o sincronizar desde Outlook con **"Sincronizar Contactos"**)
4. El agente monitoriza la conversación y enviará un recordatorio automáticamente si no hay respuesta

---

## Solución de problemas

### Error: `No module named 'app'`

Asegúrate de estar en el directorio raíz del proyecto y tener el entorno virtual activo.

### Error: `AADSTS700016: Application not found`

El `OUTLOOK_CLIENT_ID` o `OUTLOOK_TENANT_ID` son incorrectos. Verificar en Azure Portal.

### Error: `AADSTS7000215: Invalid client secret`

El `OUTLOOK_CLIENT_SECRET` es incorrecto o ha expirado. Crear uno nuevo en Azure Portal.

### Error: `Insufficient privileges to complete the operation`

Los permisos de API no han recibido admin consent. Repetir el Paso 1.5.

### Las credenciales guardadas no funcionan tras reiniciar

`FERNET_KEY` no está configurado en `.env`. La clave cambió al reiniciar. Solución: generar una clave fija y añadirla al `.env` (ver Paso 5.2).

### El scheduler no detecta respuestas

- Verificar que el permiso `Mail.Read` tiene admin consent
- Verificar en los logs que `check_responses_job` se ejecuta sin errores
- Comprobar que el `conversation_id` se guardó correctamente al enviar el email

---

## Despliegue en producción

### Variables de entorno recomendadas en producción

```env
FLASK_ENV=production
SECRET_KEY=clave-muy-larga-y-aleatoria-minimo-64-caracteres
FERNET_KEY=clave-fernet-fija-generada-una-sola-vez
DATABASE_URL=sqlite:///agent.db   # o PostgreSQL en producción
```

### Con systemd (Linux)

Crear `/etc/systemd/system/outlook-reminder.service`:

```ini
[Unit]
Description=Outlook Smart Reminder System
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/outlook-smart-reminder-system
Environment="PATH=/opt/outlook-smart-reminder-system/venv/bin"
ExecStart=/opt/outlook-smart-reminder-system/venv/bin/gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable outlook-reminder
systemctl start outlook-reminder
```

### Con Docker (opcional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV FLASK_ENV=production
EXPOSE 5000
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:create_app()"]
```

```bash
docker build -t outlook-reminder .
docker run -p 5000:5000 --env-file .env outlook-reminder
```

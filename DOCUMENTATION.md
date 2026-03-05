# Outlook Smart Reminder System — Documentación técnica

---

## Índice

1. [Visión general](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Tecnologías utilizadas](#tecnologías-utilizadas)
4. [Modelos de datos](#modelos-de-datos)
5. [Servicios](#servicios)
6. [API REST](#api-rest)
7. [Scheduler — Jobs automáticos](#scheduler--jobs-automáticos)
8. [Sistema de categorías](#sistema-de-categorías)
9. [Detección de respuestas y etiquetas](#detección-de-respuestas-y-etiquetas)
10. [Motor de recordatorios](#motor-de-recordatorios)
11. [Seguridad y cifrado](#seguridad-y-cifrado)
12. [Frontend](#frontend)
13. [Estructura del proyecto](#estructura-del-proyecto)

---

## Visión general

**Outlook Smart Reminder System** es una herramienta web interna para Accenture que automatiza el seguimiento de emails enviados a través de Microsoft Outlook / Office 365. Usa la **API oficial de Microsoft Graph** con autenticación OAuth2 delegada (Device Code Flow), eliminando la necesidad de contraseñas de aplicación o configuración SMTP.

```
Usuario envía email
       │
       ▼
SentEmail guardado en DB
(reminder_at = sent_at + horas_categoría)
       │
       ▼
Scheduler check_responses (cada 15 min) — Graph API
       ├─ ¿Hay respuesta? → status = "replied"
       └─ ¿Etiqueta en respuesta? → reprogramar custom_reminder_at
       │
       ▼
Scheduler send_reminders (cada 1h) — Graph API
       └─ SentEmail vencido sin respuesta → enviar recordatorio
```

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                     Flask Application                         │
│                                                               │
│  ┌──────────┐    ┌─────────────────────┐    ┌─────────────┐  │
│  │ routes.py│───►│ DelegatedGraphService│───►│ Graph API   │  │
│  │ (HTTP)   │    │ (OAuth2 + MSAL)     │    │ Microsoft   │  │
│  └──────────┘    └─────────────────────┘    │ graph.ms.com│  │
│       │                    │                └─────────────┘  │
│       ▼                    ▼                                  │
│  ┌──────────┐   ┌───────────────────┐                        │
│  │ models.py│   │ CategoryManager   │                        │
│  │ SQLite   │   │ ReminderEngine    │                        │
│  └──────────┘   └───────────────────┘                        │
│       │                    │                                  │
│       └────────────────────┴──► APScheduler (3 jobs)         │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ OAuth2 Device Code Flow                                 │  │
│  │ /api/auth/device-code/start → MSAL → user_code+URL     │  │
│  │ /api/auth/device-code/poll  → token endpoint → login.ms│  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

**Patrón:** Application Factory (`create_app()`), Blueprint `main`, servicios como clases Python.  
**Autenticación:** OAuth2 Device Code Flow (delegated permissions). El usuario autoriza la app desde un navegador y el refresh token se persiste cifrado en SQLite.  
**Alternativa Gmail:** SMTPService con App Password para cuentas Google.

---

## Tecnologías utilizadas

### Backend

| Tecnología | Versión | Rol |
|------------|---------|-----|
| **Python** | 3.10+ | Lenguaje base |
| **Flask** | 3.x | Framework web |
| **SQLAlchemy** | 2.x | ORM |
| **APScheduler** | 3.x | Jobs periódicos en background |
| **MSAL** | 1.20+ | Microsoft Authentication Library — OAuth2 Device Code Flow |
| **requests** | 2.31+ | Llamadas a Microsoft Graph REST API |
| **cryptography (Fernet)** | 41+ | Cifrado AES del refresh token |
| **python-dateutil** | 2.8+ | Parsing y cálculo de fechas |

### API externa

| API | Descripción |
|-----|-------------|
| **Microsoft Graph v1.0** | `https://graph.microsoft.com/v1.0` — envío de email (`/me/sendMail`), lectura de mensajes (`/me/messages`), contactos (`/me/contacts`), categorías (`/me/outlook/masterCategories`) |
| **Microsoft Identity Platform** | `https://login.microsoftonline.com/common/oauth2/v2.0/token` — intercambio de device code por access + refresh token |

### Permisos OAuth2 requeridos (delegated)

| Permiso | Uso |
|---------|-----|
| `Mail.Send` | Enviar emails como el usuario |
| `Mail.ReadWrite` | Leer mensajes y conversaciones para detectar respuestas |
| `Contacts.Read` | Sincronizar contactos de Outlook |
| `User.Read` | Obtener el email y nombre del usuario autenticado |
| `offline_access` | Obtener refresh token para acceso persistente |

### Base de datos

- **SQLite** local (`instance/agent.db`)
- Compatible con PostgreSQL cambiando `DATABASE_URL` en `.env`

### Alternativa Gmail / SMTP

Para cuentas Google con App Password:

| Componente | Detalle |
|------------|---------|
| **smtplib** | Envío de emails (stdlib Python) |
| **imaplib** | Lectura de respuestas (stdlib Python) |
| Servidores | `smtp.gmail.com:587` / `imap.gmail.com:993` |

### Frontend

| Tecnología | Rol |
|------------|-----|
| **Bootstrap 5** | Grid, modals, cards, tablas |
| **Vanilla JS + Fetch API** | Lógica de páginas y llamadas AJAX |
| **Jinja2** | Templating server-side |

### Identidad visual — Accenture

- Color primario: `#000000` (negro)
- Acento: `#A100FF` (morado Accenture)
- Tipografía: Inter (Google Fonts)
- Logo: símbolo `>` (chevron Accenture)
- Bordes: `0px` border-radius (sharp corners)

---

## Modelos de datos

### `OutlookConnection`

Almacena las credenciales de la cuenta de correo. Soporta dos modos según `backend_type`.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `backend_type` | String | `"delegated"` (Outlook OAuth2) o `"smtp"` (Gmail) |
| `client_id` | String | Application (Client) ID del registro de app Azure (solo modo delegated) |
| `user_email` | String | Dirección de correo del usuario autenticado |
| `display_name` | String | Nombre visible |
| `password_enc` | Text | **Refresh token** (modo delegated) o contraseña App Password (modo smtp), cifrado con Fernet |
| `smtp_host` | String | Solo modo smtp. Default: `smtp.gmail.com` |
| `smtp_port` | Integer | Solo modo smtp. Default: `587` |
| `imap_host` | String | Solo modo smtp. Default: `imap.gmail.com` |
| `imap_port` | Integer | Solo modo smtp. Default: `993` |
| `is_active` | Boolean | Si es la conexión activa |
| `created_at` | DateTime | |

### `CategoryRule`

Define reglas de categorías: nombre, color y tiempo de espera antes de recordar.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `name` | String UNIQUE | Nombre (ej. "Manager") |
| `color` | String | Preset de color para el UI (`preset0`–`preset14`) |
| `reminder_hours` | Integer | Horas sin respuesta antes del recordatorio |
| `description` | String | Texto libre |

**Categorías creadas automáticamente al conectar:**

| Nombre | Recordatorio |
|--------|-------------|
| Blue | 24 h |
| Manager | 48 h |
| Senior Manager | 72 h |
| VIP | 96 h |

### `Contact`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `email` | String UNIQUE | |
| `display_name` | String | Nombre completo |
| `job_title` | String | Cargo |
| `company_name` | String | Empresa |
| `category_id` | FK → CategoryRule | Categoría asignada |
| `notes` | Text | Notas internas |

### `SentEmail`

Registro de cada email enviado. Núcleo del sistema de tracking.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `contact_id` | FK → Contact | |
| `connection_id` | FK → OutlookConnection | |
| `subject` | String | Asunto del email |
| `body_preview` | Text | Primeros 300 caracteres |
| `message_id` | String | Internet Message-ID para threading |
| `conversation_id` | String | Graph API `conversationId` (modo delegated) |
| `sent_at` | DateTime | Cuándo se envió |
| `reminder_at` | DateTime | Recordatorio calculado por categoría |
| `custom_reminder_at` | DateTime | Override por etiqueta detectada en respuesta |
| `reminder_sent_at` | DateTime | Cuándo se envió el último recordatorio |
| `replied_at` | DateTime | Cuándo se detectó la respuesta |
| `response_label` | String | Etiqueta detectada (ej. `"2_days"`) |
| `status` | String | `pending` · `replied` · `reminder_sent` · `snoozed` · `closed` |

**Propiedad calculada:** `effective_reminder_at` → `custom_reminder_at` si existe, si no `reminder_at`.

### `Reminder`

Log histórico de cada recordatorio enviado.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `sent_email_id` | FK → SentEmail | |
| `sent_at` | DateTime | Cuándo se envió el recordatorio |
| `notes` | Text | Log adicional |

---

## Servicios

### `DelegatedGraphService` (`app/delegated_service.py`)

Servicio principal para cuentas Microsoft Outlook. Usa el refresh token almacenado para obtener access tokens via MSAL y llama a Microsoft Graph REST API.

```python
svc = DelegatedGraphService(conn_id=1)  # carga la conexión de DB por ID
ok, msg = svc.validate_connection()
result = svc.send_email(to_email, subject, body_html, category="Blue")
```

| Método | Descripción |
|--------|-------------|
| `_get_access_token()` | Devuelve access token válido; refresca via MSAL si ha expirado. Persiste nuevo refresh token si Microsoft lo rota |
| `validate_connection()` | `GET /me` → comprueba autenticación. Devuelve `(ok: bool, message: str)` |
| `send_email(to, subject, body_html, category?)` | `POST /me/sendMail` + recupera `conversationId` de SentItems. Asigna categoría si se indica |
| `has_reply(conversation_id, sent_at)` | `GET /me/messages?$filter=conversationId eq ...` → busca mensajes del destinatario posteriores al envío |
| `detect_response_labels(conversation_id, sent_at)` | Descarga cuerpo del mensaje de respuesta y aplica regex de etiquetas |
| `sync_contacts()` | `GET /me/contacts` → lista de contactos de Outlook |
| `ensure_category_exists(name, color)` | `GET/POST /me/outlook/masterCategories` — sincroniza categorías con Outlook |

### `SMTPService` (`app/smtp_service.py`)

Alternativa para cuentas Gmail con App Password. Usa `smtplib` + `imaplib` (stdlib Python, sin SDKs externos).

| Método | Descripción |
|--------|-------------|
| `validate_connection()` | Prueba login SMTP con auto-fallback 587→465 |
| `send_email(to, subject, body_html, ...)` | Envía via SMTP, devuelve `{message_id, conversation_id}` |
| `has_reply(message_id, sent_at)` | Busca en IMAP INBOX por header `In-Reply-To` |
| `detect_response_labels(...)` | Aplica regex sobre el cuerpo del mensaje de respuesta |

### `CategoryManager` (`app/category_manager.py`)

| Método | Descripción |
|--------|-------------|
| `assign_category(contact_id, category_id)` | Asigna categoría en DB |
| `get_reminder_hours(contact_id)` | Horas de la categoría del contacto (default: 48h) |
| `calculate_reminder_at(sent_at, hours)` | `sent_at + timedelta(hours=hours)` |
| `process_response_label(sent_email_id, label)` | Calcula `custom_reminder_at` según etiqueta detectada |
| `seed_default_categories()` | Crea las 4 categorías por defecto si la tabla está vacía |

### `ReminderEngine` (`app/reminder_engine.py`)

| Método | Descripción |
|--------|-------------|
| `get_pending_reminders()` | `SentEmail` vencidos con `status in (pending, snoozed)` y sin respuesta |
| `get_upcoming_reminders(hours_ahead)` | Próximos a vencer en N horas |
| `send_reminder(sent_email_id, svc)` | Envía recordatorio, crea registro `Reminder`, actualiza status |
| `snooze(sent_email_id, hours)` | `custom_reminder_at = now + hours`, `status = snoozed` |
| `close(sent_email_id)` | `status = closed` |

---

## API REST

Todas las respuestas son JSON. Errores → `{"error": "mensaje"}` con código HTTP correspondiente.

### Autenticación OAuth2 (Device Code Flow)

| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| `POST` | `/api/auth/device-code/start` | `{client_id}` | `{user_code, verification_uri, device_code, expires_in, message}` |
| `POST` | `/api/auth/device-code/poll` | `{device_code}` | `{status: "ok"\|"pending"\|"expired"\|"error", email?, name?}` |

**Flujo:**
1. `start` → MSAL genera `user_code` + URL → el usuario visita la URL y escribe el código en Microsoft
2. `poll` → el frontend llama cada 5s hasta que `status == "ok"` → conexión guardada, redirige al dashboard

### Conexión (Gmail / SMTP)

| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| `POST` | `/api/outlook/test` | `{user_email, password, smtp_host?, smtp_port?, imap_host?, imap_port?}` | `{ok, message}` |
| `POST` | `/api/outlook/connect` | Igual que test | `{message, connection}` |
| `GET` | `/api/connection` | — | `{connection}` |
| `POST` | `/api/outlook/disconnect` | — | `{message}` |

### Categorías

| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| `GET` | `/api/categories` | — | `{categories: [...]}` |
| `POST` | `/api/categories` | `{name, color?, reminder_hours?, description?}` | `{category}` 201 |
| `PUT` | `/api/categories/{id}` | Campos a actualizar | `{category}` |
| `DELETE` | `/api/categories/{id}` | — | `{message}` |

### Contactos

| Método | Ruta | Query / Body | Respuesta |
|--------|------|-------------|-----------|
| `GET` | `/api/contacts` | `?q=&category_id=` | `{contacts: [...]}` |
| `POST` | `/api/contacts` | `{email, display_name?, job_title?, company_name?}` | `{contact}` 201 |
| `POST` | `/api/contacts/sync` | — | Sincroniza desde Outlook (modo delegated) |
| `POST` | `/api/contacts/{id}/category` | `{category_id}` | `{contact}` |
| `DELETE` | `/api/contacts/{id}` | — | `{message}` |

### Emails

| Método | Ruta | Body / Query | Respuesta |
|--------|------|-------------|-----------|
| `POST` | `/api/emails/send` | `{contact_id, subject, body_html, body_text?}` | `{message, sent_email}` 201 |
| `GET` | `/api/emails` | `?status=&contact_id=` | `{emails: [...]}` |

### Recordatorios

| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| `GET` | `/api/reminders/pending` | — | `{reminders: [...]}` |
| `GET` | `/api/reminders/upcoming` | `?hours=24` | `{reminders: [...]}` |
| `POST` | `/api/reminders/{id}/send-now` | — | `{message, sent_email}` |
| `POST` | `/api/reminders/{id}/snooze` | `{hours: 24}` | `{message, sent_email}` |
| `POST` | `/api/reminders/{id}/close` | — | `{message, sent_email}` |

### Dashboard

| Método | Ruta | Respuesta |
|--------|------|-----------|
| `GET` | `/api/dashboard/stats` | Estadísticas completas + actividad reciente |
| `GET` | `/api/activity` | Últimos 50 eventos |

---

## Scheduler — Jobs automáticos

Configurado con **APScheduler** (`BackgroundScheduler`), arranca en `run.py`.

### `sync_contacts_job` — cada 6 horas

- Modo **delegated**: `DelegatedGraphService.sync_contacts()` → `GET /me/contacts` → crea/actualiza `Contact` en DB
- Modo **smtp**: sin efecto (IMAP no expone contactos)

### `check_responses_job` — cada 15 minutos

Para cada `SentEmail` con `status = "pending"`:

1. `svc.has_reply(conversation_id, sent_at)` — busca respuesta
2. Si hay respuesta → `status = "replied"`, `replied_at = now`
3. `svc.detect_response_labels(...)` — escanea cuerpo con regex
4. Si detecta etiqueta → `CategoryManager.process_response_label(...)` reprograma `custom_reminder_at`

### `send_reminders_job` — cada 1 hora

Para cada `SentEmail` vencido (`ReminderEngine.get_pending_reminders()`):

1. Envía email de recordatorio via Graph API o SMTP según `backend_type`
2. Crea registro `Reminder` en DB
3. Actualiza `status = "reminder_sent"`

---

## Sistema de categorías

Las categorías definen cuánto tiempo esperar antes de recordar según el tipo de contacto.

**Flujo:**
1. Se crea una `CategoryRule` con `nombre` + `color` + `reminder_hours`
2. Se asigna al `Contact`
3. Al enviar email: `reminder_at = sent_at + timedelta(hours=category.reminder_hours)`
4. Si el contacto no tiene categoría asignada: se usan 48 horas por defecto

---

## Detección de respuestas y etiquetas

### Modo delegated (Graph API)

```python
# GET /me/messages?$filter=conversationId eq '{id}' and receivedDateTime gt {sent_at}
# Compara from.emailAddress.address con el email del destinatario original
```

### Modo smtp (IMAP)

```python
# Busca en INBOX por header In-Reply-To y References
mail.search(None, f'SINCE "{since}" HEADER "In-Reply-To" "<{message_id}>"')
```

### Detección de etiquetas (regex)

Aplica expresiones regulares sobre el cuerpo del mensaje de respuesta:

| Patrón | Etiqueta | Nuevo recordatorio |
|--------|---------|-------------------|
| `contestar después de N día(s)` | `N_days` | `now + N * 24h` |
| `reply in N day(s)` | `N_days` | `now + N * 24h` |
| `al final del día` / `end of day` | `end_of_day` | Hoy a las 18:00 UTC |
| `mañana` / `tomorrow` | `tomorrow` | Mañana a las 09:00 UTC |

---

## Motor de recordatorios

### Condición de recordatorio vencido

```python
effective_reminder_at <= datetime.utcnow()
AND status in ("pending", "snoozed")
AND replied_at IS NULL
```

`effective_reminder_at` = `custom_reminder_at` si existe, si no `reminder_at`.

### Email de recordatorio

Se envía como email nuevo con asunto `Re: {asunto original}` y cuerpo personalizado indicando el nombre del contacto y las horas transcurridas sin respuesta.

---

## Seguridad y cifrado

- El **refresh token OAuth2** (o App Password en modo Gmail) se cifra con **Fernet** (AES-128-CBC + HMAC-SHA256) antes de guardarse en SQLite
- `FERNET_KEY` se genera automáticamente al arrancar si no está en `.env`. Guardarlo en `.env` garantiza que las credenciales persistan entre reinicios del servidor
- Las credenciales **nunca aparecen en logs ni en respuestas de API**
- El `client_id` de Azure es un identificador público — no es un secreto
- Todo corre en local. Las únicas conexiones externas son:
  - `login.microsoftonline.com` — autenticación OAuth2
  - `graph.microsoft.com` — envío y lectura de emails

---

## Frontend

### Páginas

| Ruta | Plantilla | Descripción |
|------|-----------|-------------|
| `/setup` | `setup.html` | Dos pestañas: **Outlook** (OAuth2 Device Code Flow: pegar Client ID → botón → muestra código + URL → polling automático) y **Gmail** (email + App Password) |
| `/categories` | `categories.html` | Tabla CRUD de categorías con modal |
| `/dashboard` | `dashboard.html` | Stats cards + recordatorios pendientes + timeline de actividad. Auto-refresh cada 30s |

### Auto-refresh del dashboard

El dashboard hace polling a `/api/dashboard/stats` cada 30 segundos para mantener los datos actualizados sin recargar la página.

### Arquitectura JS

Cada template incluye su lógica JS inline. `static/js/app.js` contiene utilidades compartidas:

| Función | Descripción |
|---------|-------------|
| `formatDate(iso)` | Fecha legible en español |
| `timeAgo(iso)` | "hace 3 horas" |
| `showToast(message, type)` | Notificaciones Bootstrap |
| `apiCall(url, method, body)` | Wrapper Fetch con manejo de errores |

---

## Estructura del proyecto

```
outlook-smart-reminder-system/
├── app/
│   ├── __init__.py              # Application factory, extensiones Flask
│   ├── models.py                # Modelos SQLAlchemy (5 modelos)
│   ├── routes.py                # 29 endpoints HTTP (páginas + API REST)
│   ├── delegated_service.py     # Microsoft Graph API — OAuth2 delegado
│   ├── smtp_service.py          # Alternativa Gmail — SMTP/IMAP
│   ├── category_manager.py      # Lógica de categorías y scheduling
│   ├── reminder_engine.py       # Motor de recordatorios
│   ├── scheduler.py             # APScheduler (3 jobs automáticos)
│   ├── crypto.py                # Cifrado Fernet
│   └── templates/
│       ├── base.html            # Layout base Accenture brand
│       ├── setup.html           # Wizard conexión: Outlook OAuth + Gmail
│       ├── categories.html      # CRUD categorías
│       └── dashboard.html       # Dashboard principal
├── static/
│   ├── css/style.css            # Estilos Accenture brand
│   └── js/app.js                # Utilidades JS compartidas
├── config.py                    # Configuración Flask
├── run.py                       # Entry point
├── requirements.txt             # Dependencias Python
├── .env.example                 # Variables de entorno de ejemplo
├── README.md                    # Resumen del proyecto
├── DOCUMENTATION.md             # Este documento
├── SETUP.md                     # Guía de instalación paso a paso
└── PRESENTATION.md              # Presentación del agente para Accenture
```

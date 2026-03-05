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

---

## Visión general

**Outlook Smart Reminder System** es una herramienta web interna para Accenture que automatiza el seguimiento de emails enviados a través de Office 365. En lugar de mantener listas manuales en Excel o configurar SMTP/IMAP, la aplicación se conecta directamente a la cuenta de correo corporativa mediante **Microsoft Graph API** y gestiona todo el ciclo de vida de un email: envío → detección de respuesta → recordatorio automático → reprogramación por etiquetas.

### Flujo principal

```
Usuario envía email
       │
       ▼
SentEmail guardado en DB
(reminder_at = sent_at + horas_categoría)
       │
       ▼
Scheduler check_responses (cada 15 min)
       ├─ ¿Hay respuesta? → status = "replied"
       └─ ¿Hay etiqueta en respuesta? → reprogramar custom_reminder_at
       │
       ▼
Scheduler send_reminders (cada 1h)
       └─ SentEmail vencido y sin respuesta → enviar recordatorio
```

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                       │
│                                                              │
│  ┌──────────┐    ┌────────────────┐    ┌─────────────────┐  │
│  │ routes.py│───►│ OutlookService │───►│ Microsoft Graph │  │
│  │ (HTTP)   │    │ (Graph API)    │    │     API v1.0    │  │
│  └──────────┘    └────────────────┘    └─────────────────┘  │
│       │                  │                                   │
│       ▼                  ▼                                   │
│  ┌──────────┐    ┌────────────────┐                         │
│  │ models.py│    │CategoryManager │                         │
│  │ SQLite   │    │ReminderEngine  │                         │
│  └──────────┘    └────────────────┘                         │
│       │                  │                                   │
│       └──────────────────┴──► APScheduler (3 jobs)          │
└─────────────────────────────────────────────────────────────┘
```

**Patrón:** Application Factory (`create_app()`), Blueprint `main` para todas las rutas, servicios como clases Python puras sin estado en Flask.

---

## Tecnologías utilizadas

### Backend

| Tecnología | Versión | Rol |
|------------|---------|-----|
| **Python** | 3.10+ | Lenguaje base |
| **Flask** | 3.x | Framework web |
| **SQLAlchemy** | 2.x | ORM — modelos y consultas |
| **Flask-Migrate** | 4.x | Migraciones de base de datos (Alembic) |
| **APScheduler** | 3.x | Jobs periódicos en background |
| **MSAL** | 1.20+ | Autenticación Microsoft (OAuth 2.0 client credentials) |
| **requests** | 2.31+ | Llamadas HTTP a Microsoft Graph API |
| **python-dateutil** | 2.8+ | Parsing y cálculo de fechas |
| **cryptography (Fernet)** | 41+ | Cifrado simétrico AES de credenciales |

### Base de datos

- **SQLite** en desarrollo/producción ligera (`instance/agent.db`)
- Compatible con PostgreSQL cambiando `DATABASE_URL` (sin cambios en código gracias a SQLAlchemy)

### API externa

- **Microsoft Graph API v1.0** — endpoints utilizados:
  - `GET /me` — validar token y obtener nombre de usuario
  - `POST /users/{email}/sendMail` — enviar emails
  - `GET /users/{email}/messages` — listar mensajes (reply detection)
  - `GET /users/{email}/contacts` — sincronizar contactos
  - `POST /users/{email}/outlook/masterCategories` — crear categorías de Outlook
  - `GET /users/{email}/outlook/masterCategories` — listar categorías

### Frontend

| Tecnología | Rol |
|------------|-----|
| **Bootstrap 5** | Grid, componentes UI (modals, cards, tables) |
| **Vanilla JS** | Lógica de páginas sin frameworks |
| **Fetch API** | Llamadas AJAX a los endpoints REST |
| **Jinja2** | Templating server-side (Flask) |

### Identidad visual

- **Marca:** Accenture
- **Colores:** Negro `#000000` (primario) · Morado `#A100FF` (acento)
- **Tipografía:** Inter (Google Fonts)
- **Logo:** símbolo `>` (chevron Accenture)
- **Estilo:** Bordes sharp (0px border-radius), tipografía uppercase en labels

---

## Modelos de datos

### `OutlookConnection`

Almacena las credenciales Azure AD para conectar con Office 365. Solo puede haber una activa (`is_active=True`).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `tenant_id` | String | Directory (tenant) ID de Azure AD |
| `client_id` | String | Application (client) ID |
| `client_secret_enc` | String | Client secret **cifrado con Fernet** |
| `user_email` | String | Buzón de correo del agente |
| `display_name` | String | Nombre del usuario (del token) |
| `is_active` | Boolean | Si es la conexión activa |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

### `CategoryRule`

Define las reglas de categorías: qué etiqueta de Outlook asignar y cuántas horas esperar antes de recordar.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `name` | String UNIQUE | Nombre de la categoría (ej. "Manager") |
| `color` | String | Preset de color Outlook (`preset0`–`preset24`) |
| `reminder_hours` | Integer | Horas a esperar sin respuesta antes de recordar |
| `description` | String | Texto libre |

**Categorías por defecto (seed automático):**

| Nombre | Color | Recordatorio |
|--------|-------|-------------|
| Blue | `preset4` (azul) | 24h |
| Manager | `preset3` (verde) | 48h |
| Senior Manager | `preset2` (naranja) | 72h |
| VIP | `preset1` (rojo) | 96h |

### `Contact`

Contacto sincronizado desde Outlook o creado manualmente.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `email` | String UNIQUE | |
| `display_name` | String | Nombre completo |
| `job_title` | String | Cargo |
| `company_name` | String | Empresa |
| `outlook_id` | String | ID en Microsoft Graph (si sincronizado) |
| `category_id` | FK → CategoryRule | Categoría asignada |
| `notes` | Text | Notas internas |
| `created_at` / `updated_at` | DateTime | |

### `SentEmail`

Registro de cada email enviado. Núcleo del sistema de tracking.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `contact_id` | FK → Contact | |
| `connection_id` | FK → OutlookConnection | |
| `subject` | String | Asunto del email |
| `body_preview` | Text | Primeros 300 caracteres del cuerpo |
| `message_id` | String | `internetMessageId` para tracking IMAP |
| `conversation_id` | String | `conversationId` de Graph API |
| `graph_message_id` | String | `id` del mensaje en Graph |
| `sent_at` | DateTime | Cuándo se envió |
| `reminder_at` | DateTime | Recordatorio calculado por categoría |
| `custom_reminder_at` | DateTime | Override por etiqueta en respuesta |
| `reminder_sent_at` | DateTime | Cuándo se envió el último recordatorio |
| `replied_at` | DateTime | Cuándo se detectó respuesta |
| `response_label` | String | Etiqueta detectada (ej. `"2_days"`) |
| `status` | String | `pending`, `replied`, `reminder_sent`, `snoozed`, `closed` |

**Propiedad calculada:** `effective_reminder_at` → devuelve `custom_reminder_at` si existe, sino `reminder_at`.

### `Reminder`

Log histórico de cada recordatorio enviado (N recordatorios por SentEmail).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `sent_email_id` | FK → SentEmail | |
| `sent_at` | DateTime | Cuándo se envió el recordatorio |
| `subject` | String | Asunto del recordatorio |
| `notes` | Text | Log adicional |

---

## Servicios

### `OutlookService` (`app/outlook_service.py`)

Wrapper sobre Microsoft Graph API. Usa MSAL con **client credentials flow** (sin usuario, solo app permissions).

```python
svc = OutlookService(tenant_id, client_id, client_secret, user_email)
```

Métodos principales:

| Método | Descripción |
|--------|-------------|
| `get_access_token()` | Obtiene token OAuth2 via MSAL (cacheable) |
| `validate_connection()` | Llama a `/me` o `/users/{email}` para verificar credenciales |
| `send_email(to, subject, body_html, body_text, category)` | Envía email via Graph, devuelve `message_id` y `conversation_id` |
| `has_reply(conversation_id, sent_at)` | Comprueba si hay mensajes en la conversación posteriores a `sent_at` con sender ≠ `user_email` |
| `detect_response_labels(conversation_id, sent_at)` | Escanea texto de respuestas con regex para detectar etiquetas de reprogramación |
| `sync_contacts()` | Devuelve lista de contactos del buzón desde Graph |
| `ensure_category_exists(name, color_preset)` | Crea la categoría en Outlook si no existe |
| `get_master_categories()` | Lista categorías de Outlook del buzón |

### `CategoryManager` (`app/category_manager.py`)

Gestiona la asignación de categorías y el cálculo de tiempos de recordatorio.

| Método | Descripción |
|--------|-------------|
| `assign_category(contact_id, category_id)` | Asigna categoría a un contacto en DB |
| `get_reminder_hours(contact_id)` | Devuelve horas de recordatorio del contacto (default: 48h) |
| `calculate_reminder_at(sent_at, hours)` | Calcula la fecha absoluta del recordatorio |
| `process_response_label(sent_email_id, label)` | Actualiza `custom_reminder_at` según etiqueta detectada |
| `seed_default_categories()` | Crea las 4 categorías por defecto si la tabla está vacía |

**Etiquetas soportadas:**

| Label | Reprogramación |
|-------|----------------|
| `1_day` | `now + 24h` |
| `2_days` | `now + 48h` |
| `3_days` | `now + 72h` |
| `end_of_day` | Hoy a las 18:00 |
| `tomorrow` | Mañana a las 09:00 |

### `ReminderEngine` (`app/reminder_engine.py`)

Motor de recordatorios: detecta los que hay que enviar y los despacha.

| Método | Descripción |
|--------|-------------|
| `get_pending_reminders()` | `SentEmail` con `effective_reminder_at <= now` y `status in (pending, snoozed)` |
| `get_upcoming_reminders(hours_ahead)` | Próximos N horas (para dashboard) |
| `send_reminder(sent_email_id, svc)` | Envía recordatorio via Graph, crea `Reminder`, actualiza `status = reminder_sent` |
| `snooze(sent_email_id, hours)` | Actualiza `custom_reminder_at = now + hours`, `status = snoozed` |
| `close(sent_email_id)` | `status = closed` |

---

## API REST

Todas las respuestas son JSON. Errores devuelven `{"error": "mensaje"}` con el código HTTP apropiado.

### Conexión Outlook

| Método | Ruta | Body | Respuesta |
|--------|------|------|-----------|
| `POST` | `/api/outlook/test` | `{tenant_id, client_id, client_secret, user_email}` | `{ok, message}` |
| `POST` | `/api/outlook/connect` | `{tenant_id, client_id, client_secret, user_email}` | `{message, connection}` |
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

| Método | Ruta | Body / Query | Respuesta |
|--------|------|-------------|-----------|
| `GET` | `/api/contacts` | `?q=&category_id=` | `{contacts: [...]}` |
| `POST` | `/api/contacts` | `{email, display_name?, ...}` | `{contact}` 201 |
| `POST` | `/api/contacts/sync` | — | `{message, total, new}` |
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
| `GET` | `/api/activity` | Últimos 50 eventos (recordatorios + respuestas) |

---

## Scheduler — Jobs automáticos

Configurado con **APScheduler** (`BackgroundScheduler`) arrancado en `run.py` via `start_scheduler(app)`.

### `sync_contacts_job` — cada 6 horas

Sincroniza contactos desde Outlook Graph. Para cada contacto recibido:
- Si existe en DB → actualiza `display_name`, `job_title`, `company_name`, `outlook_id`
- Si no existe → crea nuevo `Contact` (sin categoría asignada)

### `check_responses_job` — cada 15 minutos

Para cada `SentEmail` con `status = "pending"`:
1. Llama a `OutlookService.has_reply(conversation_id, sent_at)`
2. Si hay respuesta → `status = "replied"`, `replied_at = now`
3. Llama a `OutlookService.detect_response_labels(...)` para buscar etiquetas
4. Si detecta etiqueta → `CategoryManager.process_response_label(...)` reprograma

### `send_reminders_job` — cada 1 hora

Para cada `SentEmail` vencido (via `ReminderEngine.get_pending_reminders()`):
1. Llama a `ReminderEngine.send_reminder(sent_email_id, svc)`
2. El recordatorio se envía como respuesta a la conversación original
3. Se crea registro `Reminder` en DB

---

## Sistema de categorías

Las categorías son la clave para personalizar el comportamiento del agente por tipo de contacto.

**Flujo:**
1. Se define una `CategoryRule` con `nombre` + `color` + `reminder_hours`
2. Se asigna la categoría a un `Contact`
3. Al enviar un email a ese contacto, `reminder_at = sent_at + category.reminder_hours`
4. Opcionalmente, la categoría se sincroniza con Outlook (aparece en el cliente de correo del usuario)

**Colores Outlook (presets):**

| Preset | Color |
|--------|-------|
| preset0 | Rojo |
| preset1 | Naranja |
| preset2 | Marrón |
| preset3 | Verde amarillo |
| preset4 | Verde |
| preset5 | Teal |
| preset6 | Oliva |
| preset7 | Azul |
| preset8 | Morado |
| preset9 | Cranberry |

---

## Detección de respuestas y etiquetas

### Detección de respuesta

`OutlookService.has_reply()` consulta la conversación en Graph:

```
GET /users/{email}/messages
  ?$filter=conversationId eq '{id}' and receivedDateTime gt {sent_at}
  &$select=sender,receivedDateTime
```

Una respuesta se detecta si hay un mensaje con `sender.emailAddress.address ≠ user_email`.

### Detección de etiquetas

`detect_response_labels()` descarga el body de cada mensaje de respuesta, lo convierte a texto plano (strip HTML) y aplica expresiones regulares:

| Patrón (regex) | Etiqueta |
|----------------|----------|
| `contestar.*?(\d+)\s*día` | `{N}_day(s)` |
| `reply.*?in\s+(\d+)\s*day` | `{N}_day(s)` |
| `al\s+final\s+del\s+d[ií]a` | `end_of_day` |
| `end\s+of\s+(the\s+)?day` | `end_of_day` |
| `mañana\|tomorrow` | `tomorrow` |

---

## Motor de recordatorios

### Lógica de `effective_reminder_at`

```python
@property
def effective_reminder_at(self):
    return self.custom_reminder_at or self.reminder_at
```

Un recordatorio está vencido cuando:
```python
effective_reminder_at <= datetime.utcnow()
AND status in ("pending", "snoozed")
AND replied_at IS NULL
```

### Plantilla de recordatorio

El email de recordatorio se envía como respuesta a la conversación original con asunto `Re: {asunto original}` y cuerpo:

```
Hola {nombre},

Te escribí hace {N} horas sobre "{asunto}" y aún no he recibido respuesta.
¿Podrías echarle un vistazo cuando tengas un momento?

Gracias,
[Buzón del agente]
```

---

## Seguridad y cifrado

### Cifrado de credenciales

Las credenciales de Azure AD (especialmente `client_secret`) se almacenan **cifradas** en SQLite usando **Fernet** (AES-128-CBC + HMAC-SHA256).

- `FERNET_KEY` se genera automáticamente al arrancar si no está en `.env`
- Se guarda en el entorno del proceso (no persiste entre reinicios si no se configura)
- **Importante:** Si se pierde `FERNET_KEY`, las credenciales almacenadas quedan inutilizables

### Flask Secret Key

`SECRET_KEY` protege las sesiones de Flask. Debe ser larga y aleatoria en producción.

### Sin exposición de secretos

Los endpoints de la API nunca devuelven `client_secret_enc` ni ningún campo cifrado en las respuestas JSON.

---

## Frontend

### Páginas

| Ruta | Plantilla | Descripción |
|------|-----------|-------------|
| `/setup` | `setup.html` | Wizard 3 pasos: credenciales → test → guardar |
| `/categories` | `categories.html` | Tabla CRUD de categorías con modal |
| `/dashboard` | `dashboard.html` | Stats + recordatorios pendientes + timeline |

### Auto-refresh del dashboard

El dashboard hace polling a `/api/dashboard/stats` cada 30 segundos para mantener los datos actualizados sin recargar la página.

### Arquitectura JS

Cada template tiene su lógica JS embebida (`<script>` al final del bloque `{% block content %}`). `static/js/app.js` contiene solo utilidades compartidas:
- `formatDate(iso)` — fecha legible
- `timeAgo(iso)` — "hace 3 horas"
- `showToast(message, type)` — notificaciones Bootstrap
- `apiCall(url, method, body)` — wrapper Fetch con manejo de errores

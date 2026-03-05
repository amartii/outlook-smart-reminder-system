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

**Outlook Smart Reminder System** es una herramienta web interna para Accenture que automatiza el seguimiento de emails enviados a través de Outlook / Office 365. El agente se conecta directamente a la cuenta de correo del usuario mediante SMTP/IMAP y gestiona todo el ciclo de vida de un email:

```
Usuario envía email
       │
       ▼
SentEmail guardado en DB
(reminder_at = sent_at + horas_categoría)
       │
       ▼
Scheduler check_responses (cada 15 min) — IMAP
       ├─ ¿Hay respuesta? → status = "replied"
       └─ ¿Etiqueta en respuesta? → reprogramar custom_reminder_at
       │
       ▼
Scheduler send_reminders (cada 1h) — SMTP
       └─ SentEmail vencido sin respuesta → enviar recordatorio
```

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────┐
│                    Flask Application                      │
│                                                           │
│  ┌──────────┐    ┌─────────────┐    ┌─────────────────┐  │
│  │ routes.py│───►│ SMTPService │───►│ Outlook / O365  │  │
│  │ (HTTP)   │    │ (SMTP/IMAP) │    │ smtp.office365  │  │
│  └──────────┘    └─────────────┘    │ outlook.office  │  │
│       │                │            └─────────────────┘  │
│       ▼                ▼                                  │
│  ┌──────────┐   ┌───────────────┐                        │
│  │ models.py│   │CategoryManager│                        │
│  │ SQLite   │   │ReminderEngine │                        │
│  └──────────┘   └───────────────┘                        │
│       │                │                                  │
│       └────────────────┴──► APScheduler (3 jobs)         │
└──────────────────────────────────────────────────────────┘
```

**Patrón:** Application Factory (`create_app()`), Blueprint `main`, servicios como clases Python sin estado en Flask.

---

## Tecnologías utilizadas

### Backend

| Tecnología | Versión | Rol |
|------------|---------|-----|
| **Python** | 3.10+ | Lenguaje base |
| **Flask** | 3.x | Framework web |
| **SQLAlchemy** | 2.x | ORM |
| **Flask-Migrate** | 4.x | Migraciones de base de datos |
| **APScheduler** | 3.x | Jobs periódicos en background |
| **smtplib** | stdlib | Envío de emails (SMTP) |
| **imaplib** | stdlib | Lectura y detección de respuestas (IMAP) |
| **cryptography (Fernet)** | 41+ | Cifrado AES de contraseñas |
| **python-dateutil** | 2.8+ | Cálculo y parsing de fechas |

> No se requieren SDKs externos de Microsoft, ni Azure, ni OAuth.
> Funciona con cualquier cuenta de Outlook / Office 365 mediante SMTP/IMAP estándar.

### Base de datos

- **SQLite** local (`instance/agent.db`)
- Compatible con PostgreSQL cambiando `DATABASE_URL` en `.env`

### Servidores de correo soportados

| Proveedor | SMTP | Puerto | IMAP | Puerto |
|-----------|------|--------|------|--------|
| Outlook / Office 365 | smtp.office365.com | 587 | outlook.office365.com | 993 |
| Gmail | smtp.gmail.com | 587 | imap.gmail.com | 993 |
| Outlook.com personal | smtp.office365.com | 587 | outlook.office365.com | 993 |

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
- Bordes: 0px border-radius (sharp)

---

## Modelos de datos

### `OutlookConnection`

Almacena las credenciales de la cuenta de correo que usa el agente.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `backend_type` | String | `"smtp"` (único soportado actualmente) |
| `user_email` | String | Dirección de correo del agente |
| `display_name` | String | Nombre visible |
| `password_enc` | Text | Contraseña **cifrada con Fernet** |
| `smtp_host` | String | Servidor SMTP (default: `smtp.office365.com`) |
| `smtp_port` | Integer | Puerto SMTP (default: `587`) |
| `imap_host` | String | Servidor IMAP (default: `outlook.office365.com`) |
| `imap_port` | Integer | Puerto IMAP (default: `993`) |
| `is_active` | Boolean | Si es la conexión activa |
| `created_at` | DateTime | |

### `CategoryRule`

Define las reglas de categorías: qué etiqueta asignar al contacto y cuántas horas esperar antes de recordar.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | Integer PK | |
| `name` | String UNIQUE | Nombre (ej. "Manager") |
| `color` | String | Preset de color para el UI (`preset0`–`preset14`) |
| `reminder_hours` | Integer | Horas sin respuesta antes del recordatorio |
| `description` | String | Texto libre |

**Categorías creadas automáticamente al conectar:**

| Nombre | Color | Recordatorio |
|--------|-------|-------------|
| Blue | `preset4` (azul) | 24h |
| Manager | `preset3` (verde) | 48h |
| Senior Manager | `preset2` (amarillo) | 72h |
| VIP | `preset1` (naranja) | 96h |

### `Contact`

Contacto añadido manualmente o importado.

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
| `message_id` | String | `Message-ID` SMTP para threading |
| `conversation_id` | String | Igual que `message_id` en modo SMTP |
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

### `SMTPService` (`app/smtp_service.py`)

Servicio principal de email. Usa `smtplib` e `imaplib` de la librería estándar de Python. No requiere SDKs externos.

```python
svc = SMTPService(
    smtp_host="smtp.office365.com", smtp_port=587,
    imap_host="outlook.office365.com", imap_port=993,
    username="tu@empresa.com", password="contraseña"
)
```

| Método | Descripción |
|--------|-------------|
| `validate_connection()` | Prueba login SMTP. Devuelve `(ok: bool, message: str)` |
| `send_email(to, subject, body_html, body_text, category)` | Envía email vía SMTP. Devuelve `{message_id, conversation_id}` |
| `has_reply(conversation_id, sent_at)` | Busca en IMAP INBOX mensajes con `In-Reply-To` coincidente |
| `detect_response_labels(conversation_id, sent_at)` | Descarga cuerpo de respuestas y aplica regex de etiquetas |
| `sync_contacts()` | Devuelve lista vacía (IMAP no tiene contactos) |
| `ensure_category_exists(name, color)` | No-op en modo SMTP |

**Threading de emails:** Al enviar, se genera un `Message-ID` único. Las respuestas se detectan buscando en IMAP mensajes con header `In-Reply-To: <message_id>`.

### `CategoryManager` (`app/category_manager.py`)

| Método | Descripción |
|--------|-------------|
| `assign_category(contact_id, category_id)` | Asigna categoría en DB |
| `get_reminder_hours(contact_id)` | Horas de recordatorio del contacto (default: 48h) |
| `calculate_reminder_at(sent_at, hours)` | Fecha absoluta del recordatorio |
| `process_response_label(sent_email_id, label)` | Actualiza `custom_reminder_at` según etiqueta |
| `seed_default_categories()` | Crea las 4 categorías por defecto si la tabla está vacía |

### `ReminderEngine` (`app/reminder_engine.py`)

| Método | Descripción |
|--------|-------------|
| `get_pending_reminders()` | `SentEmail` vencidos con `status in (pending, snoozed)` |
| `get_upcoming_reminders(hours_ahead)` | Próximos N horas |
| `send_reminder(sent_email_id, svc)` | Envía recordatorio como email nuevo, crea `Reminder`, actualiza status |
| `snooze(sent_email_id, hours)` | `custom_reminder_at = now + hours`, `status = snoozed` |
| `close(sent_email_id)` | `status = closed` |

---

## API REST

Todas las respuestas son JSON. Errores → `{"error": "mensaje"}` con el código HTTP correspondiente.

### Conexión

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

En modo SMTP, `SMTPService.sync_contacts()` devuelve lista vacía (IMAP no expone contactos). Los contactos se gestionan manualmente desde el dashboard. El job se mantiene para compatibilidad futura.

### `check_responses_job` — cada 15 minutos

Para cada `SentEmail` con `status = "pending"`:
1. `SMTPService.has_reply(message_id, sent_at)` — busca en IMAP INBOX por `In-Reply-To`
2. Si hay respuesta → `status = "replied"`, `replied_at = now`
3. `SMTPService.detect_response_labels(...)` — escanea el cuerpo con regex
4. Si detecta etiqueta → `CategoryManager.process_response_label(...)` reprograma

### `send_reminders_job` — cada 1 hora

Para cada `SentEmail` vencido (`ReminderEngine.get_pending_reminders()`):
1. Envía email de recordatorio via SMTP
2. Crea registro `Reminder` en DB
3. Actualiza `status = reminder_sent`

---

## Sistema de categorías

Las categorías definen cuánto tiempo esperar antes de recordar, según el tipo de contacto.

**Flujo:**
1. Se crea una `CategoryRule` con `nombre` + `color` + `reminder_hours`
2. Se asigna al `Contact`
3. Al enviar email: `reminder_at = sent_at + timedelta(hours=category.reminder_hours)`
4. Si el contacto no tiene categoría: se usa 48h por defecto

---

## Detección de respuestas y etiquetas

### Detección de respuesta (IMAP)

```python
# Busca en INBOX mensajes con In-Reply-To coincidente
_, data = mail.search(None,
    f'SINCE "{since}" HEADER "In-Reply-To" "<{message_id}>"'
)
```

Si no hay resultados, también busca por `References` header como fallback.

### Detección de etiquetas

`detect_response_labels()` descarga el cuerpo del mensaje de respuesta y aplica expresiones regulares:

| Patrón | Etiqueta | Comportamiento |
|--------|---------|----------------|
| `contestar después de N día(s)` | `N_days` | `now + N*24h` |
| `reply in N day(s)` | `N_days` | `now + N*24h` |
| `al final del día` / `end of day` | `end_of_day` | Hoy a las 18:00 |
| `mañana` / `tomorrow` | `tomorrow` | Mañana a las 09:00 |

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

Se envía como un email nuevo (no como reply) con asunto `Re: {asunto original}` y cuerpo personalizado con el nombre del contacto y las horas transcurridas.

---

## Seguridad y cifrado

- La contraseña de Outlook se cifra con **Fernet** (AES-128-CBC + HMAC-SHA256) antes de guardarse en SQLite
- `FERNET_KEY` se genera automáticamente al arrancar si no está en `.env`. Guárdalo si quieres que las credenciales persistan entre reinicios
- Las credenciales nunca aparecen en logs ni en respuestas de API
- Todo corre en local — no hay comunicación con servicios externos más allá del servidor SMTP/IMAP de tu proveedor de correo

---

## Frontend

### Páginas

| Ruta | Plantilla | Descripción |
|------|-----------|-------------|
| `/setup` | `setup.html` | Formulario: email + contraseña de Outlook. Hosts pre-rellenados para Office 365. Sección "avanzado" para cambiar SMTP/IMAP |
| `/categories` | `categories.html` | Tabla CRUD de categorías con modal |
| `/dashboard` | `dashboard.html` | Stats + recordatorios pendientes + timeline de actividad |

### Auto-refresh del dashboard

El dashboard hace polling a `/api/dashboard/stats` cada 30 segundos para mantener los datos actualizados.

### Arquitectura JS

Cada template incluye su lógica JS. `static/js/app.js` solo contiene utilidades compartidas:
- `formatDate(iso)` — fecha legible en español
- `timeAgo(iso)` — "hace 3 horas"
- `showToast(message, type)` — notificaciones Bootstrap
- `apiCall(url, method, body)` — wrapper Fetch

---

## Estructura del proyecto

```
outlook-smart-reminder-system/
├── app/
│   ├── __init__.py           # Factory pattern, extensiones Flask
│   ├── models.py             # Modelos SQLAlchemy
│   ├── routes.py             # Endpoints HTTP (páginas + API REST)
│   ├── smtp_service.py       # Backend SMTP/IMAP (smtplib + imaplib)
│   ├── category_manager.py   # Lógica de categorías y scheduling
│   ├── reminder_engine.py    # Motor de recordatorios
│   ├── scheduler.py          # APScheduler jobs (3 jobs)
│   ├── crypto.py             # Cifrado Fernet
│   └── templates/
│       ├── base.html         # Layout base Accenture
│       ├── setup.html        # Formulario conexión Outlook
│       ├── categories.html   # CRUD categorías
│       └── dashboard.html    # Dashboard principal
├── static/
│   ├── css/style.css         # Estilos Accenture brand
│   └── js/app.js             # Utilidades JS compartidas
├── requirements.txt
├── config.py
├── run.py
└── .env.example
```

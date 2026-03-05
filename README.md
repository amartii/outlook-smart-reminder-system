# > Outlook Smart Reminder System

**Accenture Internal Tool** — Sistema inteligente de seguimiento y recordatorios de emails basado en Microsoft Graph API.

---

## ¿Qué hace?

- Conecta con **Office 365 / Outlook** vía Microsoft Graph API (sin SMTP ni IMAP)
- Asigna **categorías automáticas** a contactos (Blue, Manager, Senior Manager, VIP)
- Envía **recordatorios automáticos** según tiempo sin respuesta por categoría
- Detecta **etiquetas en respuestas** ("contestar en 2 días", "al final del día") y reprograma
- Dashboard en tiempo real con estadísticas, recordatorios pendientes y actividad

---

## Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                   Flask Application                  │
│                                                      │
│  routes.py ──► OutlookService ──► Microsoft Graph   │
│       │              │                   API         │
│       ▼              ▼                              │
│  SQLite DB    CategoryManager                       │
│  (models.py)  ReminderEngine                        │
│       │              │                              │
│       └──────────────┴──► APScheduler               │
│                           (3 jobs automáticos)       │
└─────────────────────────────────────────────────────┘
```

**Stack:**
- Backend: Python 3.10+ · Flask · SQLAlchemy · APScheduler
- Auth: MSAL (Microsoft Authentication Library) — client credentials flow
- API: Microsoft Graph v1.0
- DB: SQLite (migrable a PostgreSQL)
- Frontend: Bootstrap 5 · Vanilla JS

---

## Modelos de datos

| Modelo | Descripción |
|--------|-------------|
| `OutlookConnection` | Credenciales Azure AD cifradas (Fernet) |
| `CategoryRule` | Nombre, color Outlook, horas de recordatorio |
| `Contact` | Contacto sincronizado desde Outlook/manual |
| `SentEmail` | Email enviado con tracking de respuesta y recordatorio |
| `Reminder` | Log de cada recordatorio enviado |

---

## Requisitos previos

- Python 3.10+
- Cuenta de **Office 365 / Microsoft 365** con permisos de admin
- Aplicación registrada en **Azure Active Directory** (ver configuración abajo)

---

## Configuración de Azure AD

### 1. Registrar la aplicación

1. Ir a [https://portal.azure.com](https://portal.azure.com)
2. **Azure Active Directory** → **App registrations** → **New registration**
   - Name: `Outlook Smart Reminder`
   - Supported account types: *Accounts in this organizational directory only*
   - Redirect URI: dejar vacío
3. Click **Register**

### 2. Obtener credenciales

- Copiar **Application (client) ID** → `OUTLOOK_CLIENT_ID`
- Copiar **Directory (tenant) ID** → `OUTLOOK_TENANT_ID`

### 3. Crear Client Secret

1. **Certificates & secrets** → **New client secret**
2. Description: `Outlook Agent Secret` · Expires: 24 months
3. Copiar el **Value** → `OUTLOOK_CLIENT_SECRET` *(solo visible una vez)*

### 4. Configurar permisos de API

1. **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**
2. Añadir:
   - `Mail.Send`
   - `Mail.Read`
   - `Contacts.Read`
   - `User.Read.All`
3. Click **"Grant admin consent for [Organization]"**

---

## Instalación y despliegue

### Clonar y preparar entorno

```bash
git clone https://github.com/amartii/outlook-smart-reminder-system.git
cd outlook-smart-reminder-system

python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env`:

```env
SECRET_KEY=tu-clave-secreta-muy-larga
FERNET_KEY=                   # se genera automáticamente si está vacío
DATABASE_URL=sqlite:///agent.db

OUTLOOK_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
OUTLOOK_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
OUTLOOK_CLIENT_SECRET=tu-client-secret
GRAPH_API_ENDPOINT=https://graph.microsoft.com/v1.0
```

> **Nota:** `FERNET_KEY` se genera automáticamente en el primer arranque si no se especifica. Guárdalo para no perder credenciales cifradas.

### Inicializar la base de datos

```bash
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
```

### Arrancar la aplicación

```bash
# Desarrollo
python run.py

# Producción (Windows)
start.bat

# Producción (Linux/Mac con gunicorn)
gunicorn -w 2 -b 0.0.0.0:5000 "app:create_app()"
```

La aplicación estará disponible en `http://localhost:5000`

---

## Flujo de configuración inicial

1. Abrir `http://localhost:5000` → redirige a `/setup`
2. **Paso 1:** Introducir credenciales Azure AD (Tenant ID, Client ID, Client Secret, email de buzón)
3. **Paso 2:** Click "Test Connection" para validar → si es OK, "Guardar Conexión"
4. **Paso 3:** La app crea automáticamente 4 categorías por defecto:
   - `Blue` — recordatorio a las 24h
   - `Manager` — recordatorio a las 48h
   - `Senior Manager` — recordatorio a las 72h
   - `VIP` — recordatorio a las 96h

---

## Uso

### Categorías (`/categories`)
- Crear/editar/eliminar reglas de categoría
- Definir horas de recordatorio por tipo de contacto
- Sincroniza automáticamente con categorías de Outlook

### Dashboard (`/dashboard`)
- Ver estadísticas en tiempo real (emails enviados, respondidos, pendientes)
- Gestionar recordatorios vencidos: Enviar ahora / Posponer / Cerrar
- Timeline de actividad reciente

### API REST

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/outlook/test` | Probar credenciales Azure AD |
| POST | `/api/outlook/connect` | Guardar conexión |
| GET | `/api/categories` | Listar categorías |
| POST | `/api/categories` | Crear categoría |
| GET | `/api/contacts` | Listar contactos |
| POST | `/api/contacts/sync` | Sincronizar desde Outlook |
| POST | `/api/emails/send` | Enviar email |
| GET | `/api/reminders/pending` | Recordatorios vencidos |
| POST | `/api/reminders/{id}/send-now` | Enviar recordatorio ahora |
| POST | `/api/reminders/{id}/snooze` | Posponer N horas |
| GET | `/api/dashboard/stats` | Estadísticas completas |

---

## Scheduler (jobs automáticos)

| Job | Frecuencia | Descripción |
|-----|-----------|-------------|
| `sync_contacts` | Cada 6h | Sincroniza contactos de Outlook |
| `check_responses` | Cada 15min | Detecta respuestas y etiquetas |
| `send_reminders` | Cada 1h | Envía recordatorios vencidos |

### Etiquetas de respuesta detectadas

Cuando un contacto responde con estas frases, el sistema reprograma el recordatorio:

| Frase en el email | Comportamiento |
|-------------------|----------------|
| "contestar después de 1 día" | Reprograma en 24h |
| "contestar después de 2 días" | Reprograma en 48h |
| "al final del día" | Reprograma para las 18:00 |
| "mañana" | Reprograma para mañana 09:00 |

---

## Estructura del proyecto

```
outlook-smart-reminder-system/
├── app/
│   ├── __init__.py          # Factory pattern, extensiones Flask
│   ├── models.py            # Modelos SQLAlchemy
│   ├── routes.py            # Endpoints HTTP
│   ├── outlook_service.py   # Wrapper Microsoft Graph API
│   ├── category_manager.py  # Lógica de categorías y scheduling
│   ├── reminder_engine.py   # Motor de recordatorios
│   ├── scheduler.py         # APScheduler jobs
│   ├── crypto.py            # Cifrado Fernet
│   └── templates/
│       ├── base.html        # Layout base Accenture
│       ├── setup.html       # Wizard configuración Azure AD
│       ├── categories.html  # CRUD categorías
│       └── dashboard.html   # Dashboard principal
├── static/
│   ├── css/style.css        # Estilos Accenture brand
│   └── js/app.js            # Utilidades JS compartidas
├── requirements.txt
├── config.py
├── run.py
└── .env.example
```

---

## Diseño — Identidad Accenture

- **Color primario:** `#000000` (negro)
- **Acento:** `#A100FF` (morado Accenture)
- **Tipografía:** Inter (Google Fonts)
- **Logo:** símbolo `>` (chevron Accenture)
- **Bordes:** sharp (0px border-radius)

---

## Seguridad

- Credenciales Azure AD cifradas con **Fernet** (AES-128 CBC)
- `FERNET_KEY` generado automáticamente si no se configura
- Secretos nunca en logs ni en respuestas de API
- `SECRET_KEY` Flask configurable por entorno

---

## Licencia

Uso interno Accenture. No distribuir.

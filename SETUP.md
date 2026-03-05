# Guía de instalación — Outlook Smart Reminder System

> **Tiempo estimado: 10 minutos** (5 min instalación + 5 min registro de la app Microsoft)

---

## Requisitos previos

- **Python 3.10 o superior** — [descargar aquí](https://www.python.org/downloads/)
- **Git** — [descargar aquí](https://git-scm.com/)
- Una cuenta **Microsoft / Outlook** (corporativa o personal `@outlook.com`)
- O una cuenta **Gmail** con 2FA activado (para la alternativa Gmail)

---

## Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/amartii/outlook-smart-reminder-system.git
cd outlook-smart-reminder-system
```

---

## Paso 2 — Crear el entorno virtual e instalar dependencias

### Windows
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Paso 3 — Arrancar la aplicación

```bash
python run.py
```

Abre el navegador en **[http://localhost:5000](http://localhost:5000)**

La base de datos SQLite se crea automáticamente en `instance/agent.db`.

---

## Paso 4A — Conectar Outlook / Office 365 (recomendado)

Microsoft eliminó la autenticación por contraseña para SMTP/IMAP en 2022.
La única forma oficial es OAuth2. El proceso de registro es **gratuito** y tarda ~5 minutos.

### 4A.1 — Registrar la aplicación en Azure Portal (gratis)

> Puedes hacerlo con **cualquier cuenta Microsoft**, incluso una personal `@outlook.com`.

1. Ve a **[portal.azure.com](https://portal.azure.com)** e inicia sesión.
2. Busca y abre **"App registrations"** (registro de aplicaciones).
3. Click **"New registration"**:
   - **Name**: `Outlook Smart Reminder`
   - **Supported account types**: selecciona  
     `"Accounts in any organizational directory ... and personal Microsoft accounts"`
   - **Redirect URI**: déjalo vacío
   - Click **Register**
4. En la pantalla de la app, copia el **Application (client) ID** — lo necesitarás en el Paso 4A.2.
5. Ve a **"API permissions"** → **"Add a permission"** → **Microsoft Graph** → **Delegated permissions**.  
   Añade estos permisos:
   - `Mail.Send`
   - `Mail.ReadWrite`
   - `Contacts.Read`
   - `User.Read`
   - `offline_access`
6. Ve a **"Authentication"** → busca la sección **"Advanced settings"** →  
   activa **"Allow public client flows"** → click **Save**.

### 4A.2 — Vincular la cuenta desde la app

1. Abre la app en [http://localhost:5000/setup](http://localhost:5000/setup)
2. Selecciona la pestaña **"Microsoft Outlook"**
3. Pega el **Client ID** del paso anterior
4. Click **"Iniciar sesión con Microsoft"**
5. La app mostrará un código de 8 letras y un enlace:  
   ve a **[https://microsoft.com/devicelogin](https://microsoft.com/devicelogin)**,  
   introduce el código y acepta los permisos.
6. La app detecta automáticamente cuando completas el login y te redirige al dashboard.

---

## Paso 4B — Conectar Gmail (alternativa)

Gmail requiere una **App Password** (contraseña de aplicación). Funciona con cuentas Google
que tengan la verificación en dos pasos activada.

1. Ve a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Selecciona "Correo" + "Windows" → **Generar**
3. Copia el código de 16 caracteres (sin espacios)
4. En la app, ve a [/setup](http://localhost:5000/setup) → pestaña **"Gmail / otro"**
5. Introduce tu email de Gmail y pega el App Password
6. Click **"Guardar y conectar"**

---

## Paso 5 — Primeros pasos en el dashboard

Una vez conectado:

1. **Categorías** (`/categories`) — las categorías por defecto ya están creadas:

   | Categoría | Horas sin respuesta → recordatorio |
   |-----------|-------------------------------------|
   | Blue | 24 h |
   | Manager | 48 h |
   | Senior Manager | 72 h |
   | VIP | 96 h |

   Puedes editarlas o añadir las tuyas.

2. **Añadir contactos** — desde el dashboard, botón **"+ Contacto"**, asigna una categoría.

3. **Enviar un email** — botón **"Nuevo Email"**, selecciona contacto, escribe asunto y cuerpo.

4. El agente revisa respuestas cada **15 minutos** y envía recordatorios cada **1 hora**.

---

## Detección de etiquetas en respuestas

Si el destinatario responde incluyendo frases como:

| Frase en el email | Comportamiento |
|-------------------|----------------|
| `contestar después de 1 día` | Pospone el recordatorio 1 día |
| `contestar después de 2 días` | Pospone el recordatorio 2 días |
| `al final del día` | Recordatorio a las 18:00 del mismo día |
| `mañana` / `tomorrow` | Recordatorio al día siguiente |

El sistema reprograma automáticamente el recordatorio sin intervención manual.

---

## Variables de entorno (opcional)

Copia el archivo de ejemplo y edita la clave secreta:

```bash
cp .env.example .env
```

```env
SECRET_KEY=una-clave-larga-y-aleatoria-aqui
```

Las credenciales de Outlook/Gmail **no** van en `.env` — se introducen desde la interfaz web
y se almacenan cifradas en la base de datos local.

---

## Preguntas frecuentes

**¿Por qué no funciona con usuario y contraseña de Outlook directamente?**  
Microsoft desactivó la autenticación básica SMTP/IMAP en octubre de 2022. Es obligatorio usar OAuth2.

**¿Se envían mis datos a algún servidor externo?**  
No. El agente corre en local. Solo se comunica con `login.microsoftonline.com` (para la autenticación)
y `graph.microsoft.com` (para enviar/leer emails). No hay ningún backend intermedio.

**¿Qué pasa si el servidor se reinicia?**  
El refresh token de Microsoft se guarda cifrado en la base de datos local. No necesitas volver a hacer login.

**¿El Client ID es una contraseña?**  
No, es un identificador público. Lo que protege tu cuenta es el token OAuth que Microsoft emite,
que solo tú puedes autorizar desde tu sesión de Microsoft.

# Guía de instalación — Outlook Smart Reminder System

> Tiempo estimado de instalación: **5 minutos**

---

## Requisitos previos

- **Python 3.10 o superior** — [descargar aquí](https://www.python.org/downloads/)
- **Git** — [descargar aquí](https://git-scm.com/)
- Una cuenta de **Outlook / Office 365** activa

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

El prompt debería mostrar `(venv)` cuando esté activo.

---

## Paso 3 — Arrancar la aplicación

```bash
python run.py
```

Abre el navegador en **[http://localhost:5000](http://localhost:5000)**

La base de datos SQLite se crea automáticamente en `instance/agent.db`.

---

## Paso 4 — Conectar tu cuenta de Outlook

Al abrir la app por primera vez verás el formulario de configuración.

1. **Email** — introduce tu correo corporativo (`tunombre@empresa.com`)
2. **Contraseña** — tu contraseña de Outlook
3. Click **"Probar conexión"** para verificar que funciona
4. Click **"Guardar y conectar"** — el agente queda listo y te lleva al dashboard

Los servidores SMTP/IMAP de Office 365 ya están preconfigurados. Si usas otro proveedor,
expande **"Configuración avanzada"** en el formulario.

---

## Verificación en dos pasos (MFA)

Si tu cuenta tiene la verificación en dos pasos activada, tu contraseña normal **no funcionará** por SMTP. Necesitas generar una **contraseña de aplicación**:

### Outlook / Office 365

1. Ir a [account.microsoft.com/security](https://account.microsoft.com/security)
2. Buscar **"Contraseñas de aplicación"** (o *App passwords*)
3. Crear una nueva → copiar el código de 16 caracteres
4. Usar ese código como contraseña en el formulario del agente

### Gmail

1. Ir a [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Seleccionar "Correo" + "Otro (nombre personalizado)"
3. Generar → copiar el código de 16 caracteres

---

## Servidores por proveedor

Los campos de la sección "Configuración avanzada" del formulario:

| Proveedor | SMTP Host | Puerto | IMAP Host | Puerto |
|-----------|-----------|--------|-----------|--------|
| **Outlook / Office 365** | smtp.office365.com | 587 | outlook.office365.com | 993 |
| **Gmail** | smtp.gmail.com | 587 | imap.gmail.com | 993 |
| **Outlook.com personal** | smtp.office365.com | 587 | outlook.office365.com | 993 |
| **Yahoo Mail** | smtp.mail.yahoo.com | 587 | imap.mail.yahoo.com | 993 |

---

## Primeros pasos en el dashboard

Una vez conectado:

1. **Categorías** (`/categories`) — las 4 categorías por defecto ya están creadas:

   | Categoría | Horas sin respuesta para recordar |
   |-----------|----------------------------------|
   | Blue | 24h |
   | Manager | 48h |
   | Senior Manager | 72h |
   | VIP | 96h |

   Puedes editarlas o crear las tuyas.

2. **Añadir un contacto** — en el dashboard, botón **"+ Contacto"**, asigna una categoría.

3. **Enviar un email** — botón **"Nuevo Email"**, selecciona contacto, escribe asunto y cuerpo.

4. El agente monitoriza la bandeja de entrada cada 15 minutos. Si no hay respuesta en el
   tiempo de la categoría, envía un recordatorio automáticamente.

---

## Problema: autenticación rechazada en cuentas corporativas

Algunas organizaciones tienen desactivado el acceso SMTP/IMAP básico por política.
Si ves un error de autenticación aunque la contraseña sea correcta, solicita a tu
equipo de IT que habilite **SMTP AUTH** para tu buzón:

```
"Por favor, activa SMTP AUTH para mi cuenta en Exchange Online."
```

Comando PowerShell para el administrador de Exchange:

```powershell
Set-CASMailbox -Identity "tunombre@empresa.com" -SmtpClientAuthenticationDisabled $false
```

---

## Variables de entorno (opcional)

Si quieres configurar una `SECRET_KEY` personalizada, copia el archivo de ejemplo:

```bash
cp .env.example .env
```

Y edita `.env`:

```env
SECRET_KEY=una-clave-larga-y-aleatoria-aqui
```

Las credenciales de Outlook **no** van en `.env` — se introducen desde la interfaz web
y se guardan cifradas en la base de datos local.

---

## Solución de problemas

| Error | Causa probable | Solución |
|-------|---------------|----------|
| `SMTPAuthenticationError` | Contraseña incorrecta o MFA activo | Usar App Password |
| `[AUTHENTICATIONFAILED]` | SMTP AUTH desactivado por IT | Pedir a IT que lo habilite |
| `Connection refused` | Host o puerto incorrecto | Revisar "Configuración avanzada" |
| `No module named 'app'` | Entorno virtual no activo | Ejecutar `venv\Scripts\activate` |
| La DB no se crea | No existe la carpeta `instance/` | Se crea automáticamente al arrancar |

---

## Seguridad

- La contraseña se cifra con **Fernet (AES-128)** antes de guardarse en `instance/agent.db`
- Nada sale a Internet salvo los emails enviados a través de tu servidor SMTP
- El archivo `.env` y `instance/agent.db` están en `.gitignore` — no se suben al repositorio

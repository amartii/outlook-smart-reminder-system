# Guía de instalación — Outlook Smart Reminder System

---

## Requisitos previos

- **Python 3.10 o superior** — [descargar](https://www.python.org/downloads/)
- **Git** — [descargar](https://git-scm.com/)
- Una cuenta de **Outlook / Office 365** activa

---

## Paso 1 — Clonar el repositorio

```bash
git clone https://github.com/amartii/outlook-smart-reminder-system.git
cd outlook-smart-reminder-system
```

---

## Paso 2 — Crear el entorno virtual

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

El prompt debería mostrar `(venv)` cuando esté activo.

---

## Paso 3 — Instalar dependencias

```bash
pip install -r requirements.txt
```

---

## Paso 4 — Arrancar la aplicación

```bash
python run.py
```

Abre el navegador en **http://localhost:5000**

---

## Paso 5 — Conectar tu cuenta de Outlook

Al abrir la app por primera vez se muestra el formulario de configuración.

1. **Email** — introduce tu correo corporativo de Outlook (ej. `tunombre@empresa.com`)
2. **Contraseña** — tu contraseña habitual de Outlook

   > ⚠️ Si tu cuenta tiene **verificación en dos pasos activa**, necesitas generar una
   > **App Password** (contraseña de aplicación) en lugar de tu contraseña normal:
   > 1. Ir a [account.microsoft.com/security](https://account.microsoft.com/security)
   > 2. **Seguridad avanzada** → **Contraseñas de aplicación** → Crear nueva
   > 3. Usar ese código de 16 caracteres como contraseña aquí

3. Click **"Probar conexión"** — verás un mensaje de éxito si las credenciales son correctas
4. Click **"Guardar y conectar"** — el agente queda configurado y te lleva al dashboard

Los servidores SMTP/IMAP de Office 365 ya están preconfigurados. Si usas **Gmail** o
cualquier otro proveedor, expande "Configuración avanzada" y cámbialo.

---

## Servidores por proveedor

| Proveedor | SMTP | Puerto | IMAP | Puerto |
|-----------|------|--------|------|--------|
| **Outlook / Office 365** | smtp.office365.com | 587 | outlook.office365.com | 993 |
| **Gmail** | smtp.gmail.com | 587 | imap.gmail.com | 993 |
| **Outlook.com personal** | smtp.office365.com | 587 | outlook.office365.com | 993 |

### Gmail — pasos adicionales

Gmail requiere una **App Password** (tu contraseña normal no funciona):
1. Ir a [myaccount.google.com/security](https://myaccount.google.com/security)
2. Activar verificación en dos pasos si no está activa
3. **Contraseñas de aplicaciones** → Seleccionar "Correo" + "Otro" → Generar
4. Usar el código de 16 caracteres como contraseña en el formulario

---

## Paso 6 — Primeros pasos en el dashboard

Una vez conectado:

1. Ir a **Categorías** — las 4 categorías por defecto ya están creadas:
   - **Blue** — recordatorio a las 24h
   - **Manager** — recordatorio a las 48h
   - **Senior Manager** — recordatorio a las 72h
   - **VIP** — recordatorio a las 96h
   
   Puedes editarlas o crear las tuyas propias.

2. Añadir contactos manualmente con el botón **"+ Contacto"** en el dashboard

3. Enviar un email con **"Nuevo Email"** — selecciona el contacto, escribe asunto y cuerpo

4. El agente monitoriza automáticamente la conversación. Si no hay respuesta en el tiempo
   configurado para la categoría del contacto, envía un recordatorio automáticamente.

---

## Problema con SMTP AUTH en cuentas corporativas

Algunas organizaciones tienen desactivado el acceso SMTP/IMAP básico por política de
seguridad. Si ves un error de autenticación aunque la contraseña sea correcta, solicita
a tu equipo de IT que **habilite SMTP AUTH** para tu buzón:

> *"Por favor, activa SMTP AUTH para mi cuenta en Exchange Online
> (PowerShell: `Set-CASMailbox -Identity tunombre@empresa.com -SmtpClientAuthenticationDisabled $false`)"*

---

## Solución de problemas

| Error | Solución |
|-------|----------|
| `SMTPAuthenticationError` | Contraseña incorrecta o necesitas App Password |
| `Connection refused` | Verifica los puertos SMTP/IMAP en la configuración avanzada |
| `Authentication failed` | SMTP AUTH desactivado por IT — ver sección anterior |
| `No module named 'app'` | Activa el entorno virtual: `venv\Scripts\activate` |

---

## Notas de seguridad

- La contraseña se **cifra con Fernet** antes de guardarla en la base de datos local
- Las credenciales nunca se envían a ningún servidor externo — todo corre en local
- El archivo `instance/agent.db` contiene los datos — no lo compartas

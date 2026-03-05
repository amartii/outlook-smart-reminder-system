# Outlook Smart Reminder System

> Sistema inteligente de recordatorios para Outlook, construido para ONEtoONE Corporate Finance.  
> Funciona en local — tus datos no salen de tu ordenador.

---

## Índice

1. [¿Qué es y qué hace?](#qué-es-y-qué-hace)
2. [Funcionalidades completas](#funcionalidades-completas)
3. [Requisitos previos](#requisitos-previos)
4. [Instalación](#instalación)
5. [Guía de uso paso a paso](#guía-de-uso-paso-a-paso)
6. [Variables de personalización](#variables-de-personalización)
7. [Dashboard explicado](#dashboard-explicado)
8. [Deduplicación entre campañas](#deduplicación-entre-campañas)
9. [Sistema de follow-up automático](#sistema-de-follow-up-automático)
10. [El Excel se actualiza solo](#el-excel-se-actualiza-solo)
11. [Seguridad y privacidad](#seguridad-y-privacidad)
12. [Límites de Gmail](#límites-de-gmail)
13. [Solución de problemas](#solución-de-problemas)
14. [Preguntas frecuentes](#preguntas-frecuentes)

---

## ¿Qué es y qué hace?

**Email Agent** es una aplicación web local que automatiza el envío de campañas de email personalizadas desde tu propia cuenta de Gmail, sin intermediarios, sin cuotas mensuales y sin que tus datos salgan de tu ordenador.

### Flujo completo de una campaña

```
Excel con contactos
        ↓
 Subir a la app  →  Detecta columnas automáticamente
        ↓
Configurar campaña  →  Asunto, cuerpo HTML, follow-up, días de espera
        ↓
  Lanzar  →  Envía emails personalizados uno a uno
        ↓
Detección de respuestas  →  Comprueba el buzón IMAP cada 30 min
        ↓
Follow-up automático  →  Reenvío a los que no contestaron tras X días
        ↓
Excel actualizado  →  Estado, fecha envío, fecha respuesta, follow-up
```

---

## Funcionalidades completas

### 📂 Gestión del Excel

| Funcionalidad | Descripción |
|---|---|
| **Lectura automática de columnas** | Al subir el Excel, detecta todas las columnas disponibles |
| **Mapeo manual de columnas** | El usuario elige qué columna es "Nombre" y cuál es "Email" |
| **Drag & drop** | Arrastra el fichero directamente a la zona de carga |
| **Auto-selección inteligente** | Detecta y preselecciona automáticamente columnas llamadas "nombre", "email", "correo", etc. |
| **Actualización automática** | Al enviar cada email, el Excel se actualiza con el estado en tiempo real |
| **Columnas gestionadas** | Añade automáticamente: `Estado`, `Fecha Envío`, `Fecha Respuesta`, `Follow-up Enviado` |
| **Formatos soportados** | `.xlsx` y `.xls` |

---

### ✉️ Envío de emails

| Funcionalidad | Descripción |
|---|---|
| **Personalización por contacto** | Cualquier columna del Excel se puede usar como variable en el email |
| **Doble formato** | Envía simultáneamente HTML (con formato) y texto plano (fallback) |
| **Gmail SMTP con SSL** | Conexión cifrada mediante SMTP SSL al puerto 465 de Gmail |
| **App Password segura** | No usa tu contraseña de Gmail; usa una contraseña de aplicación de 16 dígitos |
| **Prueba de credenciales** | Botón "Probar conexión" antes de lanzar para verificar que el Gmail funciona |
| **Pausa entre envíos** | 1 segundo entre emails para no saturar el servidor y evitar spam |
| **Message-ID almacenado** | Guarda el ID único de cada email para detectar respuestas correctamente |
| **Detección de errores por contacto** | Si un email falla, se registra el error específico y continúa con los demás |
| **Error de autenticación** | Si la App Password es incorrecta, detiene la campaña y muestra el error claramente |

---

### 📥 Detección de respuestas

| Funcionalidad | Descripción |
|---|---|
| **Conexión IMAP a Gmail** | Se conecta al buzón del remitente para leer las respuestas |
| **Detección por cabeceras** | Usa `In-Reply-To` y `References` del email para identificar respuestas exactas |
| **Comprobación periódica** | El scheduler revisa el buzón cada 30 minutos automáticamente |
| **Registro de fecha** | Guarda la fecha y hora exacta en que se detectó la respuesta |
| **Actualización del Excel** | Marca al contacto como "Respondido" y rellena la columna `Fecha Respuesta` |
| **Sin dobles marcas** | Una vez marcado como respondido, no se le enviará follow-up |

---

### 🔄 Follow-up automático

| Funcionalidad | Descripción |
|---|---|
| **Días configurables** | El usuario define cuántos días esperar antes del follow-up (por defecto: 3) |
| **Solo a no respondidos** | Únicamente envía el follow-up a quienes no han contestado el email original |
| **Plantilla independiente** | El follow-up tiene su propio asunto, cuerpo HTML y texto plano |
| **Personalización igual** | Funciona con las mismas variables `{{Nombre}}`, `{{Empresa}}`, etc. |
| **Registro en Excel** | Marca la columna `Follow-up Enviado` con la fecha correspondiente |
| **Un solo follow-up** | No reenvía repetidamente; solo una vez pasados los días configurados |

---

### 🚦 Deduplicación entre campañas

| Funcionalidad | Descripción |
|---|---|
| **Historial global** | Registra todos los emails a los que se ha enviado correo en cualquier campaña |
| **Filtro automático** | Al lanzar una nueva campaña, omite contactos que ya recibieron un email |
| **Criterio de omisión** | Se omiten los que tienen estado: `enviado`, `respondido` o `follow-up enviado` |
| **Transparencia** | El mensaje de lanzamiento indica cuántos contactos se han omitido y por qué |
| **Solo nuevos** | Perfecta para añadir contactos a un Excel existente y relanzar sin duplicados |

**Ejemplo:** Si tu Excel tiene 100 contactos y 80 ya recibieron email en la campaña anterior, al relanzar solo se enviará a los 20 nuevos. El mensaje dirá: *"Enviando emails a 20 contactos. (80 omitidos por ya haber recibido email anteriormente.)"*

---

### 📊 Dashboard en tiempo real

| Funcionalidad | Descripción |
|---|---|
| **4 contadores** | Total, Enviados, Respondidos, Sin respuesta |
| **Tabla de contactos** | Lista completa con nombre, email, estado, fechas y errores |
| **Reloj en tiempo real** | El indicador de estado actualiza los segundos en directo (cada 1 segundo) |
| **Actualización automática** | Los datos se recargan del servidor cada 30 segundos sin acción del usuario |
| **Botón Pausar/Reanudar** | Para el envío en curso y lo reanuda cuando se necesite |
| **Banner de error** | Si falla la autenticación de Gmail, aparece un aviso visible con instrucciones |
| **Columna de error** | Muestra el error específico si un email concreto no pudo enviarse |
| **Botón Nueva campaña** | Archiva la campaña actual y permite comenzar una nueva desde cero |

---

### 🔐 Seguridad

| Funcionalidad | Descripción |
|---|---|
| **Cifrado de contraseñas** | La App Password se cifra con Fernet (AES-128) antes de guardarse |
| **Almacenamiento local** | Base de datos SQLite en tu máquina; ningún dato se envía a servidores externos |
| **Sin dependencias en la nube** | No usa ningún servicio SaaS externo ni API de terceros |
| **Código abierto** | Puedes revisar el código fuente completo en el repositorio |

---

### 🎨 Interfaz

| Funcionalidad | Descripción |
|---|---|
| **Diseño ONEtoONE CF** | Colores corporativos: navy `#0C2340`, azul `#0056A7`, acento `#1863DC`, fondo crema `#F9F7EE` |
| **Tipografía** | Fraunces (serif elegante) para títulos y cifras + Inter para cuerpo |
| **Responsive** | Funciona en pantallas de escritorio y tablet |
| **Wizard en 3 pasos** | Navegación clara: Excel → Campaña → Dashboard |
| **Indicadores de estado** | Badges de color por estado (azul=enviado, verde=respondido, naranja=follow-up, rojo=error) |

---

## Requisitos previos

### 1. Python 3.9 o superior

1. Descarga desde [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. **IMPORTANTE:** Durante la instalación, marca **"Add Python to PATH"**
3. Verifica: abre `cmd` y ejecuta `python --version`

### 2. Git

1. Descarga desde [https://git-scm.com/download/win](https://git-scm.com/download/win)
2. Instala con las opciones por defecto
3. Verifica: `git --version`

### 3. Gmail con App Password

Google no permite usar tu contraseña normal por API. Necesitas una **Contraseña de Aplicación**:

1. Activa la **verificación en dos pasos** en [https://myaccount.google.com/security](https://myaccount.google.com/security)
2. Ve a [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
3. Escribe un nombre (ej: `Email Agent`) y haz clic en **Crear**
4. Google te dará una contraseña de 16 caracteres tipo: `abcd efgh ijkl mnop`
5. Guárdala, la necesitarás al configurar la campaña

> La App Password solo da permiso de envío de emails. No expone tu contraseña real ni el resto de tu cuenta Google.

---

## Instalación

### Windows (método rápido)

```cmd
:: 1. Descargar el código
git clone https://github.com/amartii/email-agent.git
cd email-agent

:: 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate

:: 3. Instalar dependencias
pip install -r requirements.txt

:: 4. Arrancar la aplicación
python run.py
```

Abre tu navegador en **http://localhost:5000**

### Arranque posterior

Para las próximas veces, simplemente haz **doble clic en `start.bat`** — no necesitas repetir los pasos anteriores.

### Dependencias instaladas automáticamente

| Paquete | Versión | Para qué sirve |
|---|---|---|
| Flask | 3.x | Servidor web local |
| Flask-SQLAlchemy | 3.x | Base de datos SQLite |
| openpyxl | 3.x | Leer y escribir Excel |
| cryptography | 42.x | Cifrar contraseñas |
| APScheduler | 3.x | Tareas automáticas periódicas |
| Bootstrap | 5.3 (CDN) | Interfaz gráfica |

---

## Guía de uso paso a paso

### Paso 1 — Prepara tu Excel

Mínimo necesitas dos columnas: **Nombre** y **Email**. El resto son opcionales pero aprovechables:

| Nombre | Email | Empresa | Cargo | Ciudad |
|---|---|---|---|---|
| Ana García | ana@acme.com | Acme Corp | Directora | Madrid |
| Pedro López | pedro@beta.com | Beta SA | CEO | Barcelona |

> Las columnas adicionales se convierten automáticamente en variables para personalizar el email.

### Paso 2 — Sube el Excel

1. Abre [http://localhost:5000](http://localhost:5000)
2. Arrastra el fichero a la zona de carga o haz clic para seleccionarlo
3. Haz clic en **"Detectar columnas"**
4. Selecciona cuál columna es **Nombre** y cuál es **Email**
5. Haz clic en **"Continuar a configuración"**

### Paso 3 — Configura la campaña

Rellena el formulario en dos secciones:

**Cuenta de envío:**
- Nombre de la campaña (para identificarla en el dashboard)
- Gmail (tu dirección completa)
- App Password (los 16 caracteres de Google, con o sin espacios)
- Días para follow-up (por defecto 3)
- Haz clic en **"Probar conexión"** — debe aparecer un mensaje verde ✅

**Email principal:**
- Asunto: usa variables como `{{Nombre}}` o `{{Empresa}}`
- Cuerpo HTML: el email con formato visual
- Cuerpo texto: versión plana sin etiquetas

**Follow-up:**
- Asunto y cuerpo del recordatorio para no respondidos

Haz clic en **"Guardar y lanzar campaña"** — comenzará el envío inmediatamente.

### Paso 4 — Sigue la campaña en el dashboard

El dashboard muestra en tiempo real:

- Los **4 contadores** se actualizan cada 30 segundos
- La **tabla de contactos** muestra el estado de cada uno
- El **reloj** a la derecha del estado cambia cada segundo
- El **Excel** en tu disco se actualiza a medida que se envían los emails

---

## Variables de personalización

En el asunto y el cuerpo del email puedes usar cualquier columna del Excel con la sintaxis `{{NombreColumna}}`:

```
Asunto:   Hola {{Nombre}}, te escribo sobre tu empresa {{Empresa}}
Cuerpo:   <p>Estimado/a {{Nombre}},</p>
          <p>Como {{Cargo}} de {{Empresa}} en {{Ciudad}}, creo que...</p>
```

### Reglas de las variables

| Regla | Detalle |
|---|---|
| **Case-insensitive** | `{{nombre}}` y `{{Nombre}}` funcionan igual |
| **Cualquier columna** | Cualquier cabecera del Excel es válida como variable |
| **Sin espacios en la variable** | La columna "Fecha Nacimiento" se usa como `{{FechaNacimiento}}` o `{{fecha nacimiento}}` |
| **Fallback vacío** | Si una variable no tiene valor para ese contacto, se deja en blanco (no da error) |

---

## Dashboard explicado

```
┌─────────────────────────────────────────────────────────────┐
│  Campaña Prospección Q1     [En curso ●]   · 22:48:53       │
│                                         [Pausar] [Nueva]    │
├──────────┬──────────┬───────────┬────────────────────────────┤
│    4     │    4     │     0     │      4                     │
│  TOTAL   │ENVIADOS  │RESPONDIDOS│  SIN RESPUESTA             │
├──────────┴──────────┴───────────┴────────────────────────────┤
│ Nombre  │ Email │ Estado  │ Enviado │ Respondido │ Error     │
├─────────┼───────┼─────────┼─────────┼────────────┼───────────┤
│ Carlos  │ c@... │ Enviado │ 24/2 10 │     —      │           │
│ Álvaro  │ a@... │ Enviado │ 24/2 10 │     —      │           │
└─────────────────────────────────────────────────────────────┘
```

### Estados posibles de un contacto

| Estado | Color | Significado |
|---|---|---|
| **Pendiente** | Gris | Todavía no se ha procesado |
| **Enviado** | Azul | Email enviado, esperando respuesta |
| **Respondido** | Verde | El contacto ha contestado al email |
| **Follow-up enviado** | Naranja | Se envió el recordatorio (no respondió en X días) |
| **Rebotado** | Rojo | El email no pudo entregarse (ver columna Error) |

### Botones del dashboard

| Botón | Acción |
|---|---|
| **Pausar** | Detiene el envío en el contacto actual. Los ya enviados se mantienen. |
| **Reanudar** | Continúa el envío desde donde se quedó |
| **Nueva campaña** | Archiva la campaña actual y vuelve al paso 1 para empezar de cero |

---

## Deduplicación entre campañas

Esta funcionalidad evita enviar emails duplicados cuando reutilizas o amplías un Excel.

### Cómo funciona

1. Al lanzar una campaña, el agente consulta el historial de **todas las campañas anteriores**
2. Si un email ya está registrado como `enviado`, `respondido` o `follow-up enviado`, se omite
3. Solo se envía a los contactos **nuevos** que no aparecen en el historial

### Caso de uso típico

```
Campaña 1:  100 contactos → 100 emails enviados
             (a los 3 días: 20 responden, 80 no)

Añades 30 nuevos contactos al Excel → ahora tienes 130

Campaña 2:  El agente omite los 100 anteriores
            Solo envía a los 30 nuevos
            Mensaje: "Enviando a 30 contactos. (100 omitidos por
                      ya haber recibido email anteriormente.)"
```

---

## Sistema de follow-up automático

El scheduler (tarea automática) se ejecuta en segundo plano mientras la app está abierta.

### Secuencia temporal

```
Día 0  →  Se envía el email inicial
Día 0-3  →  El scheduler comprueba respuestas cada 30 minutos
Día 3  →  Si no hay respuesta, envía el follow-up automáticamente
Día 3+  →  El scheduler sigue comprobando respuestas al follow-up
```

### Condiciones para el follow-up

- El contacto tiene estado `enviado` (no `respondido`, `rebotado`, ni `follow-up enviado`)
- Han pasado más de N días desde `Fecha Envío` (N configurable por el usuario)
- La campaña está en estado `en curso` (no pausada)

> **Importante:** La app debe estar abierta/corriendo para que el scheduler funcione. Si la cierras, el follow-up se retrasa hasta que la vuelvas a abrir.

---

## El Excel se actualiza solo

Cada vez que se procesa un contacto, la app escribe directamente en tu fichero Excel:

| Columna | Se rellena cuando... | Ejemplo |
|---|---|---|
| `Estado` | Se envía, responde o hace follow-up | `Enviado` / `Respondido` / `Follow-up enviado` |
| `Fecha Envío` | Se envía el email inicial | `24/02/2026 10:30` |
| `Fecha Respuesta` | Se detecta una respuesta | `24/02/2026 14:15` |
| `Follow-up Enviado` | Se envía el email de seguimiento | `27/02/2026 10:30` |

Estas columnas se añaden automáticamente al final del Excel si no existen. No se eliminan ni modifican las columnas originales.

---

## Seguridad y privacidad

| Aspecto | Implementación |
|---|---|
| **Contraseña de Gmail** | Cifrada con Fernet AES-128 antes de guardar en disco |
| **Clave de cifrado** | Derivada del `SECRET_KEY` local del servidor (no viaja a ningún sitio) |
| **Base de datos** | SQLite local en `instance/agent.db` — solo accesible desde tu máquina |
| **Excel** | Guardado en la carpeta `uploads/` de la aplicación, en tu máquina |
| **Sin telemetría** | Ningún dato de uso, contactos ni credenciales se envía a servidores externos |
| **Código auditables** | 100% open source, puedes revisar cada línea en el repositorio |

> **Recomendación:** No compartas la carpeta `instance/` ni el fichero `agent.db` con nadie.  
> Contiene las contraseñas cifradas y el historial de campañas.

---

## Límites de Gmail

### Cuenta Gmail gratuita (@gmail.com)

| Límite | Valor |
|---|---|
| Emails por día | ~500 |
| Emails por hora | ~100 recomendado |
| Pausa automática entre envíos | 1 segundo |

### Cuenta Google Workspace (empresa)

| Límite | Valor |
|---|---|
| Emails por día | ~2.000 |
| Límite SMTP | Configurado por el administrador |

> Si tu campaña supera 500 contactos, divídela en días o usa una cuenta Workspace.

---

## Solución de problemas

### La app no arranca

```
Error: Python no encontrado
```
→ Asegúrate de haber marcado "Add Python to PATH" durante la instalación. Reinstala Python.

```
ModuleNotFoundError: No module named 'flask'
```
→ Ejecuta `venv\Scripts\activate` antes de `python run.py`.

---

### Error de autenticación de Gmail

```
Error de autenticación Gmail. Comprueba el email y la App Password.
```

Causas habituales:
1. **Contraseña equivocada** — Usa la App Password de 16 caracteres, no tu contraseña habitual
2. **Verificación en dos pasos desactivada** — Es obligatoria para generar App Passwords
3. **Email incorrecto** — El Gmail que introduces debe ser exactamente el de la cuenta que generó la App Password
4. **App Password revocada** — Genera una nueva en [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)

---

### El Excel no se sube (error 404 o sin respuesta)

1. Verifica que la app está corriendo (`python run.py` activo en terminal)
2. Abre [http://localhost:5000](http://localhost:5000) — si no carga, el servidor no está activo
3. Comprueba que el fichero es `.xlsx` o `.xls`

---

### El dashboard no muestra contactos ("Cargando...")

1. El servidor debe estar corriendo
2. Abre la consola del navegador (F12 → Console) — si hay un error JS, repórtalo
3. Prueba a recargar la página con Ctrl+F5 (fuerza recarga sin caché)

---

### Los emails no llegan al destinatario

1. Revisa que la dirección de email es correcta (sin espacios, con `@`)
2. Comprueba la carpeta **Spam** del destinatario
3. Verifica que el email no aparece como **Rebotado** en el dashboard (columna Error)
4. Evita en el asunto palabras como "GRATIS", "OFERTA", "urgente" en mayúsculas

---

## Preguntas frecuentes

**¿Necesito internet para que funcione?**  
Sí, para enviar emails y detectar respuestas. La interfaz web (dashboard, formularios) funciona en local, pero la conexión con Gmail requiere internet.

**¿Puedo usar una cuenta que no sea Gmail?**  
Por ahora solo soporta Gmail con App Password. El soporte para Outlook/Office365 y otros SMTP está previsto.

**¿Qué pasa si cierro el ordenador a mitad de campaña?**  
Los emails ya enviados se mantienen. Al volver a abrir la app, continuará desde el siguiente contacto pendiente. Los follow-ups programados se recalcularán según las fechas guardadas.

**¿Puedo tener varias campañas activas a la vez?**  
Actualmente solo puede haber una campaña activa a la vez. Para lanzar una nueva, usa "Nueva campaña" en el dashboard.

**¿Puedo editar el Excel mientras la campaña está activa?**  
No recomendado. La app lee y escribe el Excel activamente. Edítalo solo cuando la campaña esté pausada o terminada.

**¿Cómo sé si alguien respondió pero en otro hilo (no como respuesta directa)?**  
El sistema detecta respuestas directas al email usando cabeceras `In-Reply-To`. Si alguien escribe un email nuevo al mismo remitente sin usar "Responder", no se detecta automáticamente.

**¿Puedo usar el mismo Gmail para varias campañas seguidas?**  
Sí. Cada campaña es independiente. La deduplicación garantiza que no se envíe dos veces al mismo contacto.

---

## Estructura del proyecto

```
email-agent/
├── app/
│   ├── __init__.py          # Factory de Flask + SQLAlchemy
│   ├── models.py            # Modelos BD: Campaign, Contact
│   ├── routes.py            # API REST: upload, configure, launch, status...
│   ├── email_service.py     # SMTP (envío) + IMAP (detección respuestas)
│   ├── excel_service.py     # Lectura y escritura del fichero Excel
│   ├── crypto.py            # Cifrado Fernet para contraseñas
│   ├── scheduler.py         # APScheduler: reply check + follow-up jobs
│   └── templates/
│       ├── base.html        # Layout base con navbar ONEtoONE CF
│       ├── index.html       # Paso 1: Subir Excel
│       ├── configure.html   # Paso 2: Configurar campaña
│       └── dashboard.html   # Paso 3: Dashboard en tiempo real
├── static/
│   ├── css/style.css        # Estilos ONEtoONE CF (Inter + Fraunces)
│   └── js/app.js            # Lógica frontend: wizard + dashboard polling
├── instance/
│   └── agent.db             # SQLite (generado automáticamente)
├── uploads/                 # Excels subidos (generado automáticamente)
├── docs de prueba/
│   └── contactos_prueba.xlsx # Excel de ejemplo con 10 contactos
├── config.py                # Configuración Flask
├── run.py                   # Punto de entrada del servidor
├── requirements.txt         # Dependencias Python
└── start.bat                # Lanzador con doble clic para Windows
```

---

## Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Backend | Python 3 + Flask 3 |
| Base de datos | SQLite + SQLAlchemy |
| Email (envío) | smtplib SMTP_SSL → Gmail puerto 465 |
| Email (recepción) | imaplib IMAP4_SSL → imap.gmail.com |
| Lectura/escritura Excel | openpyxl |
| Cifrado | cryptography (Fernet / AES-128) |
| Tareas automáticas | APScheduler 3 |
| Frontend | Bootstrap 5.3 + Vanilla JS |
| Fuentes | Google Fonts: Inter + Fraunces |

---

## Repositorio

[https://github.com/amartii/email-agent](https://github.com/amartii/email-agent)

---

*Desarrollado para ONEtoONE Corporate Finance · 2026*

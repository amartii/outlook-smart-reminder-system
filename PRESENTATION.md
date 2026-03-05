# > Outlook Smart Reminder System
### Documento de presentación del agente

---

## Nombre del agente

**Outlook Smart Reminder System**

Agente inteligente de seguimiento y recordatorios de emails, desarrollado bajo la identidad corporativa de **Accenture**.

---

## Herramienta utilizada

El agente está construido sobre las siguientes tecnologías:

| Capa | Tecnología |
|------|-----------|
| **Backend** | Python 3.10+ · Flask · SQLAlchemy · APScheduler |
| **Protocolo de correo** | SMTP (envío) + IMAP (lectura/detección) — estándar de internet, sin SDKs externos |
| **Base de datos** | SQLite local (sin servidor, sin configuración adicional) |
| **Cifrado** | Fernet (AES-128-CBC) para proteger las credenciales almacenadas |
| **Frontend** | Bootstrap 5 · Vanilla JS · Jinja2 |
| **Identidad visual** | Accenture brand — negro `#000000`, morado `#A100FF`, tipografía Inter |

El agente corre **100% en local** sobre el equipo del usuario. No requiere servicios en la nube, APIs externas de pago ni configuración en Azure o Google Cloud. La única conexión externa es con el servidor de correo corporativo (smtp.office365.com / outlook.office365.com), que ya usa el usuario a diario.

---

## ¿A quién va dirigido?

El agente está dirigido a **profesionales de Accenture** que gestionan relaciones comerciales o de consultoría y cuya actividad diaria implica:

- Enviar emails a **clientes, socios o candidatos** y necesitar hacer seguimiento de las respuestas
- Trabajar con **contactos de diferentes niveles de seniority** (Blue, Manager, Senior Manager, VIP) que requieren tiempos de respuesta distintos
- Manejar **un volumen medio-alto de conversaciones activas** en paralelo, donde perder un seguimiento tiene impacto real en el negocio
- Personas que actualmente llevan ese seguimiento **manualmente en Excel, notas o memoria**, con el riesgo de olvidar o duplicar contactos

**Perfil típico:**
- Consultores de negocio y account managers
- Recruiters y talent acquisition
- Business developers
- Project leads con interlocución externa frecuente

---

## Problema que resuelve

En entornos de consultoría de alto ritmo como Accenture, el seguimiento de emails es una tarea crítica pero costosa en tiempo y atención. El problema concreto que resuelve el agente es:

### Sin el agente

1. Un profesional envía un email a un cliente o candidato
2. La respuesta no llega — el email queda enterrado en la bandeja de enviados
3. Días después, el profesional recuerda (o no) que debe hacer seguimiento
4. Busca manualmente el email, redacta un recordatorio, lo envía
5. Este proceso se repite para cada conversación activa, de forma completamente manual
6. Los contactos de mayor seniority requieren tiempos de espera distintos — difícil de gestionar a mano

### Con el agente

1. El profesional envía el email desde la interfaz del agente
2. El agente registra la conversación y calcula automáticamente cuándo recordar según el nivel del contacto
3. Monitoriza la bandeja de entrada cada 15 minutos buscando respuestas
4. Si detecta respuesta → cierra el seguimiento automáticamente
5. Si detecta una etiqueta en la respuesta ("contestar en 2 días", "al final del día") → reprograma el recordatorio sin intervención humana
6. Si no hay respuesta en el plazo definido → envía el recordatorio automáticamente

El profesional solo interviene cuando hay una acción real que tomar. El ruido de los seguimientos pendientes desaparece.

---

## Datos necesarios para su funcionamiento

### Para instalar y arrancar el agente

| Dato | Descripción |
|------|-------------|
| **Python 3.10+** | Instalado en el equipo |
| **Git** | Para clonar el repositorio |

### Para conectar la cuenta de Outlook

| Dato | Obligatorio | Descripción |
|------|-------------|-------------|
| **Email corporativo** | ✅ | La dirección desde la que se enviarán los emails (`nombre@empresa.com`) |
| **Contraseña de Outlook** | ✅ | La contraseña habitual de la cuenta. Si la cuenta tiene verificación en dos pasos (MFA), se necesita generar una **contraseña de aplicación** desde account.microsoft.com |

> Los servidores SMTP/IMAP de Office 365 ya están preconfigurados. No hay que introducir ningún dato técnico adicional salvo que se use un proveedor distinto.

### Para usar el agente en el día a día

| Dato | Descripción |
|------|-------------|
| **Email del destinatario** | A quién va dirigido el email |
| **Nombre y cargo del contacto** | Para asignarle la categoría correcta y personalizar los recordatorios |
| **Categoría del contacto** | Blue / Manager / Senior Manager / VIP — define el tiempo de espera antes de recordar |
| **Asunto y cuerpo del email** | El mensaje que se quiere enviar |

### Ningún dato sale del equipo salvo los propios emails

Las credenciales se almacenan **cifradas** en la base de datos local. No se envían a ningún servidor externo. El agente solo se comunica con el servidor de correo corporativo de Microsoft.

---

## Beneficios que aporta

### ⏱ Ahorro de tiempo
Elimina la gestión manual de seguimientos. Un profesional con 20 conversaciones activas puede pasar de dedicar 30–45 minutos diarios a revisar y redactar recordatorios, a no dedicar ninguno — el agente lo hace automáticamente.

### 🎯 Cero seguimientos olvidados
El sistema no depende de la memoria ni de recordatorios en el calendario. Cada email enviado tiene asociado un recordatorio calculado automáticamente. Si no hay respuesta, el seguimiento se envía sin falta.

### 🧠 Adaptación inteligente por nivel de contacto
No todos los contactos requieren el mismo ritmo. Un perfil "Blue" puede recibir un seguimiento en 24h; un "VIP" merece más paciencia — 96h. El agente aplica estas reglas automáticamente según la categoría asignada.

### 🔄 Reprogramación automática por etiquetas
Si un contacto responde "contestar después de 2 días" o "al final del día", el agente detecta esa instrucción y reprograma el recordatorio solo. Sin acción humana.

### 🔒 Privacidad y control total
Todo corre en local. Las credenciales están cifradas. Los emails no pasan por ningún intermediario. El profesional tiene control total sobre sus datos.

### 📊 Visibilidad en tiempo real
El dashboard muestra en todo momento cuántos emails están pendientes de respuesta, cuáles tienen recordatorio próximo, y un historial de toda la actividad. No hay más incertidumbre sobre el estado de las conversaciones.

### 🚀 Instalación en minutos
No requiere Azure, OAuth, APIs de pago ni configuración en la nube. Instalar Python, clonar el repositorio, ejecutar `python run.py`, introducir email y contraseña — y el agente está operativo.

---

## Enlace al agente

📦 **Repositorio GitHub:**
[https://github.com/amartii/outlook-smart-reminder-system](https://github.com/amartii/outlook-smart-reminder-system)

📄 **Documentación técnica:**
[DOCUMENTATION.md](https://github.com/amartii/outlook-smart-reminder-system/blob/main/DOCUMENTATION.md)

🚀 **Guía de instalación paso a paso:**
[SETUP.md](https://github.com/amartii/outlook-smart-reminder-system/blob/main/SETUP.md)

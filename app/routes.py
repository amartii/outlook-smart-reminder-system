"""
routes.py  —  Outlook Smart Reminder System
"""
import logging
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, redirect, url_for

from app import db
from app.models import OutlookConnection, CategoryRule, Contact, SentEmail, Reminder
from app.crypto import encrypt, decrypt

logger = logging.getLogger(__name__)
main = Blueprint("main", __name__)

DELEGATED_SCOPES = [
    "Mail.Send", "Mail.ReadWrite", "Contacts.Read", "User.Read", "offline_access"
]

# Temporary in-memory store for active device code flows (local app, fine)
_device_flows: dict = {}


def _get_active_connection():
    return OutlookConnection.query.filter_by(is_active=True).first()


def _build_service(conn):
    """Return the right service based on connection backend_type."""
    if conn.backend_type == "delegated":
        from app.delegated_service import DelegatedGraphService
        return DelegatedGraphService(conn.id)
    # smtp fallback
    from app.smtp_service import SMTPService
    return SMTPService(
        smtp_host=conn.smtp_host or "smtp.gmail.com",
        smtp_port=conn.smtp_port or 587,
        imap_host=conn.imap_host or "imap.gmail.com",
        imap_port=conn.imap_port or 993,
        username=conn.user_email,
        password=decrypt(conn.password_enc),
        sender_email=conn.user_email,
    )


# ── Pages ──────────────────────────────────────────────────────────────────────

@main.route("/")
def index():
    conn = _get_active_connection()
    return redirect(url_for("main.setup") if not conn else url_for("main.dashboard"))


@main.route("/setup")
def setup():
    conn = _get_active_connection()
    return render_template("setup.html", connection=conn)


@main.route("/categories")
def categories():
    conn = _get_active_connection()
    if not conn:
        return redirect(url_for("main.setup"))
    return render_template("categories.html", connection=conn)


@main.route("/dashboard")
def dashboard():
    conn = _get_active_connection()
    if not conn:
        return redirect(url_for("main.setup"))
    return render_template("dashboard.html", connection=conn)


# ── Outlook connection ─────────────────────────────────────────────────────────

@main.route("/api/outlook/test", methods=["POST"])
def api_outlook_test():
    from app.smtp_service import SMTPService
    data = request.get_json() or {}
    for f in ["user_email", "password"]:
        if not data.get(f):
            return jsonify({"ok": False, "message": f"Campo requerido: {f}"}), 400
    svc = SMTPService(
        smtp_host=data.get("smtp_host", "smtp.office365.com"),
        smtp_port=int(data.get("smtp_port", 587)),
        imap_host=data.get("imap_host", "outlook.office365.com"),
        imap_port=int(data.get("imap_port", 993)),
        username=data["user_email"].strip(),
        password=data["password"].strip(),
    )
    ok, message = svc.validate_connection()
    # Return the port that actually worked so the UI can update
    return jsonify({"ok": ok, "message": message, "smtp_port": svc.smtp_port})


@main.route("/api/outlook/connect", methods=["POST"])
def api_outlook_connect():
    from app.smtp_service import SMTPService
    from app.category_manager import CategoryManager
    data = request.get_json() or {}
    for f in ["user_email", "password"]:
        if not data.get(f):
            return jsonify({"error": f"Campo requerido: {f}"}), 400

    email = data["user_email"].strip().lower()
    password = data["password"].strip()
    smtp_host = data.get("smtp_host", "smtp.office365.com").strip()
    smtp_port = int(data.get("smtp_port", 587))
    imap_host = data.get("imap_host", "outlook.office365.com").strip()
    imap_port = int(data.get("imap_port", 993))

    svc = SMTPService(smtp_host, smtp_port, imap_host, imap_port, email, password)
    ok, message = svc.validate_connection()
    if not ok:
        return jsonify({"error": message}), 400

    # svc.smtp_port may have been auto-switched to 465 during validation
    working_smtp_port = svc.smtp_port

    OutlookConnection.query.update({"is_active": False})
    db.session.flush()
    conn = OutlookConnection(
        backend_type="smtp",
        user_email=email,
        display_name=data.get("display_name", "").strip() or email,
        password_enc=encrypt(password),
        smtp_host=smtp_host, smtp_port=working_smtp_port,
        imap_host=imap_host, imap_port=imap_port,
        is_active=True,
    )
    db.session.add(conn)
    db.session.commit()
    CategoryManager.seed_default_categories()
    return jsonify({"message": message, "connection": conn.to_dict()})


@main.route("/api/connection", methods=["GET"])
def api_connection():
    conn = _get_active_connection()
    return jsonify({"connection": conn.to_dict() if conn else None})


@main.route("/api/outlook/disconnect", methods=["POST"])
def api_outlook_disconnect():
    OutlookConnection.query.update({"is_active": False})
    db.session.commit()
    return jsonify({"message": "Conexion desactivada"})


# ── Microsoft OAuth2 Device Code Flow ─────────────────────────────────────────

@main.route("/api/auth/device-code/start", methods=["POST"])
def api_device_code_start():
    """Initiate Microsoft OAuth2 device code flow."""
    import msal
    data = request.get_json() or {}
    client_id = data.get("client_id", "").strip()
    if not client_id:
        return jsonify({"error": "client_id requerido"}), 400

    msal_app = msal.PublicClientApplication(
        client_id,
        authority="https://login.microsoftonline.com/common",
    )
    flow = msal_app.initiate_device_flow(scopes=DELEGATED_SCOPES)
    if "error" in flow:
        return jsonify({"error": flow.get("error_description", flow["error"])}), 400

    _device_flows[flow["device_code"]] = {"flow": flow, "client_id": client_id}
    return jsonify({
        "user_code": flow["user_code"],
        "verification_uri": flow.get("verification_uri", "https://microsoft.com/devicelogin"),
        "message": flow.get("message", ""),
        "device_code": flow["device_code"],
        "expires_in": flow.get("expires_in", 900),
        "interval": flow.get("interval", 5),
    })


@main.route("/api/auth/device-code/poll", methods=["POST"])
def api_device_code_poll():
    """Poll Microsoft token endpoint for device code completion (non-blocking)."""
    import requests as req
    from app.category_manager import CategoryManager
    data = request.get_json() or {}
    device_code_key = data.get("device_code", "")

    if device_code_key not in _device_flows:
        return jsonify({"status": "expired"})

    stored = _device_flows[device_code_key]
    client_id = stored["client_id"]
    device_code = stored["flow"]["device_code"]

    # Poll Microsoft token endpoint directly (non-blocking single request)
    resp = req.post(
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": client_id,
            "device_code": device_code,
        },
        timeout=15,
    )
    result = resp.json()

    if "access_token" in result:
        # Success — store connection
        refresh_token = result.get("refresh_token", "")
        # Get user info from Graph
        try:
            me_resp = req.get(
                "https://graph.microsoft.com/v1.0/me?$select=displayName,mail,userPrincipalName",
                headers={"Authorization": f"Bearer {result['access_token']}"},
                timeout=10,
            )
            me = me_resp.json()
            user_email = (me.get("mail") or me.get("userPrincipalName", "")).lower()
            display_name = me.get("displayName", user_email)
        except Exception:
            user_email = ""
            display_name = ""

        OutlookConnection.query.update({"is_active": False})
        db.session.flush()
        conn = OutlookConnection(
            backend_type="delegated",
            client_id=client_id,
            user_email=user_email,
            display_name=display_name,
            password_enc=encrypt(refresh_token),  # refresh token stored here
            is_active=True,
        )
        db.session.add(conn)
        db.session.commit()
        CategoryManager.seed_default_categories()

        del _device_flows[device_code_key]
        return jsonify({"status": "ok", "email": user_email, "name": display_name,
                        "connection": conn.to_dict()})

    error = result.get("error", "")
    if error in ("authorization_pending", "slow_down"):
        return jsonify({"status": "pending"})
    if error in ("expired_token", "code_expired", "authorization_declined"):
        _device_flows.pop(device_code_key, None)
        return jsonify({"status": "expired", "message": result.get("error_description", "")})

    return jsonify({"status": "error", "message": result.get("error_description", error)})


# ── Categories ─────────────────────────────────────────────────────────────────

@main.route("/api/categories", methods=["GET"])
def api_categories_list():
    rules = CategoryRule.query.order_by(CategoryRule.reminder_hours).all()
    return jsonify({"categories": [r.to_dict() for r in rules]})


@main.route("/api/categories", methods=["POST"])
def api_categories_create():
    data = request.get_json() or {}
    if not data.get("name"):
        return jsonify({"error": "El nombre es obligatorio"}), 400
    if CategoryRule.query.filter_by(name=data["name"]).first():
        return jsonify({"error": f"Ya existe una categoria '{data['name']}'"}), 409
    rule = CategoryRule(name=data["name"].strip(), color=data.get("color","preset4"),
                        reminder_hours=int(data.get("reminder_hours", 72)), description=data.get("description",""))
    db.session.add(rule)
    db.session.commit()
    conn = _get_active_connection()
    if conn:
        try: _build_service(conn).ensure_category_exists(rule.name, rule.color)
        except Exception as exc: logger.warning("Outlook category sync: %s", exc)
    return jsonify({"category": rule.to_dict()}), 201


@main.route("/api/categories/<int:rule_id>", methods=["PUT"])
def api_categories_update(rule_id):
    rule = CategoryRule.query.get_or_404(rule_id)
    data = request.get_json() or {}
    for field in ("name","color","description"):
        if field in data: setattr(rule, field, data[field])
    if "reminder_hours" in data: rule.reminder_hours = int(data["reminder_hours"])
    db.session.commit()
    return jsonify({"category": rule.to_dict()})


@main.route("/api/categories/<int:rule_id>", methods=["DELETE"])
def api_categories_delete(rule_id):
    rule = CategoryRule.query.get_or_404(rule_id)
    Contact.query.filter_by(category_id=rule_id).update({"category_id": None})
    db.session.delete(rule)
    db.session.commit()
    return jsonify({"message": f"Categoria '{rule.name}' eliminada"})


# ── Contacts ───────────────────────────────────────────────────────────────────

@main.route("/api/contacts", methods=["GET"])
def api_contacts_list():
    q = request.args.get("q","").strip()
    cat_id = request.args.get("category_id")
    query = Contact.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Contact.email.ilike(like), Contact.display_name.ilike(like), Contact.company_name.ilike(like)))
    if cat_id: query = query.filter_by(category_id=int(cat_id))
    return jsonify({"contacts": [c.to_dict() for c in query.order_by(Contact.display_name).all()]})


@main.route("/api/contacts", methods=["POST"])
def api_contacts_create():
    data = request.get_json() or {}
    if not data.get("email"): return jsonify({"error": "El email es obligatorio"}), 400
    email = data["email"].strip().lower()
    if Contact.query.filter_by(email=email).first(): return jsonify({"error": f"El contacto {email} ya existe"}), 409
    contact = Contact(email=email, display_name=data.get("display_name","").strip(),
                      job_title=data.get("job_title","").strip(), company_name=data.get("company_name","").strip(),
                      notes=data.get("notes",""), category_id=data.get("category_id"))
    db.session.add(contact)
    db.session.commit()
    return jsonify({"contact": contact.to_dict()}), 201


@main.route("/api/contacts/sync", methods=["POST"])
def api_contacts_sync():
    conn = _get_active_connection()
    if not conn: return jsonify({"error": "No hay conexion activa con Outlook"}), 400
    try:
        contacts_data = _build_service(conn).sync_contacts()
    except Exception as exc:
        return jsonify({"error": f"Error sincronizando: {exc}"}), 500
    new_count = 0
    for c in contacts_data:
        if not c.get("email"): continue
        existing = Contact.query.filter_by(email=c["email"]).first()
        if existing:
            existing.display_name = c["display_name"] or existing.display_name
            existing.job_title = c["job_title"] or existing.job_title
            existing.company_name = c["company_name"] or existing.company_name
            existing.outlook_id = c["outlook_id"] or existing.outlook_id
            existing.updated_at = datetime.utcnow()
        else:
            db.session.add(Contact(email=c["email"], display_name=c["display_name"],
                                   job_title=c["job_title"], company_name=c["company_name"], outlook_id=c["outlook_id"]))
            new_count += 1
    db.session.commit()
    return jsonify({"message": f"Sincronizacion completada. {new_count} nuevos contactos.", "total": len(contacts_data), "new": new_count})


@main.route("/api/contacts/<int:contact_id>/category", methods=["POST"])
def api_contacts_assign_category(contact_id):
    from app.category_manager import CategoryManager
    data = request.get_json() or {}
    category_id = data.get("category_id")
    if category_id is None: return jsonify({"error": "category_id requerido"}), 400
    ok = CategoryManager.assign_category(contact_id, int(category_id))
    if not ok: return jsonify({"error": "Contacto o categoria no encontrados"}), 404
    return jsonify({"contact": Contact.query.get(contact_id).to_dict()})


@main.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
def api_contacts_delete(contact_id):
    contact = Contact.query.get_or_404(contact_id)
    for se in contact.sent_emails:
        Reminder.query.filter_by(sent_email_id=se.id).delete()
    SentEmail.query.filter_by(contact_id=contact_id).delete()
    db.session.delete(contact)
    db.session.commit()
    return jsonify({"message": f"Contacto {contact.email} eliminado"})


# ── Email sending ──────────────────────────────────────────────────────────────

@main.route("/api/emails/send", methods=["POST"])
def api_emails_send():
    from datetime import timedelta
    from app.category_manager import CategoryManager
    conn = _get_active_connection()
    if not conn: return jsonify({"error": "No hay conexion activa con Outlook"}), 400
    data = request.get_json() or {}
    for f in ["contact_id","subject","body_html"]:
        if not data.get(f): return jsonify({"error": f"Campo requerido: {f}"}), 400
    contact = Contact.query.get(data["contact_id"])
    if not contact: return jsonify({"error": "Contacto no encontrado"}), 404
    try:
        svc = _build_service(conn)
        category_name = contact.category_rule.name if contact.category_rule else None
        result = svc.send_email(to_email=contact.email, subject=data["subject"],
                                body_html=data["body_html"], body_text=data.get("body_text",""), category=category_name)
        now = datetime.utcnow()
        reminder_hours = CategoryManager.get_reminder_hours(contact.id)
        reminder_at = CategoryManager.calculate_reminder_at(now, reminder_hours)
        sent = SentEmail(contact_id=contact.id, connection_id=conn.id, subject=data["subject"],
                         body_preview=data["body_html"][:300], message_id=result.get("message_id",""),
                         conversation_id=result.get("conversation_id",""), graph_message_id=result.get("graph_id",""),
                         sent_at=now, reminder_at=reminder_at, status="pending")
        db.session.add(sent)
        db.session.commit()
        return jsonify({"message": f"Email enviado a {contact.email}", "sent_email": sent.to_dict()}), 201
    except Exception as exc:
        logger.exception("Email send error")
        return jsonify({"error": f"Error enviando email: {exc}"}), 500


@main.route("/api/emails", methods=["GET"])
def api_emails_list():
    status = request.args.get("status")
    contact_id = request.args.get("contact_id")
    query = SentEmail.query
    if status: query = query.filter_by(status=status)
    if contact_id: query = query.filter_by(contact_id=int(contact_id))
    emails = query.order_by(SentEmail.sent_at.desc()).limit(100).all()
    return jsonify({"emails": [e.to_dict() for e in emails]})


# ── Reminders ──────────────────────────────────────────────────────────────────

@main.route("/api/reminders/pending", methods=["GET"])
def api_reminders_pending():
    from app.reminder_engine import ReminderEngine
    return jsonify({"reminders": [se.to_dict() for se in ReminderEngine.get_pending_reminders()]})


@main.route("/api/reminders/upcoming", methods=["GET"])
def api_reminders_upcoming():
    from app.reminder_engine import ReminderEngine
    hours = int(request.args.get("hours", 24))
    return jsonify({"reminders": [se.to_dict() for se in ReminderEngine.get_upcoming_reminders(hours_ahead=hours)]})


@main.route("/api/reminders/<int:sent_email_id>/send-now", methods=["POST"])
def api_reminders_send_now(sent_email_id):
    from app.reminder_engine import ReminderEngine
    conn = _get_active_connection()
    if not conn: return jsonify({"error": "No hay conexion activa"}), 400
    ok = ReminderEngine.send_reminder(sent_email_id, _build_service(conn))
    se = SentEmail.query.get(sent_email_id)
    return jsonify({"message": "Recordatorio enviado", "sent_email": se.to_dict()}) if ok else jsonify({"error": "No se pudo enviar"}), 500


@main.route("/api/reminders/<int:sent_email_id>/snooze", methods=["POST"])
def api_reminders_snooze(sent_email_id):
    from app.reminder_engine import ReminderEngine
    hours = int((request.get_json() or {}).get("hours", 24))
    ok = ReminderEngine.snooze(sent_email_id, hours)
    if not ok: return jsonify({"error": "SentEmail no encontrado"}), 404
    return jsonify({"message": f"Pospuesto {hours}h", "sent_email": SentEmail.query.get(sent_email_id).to_dict()})


@main.route("/api/reminders/<int:sent_email_id>/close", methods=["POST"])
def api_reminders_close(sent_email_id):
    from app.reminder_engine import ReminderEngine
    ok = ReminderEngine.close(sent_email_id)
    if not ok: return jsonify({"error": "SentEmail no encontrado"}), 404
    return jsonify({"message": "Recordatorio cerrado", "sent_email": SentEmail.query.get(sent_email_id).to_dict()})


# ── Dashboard stats ────────────────────────────────────────────────────────────

@main.route("/api/dashboard/stats", methods=["GET"])
def api_dashboard_stats():
    from app.reminder_engine import ReminderEngine
    total_emails = SentEmail.query.count()
    by_status = {s: SentEmail.query.filter_by(status=s).count()
                 for s in ("pending","replied","reminder_sent","snoozed","closed")}
    overdue     = len(ReminderEngine.get_pending_reminders())
    upcoming_24 = len(ReminderEngine.get_upcoming_reminders(24))
    categories  = CategoryRule.query.all()
    cat_breakdown = []
    for cat in categories:
        ids = [c.id for c in cat.contacts]
        pending_count = SentEmail.query.filter(SentEmail.contact_id.in_(ids), SentEmail.status.in_(["pending","snoozed"])).count() if ids else 0
        cat_breakdown.append({"id":cat.id,"name":cat.name,"color":cat.color,"reminder_hours":cat.reminder_hours,
                               "pending_reminders":pending_count,"contacts_count":len(cat.contacts)})
    recent_reminders = Reminder.query.order_by(Reminder.sent_at.desc()).limit(20).all()
    recent_replies   = SentEmail.query.filter(SentEmail.replied_at.isnot(None)).order_by(SentEmail.replied_at.desc()).limit(20).all()
    activity = []
    for r in recent_reminders:
        se = SentEmail.query.get(r.sent_email_id)
        activity.append({"type":"reminder","at":r.sent_at.isoformat(),
                         "contact": se.contact.display_name or se.contact.email if se and se.contact else "—",
                         "subject": se.subject if se else ""})
    for se in recent_replies:
        activity.append({"type":"reply","at":se.replied_at.isoformat(),
                         "contact": se.contact.display_name or se.contact.email if se.contact else "—",
                         "subject":se.subject,"label":se.response_label})
    activity.sort(key=lambda x: x["at"], reverse=True)
    return jsonify({"total_emails":total_emails,"by_status":by_status,"overdue_reminders":overdue,
                    "upcoming_24h":upcoming_24,"total_contacts":Contact.query.count(),
                    "total_categories":CategoryRule.query.count(),"category_breakdown":cat_breakdown,"activity":activity[:30]})


@main.route("/api/activity", methods=["GET"])
def api_activity():
    reminders = Reminder.query.order_by(Reminder.sent_at.desc()).limit(50).all()
    replies   = SentEmail.query.filter(SentEmail.replied_at.isnot(None)).order_by(SentEmail.replied_at.desc()).limit(50).all()
    events = []
    for r in reminders:
        se = SentEmail.query.get(r.sent_email_id)
        events.append({"type":"reminder_sent","at":r.sent_at.isoformat(),
                       "contact": se.contact.display_name or se.contact.email if se and se.contact else "—",
                       "subject": se.subject if se else "","notes":r.notes})
    for se in replies:
        events.append({"type":"reply_received","at":se.replied_at.isoformat(),
                       "contact": se.contact.display_name or se.contact.email if se.contact else "—",
                       "subject":se.subject,"label":se.response_label})
    events.sort(key=lambda x: x["at"], reverse=True)
    return jsonify({"activity": events[:50]})

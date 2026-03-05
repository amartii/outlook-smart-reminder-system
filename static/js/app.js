// Outlook Smart Reminder System — Accenture — app.js
// Shared utilities used across all pages.

function esc(s) {
    return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function fmt(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString('es-ES', {
        day:'2-digit', month:'2-digit', year:'2-digit',
        hour:'2-digit', minute:'2-digit'
    });
}

function showAlert(msg, type = 'info') {
    const container = document.getElementById('alertContainer');
    if (!container) { console.warn(msg); return; }
    const id = 'alert_' + Date.now();
    container.insertAdjacentHTML('beforeend', `
        <div id="${id}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${esc(msg)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>`);
    setTimeout(() => document.getElementById(id)?.remove(), 6000);
}

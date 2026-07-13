"""Utilidades de seguridad para la aplicación Flask."""

import hmac
import ipaddress
import json
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

from flask import abort, jsonify, request, session

CSRF_FIELD_NAME = '_csrf_token'
# Un deque de marcas de tiempo por cada (ip, endpoint). En memoria y por proceso;
# suficiente para un despliegue de un solo worker (waitress) en red interna.
_rate_limit_buckets = defaultdict(deque)
# Contador de peticiones para lanzar una purga esporádica de buckets vacíos y no
# acumular claves de clientes que dejaron de enviar tráfico.
_rate_limit_requests_since_sweep = 0
_RATE_LIMIT_SWEEP_EVERY = 1000


def get_csrf_token():
    """Devuelve el token CSRF de la sesión actual, creándolo si hace falta."""
    token = session.get(CSRF_FIELD_NAME)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_FIELD_NAME] = token
    return token


def configure_security(app):
    """Registra protección CSRF básica y headers defensivos."""

    @app.before_request
    def validate_host_and_client_ip():
        allowed_hosts = app.config.get('ALLOWED_HOSTS', [])
        if allowed_hosts:
            host = (request.host or '').split(':', 1)[0].lower()
            if host not in allowed_hosts:
                abort(400, description='Host no permitido.')

        allowlist = app.config.get('CLIENT_IP_ALLOWLIST', [])
        if allowlist and not _client_ip_allowed(request.remote_addr, allowlist):
            abort(403, description='Cliente no autorizado.')

        return None

    @app.context_processor
    def csrf_context():
        return {'csrf_token': get_csrf_token, 'csrf_field_name': CSRF_FIELD_NAME}

    @app.before_request
    def apply_rate_limit():
        if not app.config.get('RATE_LIMIT_ENABLED', True) or request.endpoint == 'static':
            return None

        now = time.monotonic()
        window = app.config['RATE_LIMIT_WINDOW_SECONDS']
        max_requests = app.config['RATE_LIMIT_MAX_REQUESTS']
        _sweep_rate_limit_buckets(now, window)
        key = (request.remote_addr or 'local', request.endpoint or request.path)
        bucket = _rate_limit_buckets[key]

        while bucket and now - bucket[0] > window:
            bucket.popleft()

        if len(bucket) >= max_requests:
            response = jsonify({'error': 'rate_limit', 'message': 'Demasiadas solicitudes. Intenta de nuevo más tarde.'})
            response.status_code = 429
            response.headers['Retry-After'] = str(window)
            return response

        bucket.append(now)
        return None

    @app.before_request
    def validate_csrf():
        if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return None

        expected = session.get(CSRF_FIELD_NAME)
        received = request.form.get(CSRF_FIELD_NAME) or request.headers.get('X-CSRFToken')

        if not expected or not received or not hmac.compare_digest(expected, received):
            abort(400, description='CSRF token inválido o ausente.')

        return None

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        # Aísla el contexto de navegación de otros orígenes (defensa extra frente a
        # fugas cross-origin). No afecta a esta app: no abre popups ni comparte recursos.
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        response.headers.setdefault('X-Permitted-Cross-Domain-Policies', 'none')
        # HSTS solo si la petición llegó por HTTPS; en el uso local por HTTP no se
        # emite, para no forzar TLS donde todavía no lo hay.
        if request.is_secure:
            response.headers.setdefault(
                'Strict-Transport-Security', 'max-age=31536000; includeSubDomains'
            )
        # NOTA: script/style mantienen 'unsafe-inline' porque Tailwind se sirve por CDN
        # (compila estilos en el navegador). Para eliminarlo hay que precompilar Tailwind
        # a un CSS local; queda pendiente junto con el login. object-src 'none' bloquea
        # plugins/<object>/<embed>, que esta app no usa.
        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self' data:; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response

    @app.after_request
    def write_audit_log(response):
        if not app.config.get('AUDIT_LOG_ENABLED', True):
            return response
        if request.method not in {'POST', 'PUT', 'PATCH', 'DELETE'}:
            return response

        audit_path = _resolve_instance_path(app, app.config['AUDIT_LOG_PATH'])
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        _rotate_audit_log_if_needed(audit_path, app.config.get('AUDIT_LOG_MAX_BYTES', 0))
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'method': request.method,
            'path': request.path,
            'endpoint': request.endpoint,
            'status_code': response.status_code,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', '')[:200],
        }
        with audit_path.open('a', encoding='utf-8') as log_file:
            log_file.write(json.dumps(event, ensure_ascii=False) + '\n')

        return response

    @app.errorhandler(400)
    def bad_request(error):
        return _error_response('solicitud_invalida', getattr(error, 'description', 'Solicitud inválida.'), 400)

    @app.errorhandler(404)
    def not_found(error):
        return _error_response('no_encontrado', 'Recurso no encontrado.', 404)

    @app.errorhandler(403)
    def forbidden(error):
        return _error_response('no_autorizado', getattr(error, 'description', 'Acceso no autorizado.'), 403)

    @app.errorhandler(413)
    def payload_too_large(error):
        return _error_response('solicitud_demasiado_grande', 'La solicitud supera el tamaño permitido.', 413)

    @app.errorhandler(429)
    def too_many_requests(error):
        return _error_response('demasiadas_solicitudes', 'Demasiadas solicitudes. Intenta de nuevo más tarde.', 429)

    @app.errorhandler(500)
    def internal_error(error):
        return _error_response('error_interno', 'Ocurrió un error interno.', 500)


def _sweep_rate_limit_buckets(now, window):
    """Elimina periódicamente los buckets ya vencidos para acotar la memoria.

    No altera el conteo de los clientes activos: solo descarta claves cuyas marcas
    de tiempo caen todas fuera de la ventana actual (clientes que dejaron de pedir).
    """
    global _rate_limit_requests_since_sweep
    _rate_limit_requests_since_sweep += 1
    if _rate_limit_requests_since_sweep < _RATE_LIMIT_SWEEP_EVERY:
        return
    _rate_limit_requests_since_sweep = 0

    for key in list(_rate_limit_buckets.keys()):
        bucket = _rate_limit_buckets[key]
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if not bucket:
            del _rate_limit_buckets[key]


def _rotate_audit_log_if_needed(audit_path, max_bytes):
    """Rota el audit log a <archivo>.1 cuando supera max_bytes (0 = sin límite)."""
    if not max_bytes or max_bytes <= 0:
        return
    try:
        if audit_path.exists() and audit_path.stat().st_size >= max_bytes:
            respaldo = audit_path.with_name(audit_path.name + '.1')
            respaldo.unlink(missing_ok=True)
            audit_path.replace(respaldo)
    except OSError:
        # Si la rotación falla (permisos, bloqueo en Windows) se sigue escribiendo
        # en el archivo actual: preservar el registro es más importante que rotar.
        pass


def _resolve_instance_path(app, configured_path):
    path = Path(configured_path)
    if path.is_absolute():
        return path
    return Path(app.instance_path) / path


def _client_ip_allowed(remote_addr, allowlist):
    if not remote_addr:
        return False
    try:
        client_ip = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False

    for item in allowlist:
        try:
            if '/' in item:
                if client_ip in ipaddress.ip_network(item, strict=False):
                    return True
            elif client_ip == ipaddress.ip_address(item):
                return True
        except ValueError:
            continue
    return False


def _error_response(code, message, status_code):
    if request.path.startswith('/api/') or request.accept_mimetypes.best == 'application/json':
        return jsonify({'error': code, 'message': message}), status_code
    return f'{status_code} - {message}', status_code

"""Configuración de la aplicación."""

import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    APP_ENV = os.getenv('APP_ENV', 'development')
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave-local-de-desarrollo')
    SERVER_HOST = os.getenv('SERVER_HOST', '127.0.0.1')
    SERVER_PORT = int(os.getenv('SERVER_PORT', '5000'))
    ALLOWED_HOSTS = [
        host.strip().lower()
        for host in os.getenv('ALLOWED_HOSTS', '').split(',')
        if host.strip()
    ]
    CLIENT_IP_ALLOWLIST = [
        item.strip()
        for item in os.getenv('CLIENT_IP_ALLOWLIST', '').split(',')
        if item.strip()
    ]
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', str(2 * 1024 * 1024)))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
    RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv('RATE_LIMIT_WINDOW_SECONDS', '60'))
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv('RATE_LIMIT_MAX_REQUESTS', '240'))
    AUDIT_LOG_ENABLED = os.getenv('AUDIT_LOG_ENABLED', 'true').lower() == 'true'
    AUDIT_LOG_PATH = os.getenv('AUDIT_LOG_PATH', 'security_audit.log')
    # Tamaño máximo del audit log antes de rotarlo (por defecto 5 MB). Al superarlo
    # se renombra a <archivo>.1 y se empieza uno nuevo, evitando crecimiento sin fin.
    AUDIT_LOG_MAX_BYTES = int(os.getenv('AUDIT_LOG_MAX_BYTES', str(5 * 1024 * 1024)))
    SQLITE_BUSY_TIMEOUT_MS = int(os.getenv('SQLITE_BUSY_TIMEOUT_MS', '5000'))
    REPORT_TEMPLATE_PATH = os.getenv('REPORT_TEMPLATE_PATH', 'app/static/formato_reporte_demo.xlsx')
    REPORT_SHEET_NAME = os.getenv('REPORT_SHEET_NAME', 'Equipo_Inventario')
    APP_TITLE = os.getenv('APP_TITLE', 'Inventario TI')
    SPECIALIZED_SYSTEMS_TITLE = os.getenv('SPECIALIZED_SYSTEMS_TITLE', 'Sistemas Especializados')
    SPECIALIZED_SYSTEM_LABELS = {
        'helpdesk_system': os.getenv('LABEL_HELPDESK_SYSTEM', 'Mesa de ayuda'),
        'system_a': os.getenv('LABEL_SYSTEM_A', 'Sistema A'),
        'system_b': os.getenv('LABEL_SYSTEM_B', 'Sistema B'),
        'system_c': os.getenv('LABEL_SYSTEM_C', 'Sistema C'),
        'messaging_system': os.getenv('LABEL_MESSAGING_SYSTEM', 'Mensajería'),
        'erp_system': os.getenv('LABEL_ERP_SYSTEM', 'ERP'),
        'learning_platform': os.getenv('LABEL_LEARNING_PLATFORM', 'E-learning'),
        'quality_system': os.getenv('LABEL_QUALITY_SYSTEM', 'Gestión de calidad'),
        'internal_database': os.getenv('LABEL_INTERNAL_DATABASE', 'Base de datos interna'),
    }
    BASE_POSITIONS = [
        p.strip()
        for p in os.getenv('BASE_POSITIONS', 'Area 1,Area 2,Administracion,Gerencia,SITE').split(',')
        if p.strip()
    ]
    # Ruta relativa: con instance_relative_config=True, Flask/SQLAlchemy la resuelve
    # dentro de la carpeta instance/, donde vive inventario.db.
    SQLALCHEMY_DATABASE_URI = 'sqlite:///inventario.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

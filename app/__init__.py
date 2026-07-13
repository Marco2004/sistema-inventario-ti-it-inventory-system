"""Fábrica de la aplicación: crea la app, enlaza la BD y registra las rutas."""
from flask import Flask
from sqlalchemy import event

from .config import Config
from .models import db, TipoActivo, Posicion
from .rutas import registrar_rutas
from .security import configure_security


def crear_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    _validar_configuracion(app)
    configure_security(app)

    @app.context_processor
    def etiquetas_interfaz():
        return {
            'app_title': app.config['APP_TITLE'],
            'specialized_systems_title': app.config['SPECIALIZED_SYSTEMS_TITLE'],
            'system_labels': app.config['SPECIALIZED_SYSTEM_LABELS'],
        }

    @app.teardown_request
    def rollback_on_error(error):
        if error is not None:
            db.session.rollback()

    db.init_app(app)
    registrar_rutas(app)

    with app.app_context():
        _registrar_pragmas_sqlite(app.config['SQLITE_BUSY_TIMEOUT_MS'])
        db.create_all()
        _sembrar_catalogos_base(app.config['BASE_POSITIONS'])

    return app


def _validar_configuracion(app):
    """Valida configuraciones riesgosas cuando se declara entorno de servidor."""
    if app.config['APP_ENV'].lower() in {'production', 'server'}:
        secret_key = app.config['SECRET_KEY']
        claves_inseguras = {'clave-local-de-desarrollo', 'cambia-esta-clave-en-tu-pc'}
        if secret_key in claves_inseguras or len(secret_key) < 32:
            raise RuntimeError('Configura una SECRET_KEY privada y larga antes de usar APP_ENV=production/server.')
        if app.config.get('SESSION_COOKIE_SECURE') and app.config['SERVER_HOST'] == '127.0.0.1':
            raise RuntimeError('SESSION_COOKIE_SECURE=true requiere servir la app por HTTPS.')


def _registrar_pragmas_sqlite(busy_timeout_ms):
    """Aplica pragmas útiles cada vez que SQLAlchemy abre una conexión SQLite."""

    @event.listens_for(db.engine, 'connect')
    def set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute(f'PRAGMA busy_timeout={busy_timeout_ms}')
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.close()


def _sembrar_catalogos_base(posiciones_base):
    """Inserta los catálogos base (tipos de activo y posiciones) si las tablas están vacías."""
    if not TipoActivo.query.first():
        tipos_base = ['computadora', 'laptop', 'mouse', 'teclado', 'diadema', 'monitor']
        for t in tipos_base:
            db.session.add(TipoActivo(nombre=t))
        db.session.commit()
    if not Posicion.query.first():
        for p in posiciones_base:
            db.session.add(Posicion(nombre=p))
        db.session.commit()

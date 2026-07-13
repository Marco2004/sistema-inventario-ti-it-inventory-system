"""Modelos de base de datos del sistema de inventario."""
import os

from flask_sqlalchemy import SQLAlchemy

# Instancia compartida. Se enlaza a la app en la fábrica con db.init_app(app).
db = SQLAlchemy()


class TipoActivo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)


class Posicion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)


class Responsable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    extension = db.Column(db.String(20), nullable=False, default="No aplica")
    num_empleado = db.Column(db.String(50), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False, default="No aplica")
    departamento = db.Column(db.String(100), nullable=False, default="No aplica")
    puesto = db.Column(db.String(100), nullable=False, default="No aplica")
    activos = db.relationship('Activo', backref='responsable', lazy=True)


class Activo(db.Model):
    # PK interna autoincremental — num_activo es solo un campo, puede repetirse "No aplica"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    num_activo = db.Column(db.String(100), nullable=False, default="No aplica")
    tipo_activo = db.Column(db.String(50), nullable=False)
    marca = db.Column(db.String(50), default="No aplica")
    modelo = db.Column(db.String(50), default="No aplica")
    num_serie = db.Column(db.String(100), default="No aplica")
    accesorio = db.Column(db.String(100), default="No aplica")
    clasificacion = db.Column(db.String(50), default="No aplica")
    posicion = db.Column(db.String(50), default="No aplica")
    responsable_id = db.Column(db.Integer, db.ForeignKey('responsable.id'), nullable=True)
    detalles = db.relationship('DetalleComputo', backref='activo', uselist=False,
                               cascade="all, delete-orphan")


class DetalleComputo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    activo_id = db.Column(db.Integer, db.ForeignKey('activo.id'), nullable=False)
    procesador = db.Column(db.String(50), default="No aplica")
    ipv4 = db.Column(db.String(15), default="No aplica")
    mac_address = db.Column(db.String(17), default="No aplica")
    ram = db.Column(db.String(20), default="No aplica")
    tipo_almacenamiento = db.Column(db.String(20), default="No aplica")
    capacidad = db.Column(db.String(20), default="No aplica")
    nombre_maquina = db.Column(db.String(50), default="No aplica")
    sistema_operativo = db.Column(db.String(50), default="No aplica")
    office = db.Column(db.String(50), default="No aplica")
    antivirus = db.Column(db.String(50), default="No aplica")
    lector_pdf = db.Column(db.String(50), default="No aplica")
    navegadores = db.Column(db.String(100), default="No aplica")
    compresor = db.Column(db.String(50), default="No aplica")
    videoconferencia = db.Column(db.String(50), default="No aplica")
    software_impresora = db.Column(db.String(50), default="No aplica")
    dominio = db.Column(db.String(50), default="No aplica")
    vpn = db.Column(db.String(50), default="No aplica")
    helpdesk_system = db.Column(os.getenv('COL_HELPDESK_SYSTEM', 'helpdesk_system'), db.String(50), default="No aplica")
    system_a = db.Column(os.getenv('COL_SYSTEM_A', 'system_a'), db.String(50), default="No aplica")
    system_b = db.Column(os.getenv('COL_SYSTEM_B', 'system_b'), db.String(50), default="No aplica")
    system_c = db.Column(os.getenv('COL_SYSTEM_C', 'system_c'), db.String(50), default="No aplica")
    messaging_system = db.Column(os.getenv('COL_MESSAGING_SYSTEM', 'messaging_system'), db.String(50), default="No aplica")
    erp_system = db.Column(os.getenv('COL_ERP_SYSTEM', 'erp_system'), db.String(50), default="No aplica")
    learning_platform = db.Column(os.getenv('COL_LEARNING_PLATFORM', 'learning_platform'), db.String(50), default="No aplica")
    quality_system = db.Column(os.getenv('COL_QUALITY_SYSTEM', 'quality_system'), db.String(50), default="No aplica")
    internal_database = db.Column(os.getenv('COL_INTERNAL_DATABASE', 'internal_database'), db.String(50), default="No aplica")
    usuario_ad = db.Column(db.String(50), default="No aplica")
    usuario_correo = db.Column(db.String(100), default="No aplica")

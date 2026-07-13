"""Funciones auxiliares: creación de tipos/posiciones/responsables, orden y filtros."""
import uuid
from flask import request
from .models import db, TipoActivo, Posicion, Responsable

FIELD_LIMITS = {
    'extension': 20,
    'num_empleado': 50,
    'nombre': 100,
    'departamento': 100,
    'puesto': 100,
    'num_activo': 100,
    'tipo_activo': 50,
    'marca': 50,
    'modelo': 50,
    'num_serie': 100,
    'accesorio': 100,
    'clasificacion': 50,
    'posicion': 50,
    'procesador': 50,
    'ipv4': 15,
    'mac_address': 17,
    'ram': 20,
    'tipo_almacenamiento': 20,
    'capacidad': 20,
    'nombre_maquina': 50,
    'sistema_operativo': 50,
    'office': 50,
    'antivirus': 50,
    'lector_pdf': 50,
    'navegadores': 100,
    'compresor': 50,
    'videoconferencia': 50,
    'software_impresora': 50,
    'dominio': 50,
    'vpn': 50,
    'usuario_ad': 50,
    'usuario_correo': 100,
    'helpdesk_system': 50,
    'system_a': 50,
    'system_b': 50,
    'system_c': 50,
    'messaging_system': 50,
    'erp_system': 50,
    'learning_platform': 50,
    'quality_system': 50,
    'internal_database': 50,
}


def limpiar_texto(valor, max_length, default='No aplica', lowercase=False):
    """Normaliza texto de formularios sin permitir controles ni tamaños excesivos."""
    if valor is None:
        return default
    texto = ''.join(ch for ch in str(valor).strip() if ch.isprintable())
    if lowercase:
        texto = texto.lower()
    if not texto:
        return default
    return texto[:max_length]


def valor_form(form, key, default='No aplica', lowercase=False):
    return limpiar_texto(form.get(key, ''), FIELD_LIMITS[key], default=default, lowercase=lowercase)


def valor_busqueda(valor, max_length=100):
    return limpiar_texto(valor, max_length, default='')


def obtener_o_crear_tipo(request_form):
    tipo_seleccionado = valor_form(request_form, 'tipo_activo', default='', lowercase=True)
    if not tipo_seleccionado or tipo_seleccionado == 'otro':
        nuevo_tipo = limpiar_texto(request_form.get('nuevo_tipo_texto', ''), FIELD_LIMITS['tipo_activo'], default='', lowercase=True)
        if nuevo_tipo:
            existe = TipoActivo.query.filter_by(nombre=nuevo_tipo).first()
            if not existe:
                db.session.add(TipoActivo(nombre=nuevo_tipo))
                db.session.commit()
            return nuevo_tipo
        return "no aplica"
    return tipo_seleccionado


def obtener_o_crear_posicion(request_form):
    """Devuelve el nombre de la posición seleccionada o creada. Si está vacía → 'No aplica'."""
    seleccionada = valor_form(request_form, 'posicion', default='')
    if seleccionada.lower() == 'otro':
        nueva = limpiar_texto(request_form.get('nueva_posicion_texto', ''), FIELD_LIMITS['posicion'], default='')
        if nueva and nueva.lower() != 'no aplica':
            existe = Posicion.query.filter(db.func.lower(Posicion.nombre) == nueva.lower()).first()
            if not existe:
                db.session.add(Posicion(nombre=nueva))
                db.session.commit()
                return nueva
            return existe.nombre
        return "No aplica"
    if not seleccionada or seleccionada.lower() == 'no aplica':
        return "No aplica"
    return seleccionada


def obtener_responsable(form):
    def limpio(key):
        v = valor_form(form, key, default='')
        return '' if v.lower() == 'no aplica' else v

    num_emp = limpio('num_empleado')
    nombre = limpio('nombre')
    extension = limpio('extension')
    departamento = limpio('departamento')
    puesto = limpio('puesto')

    if not num_emp and not nombre:
        return None

    if num_emp:
        existente = Responsable.query.filter_by(num_empleado=num_emp).first()
        if existente:
            return existente
        nuevo = Responsable(
            num_empleado=num_emp,
            nombre=nombre or "No aplica",
            extension=extension or "No aplica",
            departamento=departamento or "No aplica",
            puesto=puesto or "No aplica"
        )
        db.session.add(nuevo)
        db.session.commit()
        return nuevo

    existente = Responsable.query.filter(
        Responsable.nombre == nombre,
        ~Responsable.num_empleado.like('sin-emp-%')
    ).first()
    if existente:
        return existente

    nuevo = Responsable(
        num_empleado=f"sin-emp-{uuid.uuid4().hex[:8]}",
        nombre=nombre,
        extension=extension or "No aplica",
        departamento=departamento or "No aplica",
        puesto=puesto or "No aplica"
    )
    db.session.add(nuevo)
    db.session.commit()
    return nuevo


def detalles_desde_form(form):
    return dict(
        procesador=valor_form(form, 'procesador'),
        ipv4=valor_form(form, 'ipv4'),
        mac_address=valor_form(form, 'mac_address'),
        ram=valor_form(form, 'ram'),
        tipo_almacenamiento=valor_form(form, 'tipo_almacenamiento'),
        capacidad=valor_form(form, 'capacidad'),
        nombre_maquina=valor_form(form, 'nombre_maquina'),
        sistema_operativo=valor_form(form, 'sistema_operativo'),
        office=valor_form(form, 'office'),
        antivirus=valor_form(form, 'antivirus'),
        lector_pdf=valor_form(form, 'lector_pdf'),
        navegadores=valor_form(form, 'navegadores'),
        compresor=valor_form(form, 'compresor'),
        videoconferencia=valor_form(form, 'videoconferencia'),
        software_impresora=valor_form(form, 'software_impresora'),
        dominio=valor_form(form, 'dominio'),
        vpn=valor_form(form, 'vpn'),
        usuario_ad=valor_form(form, 'usuario_ad'),
        usuario_correo=valor_form(form, 'usuario_correo'),
        helpdesk_system=valor_form(form, 'helpdesk_system'),
        system_a=valor_form(form, 'system_a'),
        system_b=valor_form(form, 'system_b'),
        system_c=valor_form(form, 'system_c'),
        messaging_system=valor_form(form, 'messaging_system'),
        erp_system=valor_form(form, 'erp_system'),
        learning_platform=valor_form(form, 'learning_platform'),
        quality_system=valor_form(form, 'quality_system'),
        internal_database=valor_form(form, 'internal_database'),
    )


def ordenar_activos(activos):
    """Ordena por num_empleado ascendente (numérico), después por tipo de activo.
    Los activos sin responsable real van al final."""
    def orden_key(a):
        if a.responsable is None or a.responsable.num_empleado.startswith('sin-emp-'):
            return (2, 0, '', a.tipo_activo or '')
        num_emp_str = a.responsable.num_empleado
        try:
            num = int(num_emp_str)
            return (0, num, '', a.tipo_activo or '')
        except ValueError:
            return (1, 0, num_emp_str.upper(), a.tipo_activo or '')
    return sorted(activos, key=orden_key)


def filtros_actuales():
    """Recoge los filtros de la query string para propagarlos en redirects."""
    return {
        'buscar': valor_busqueda(request.args.get('buscar', ''), 100),
        'tipo_activo': valor_busqueda(request.args.get('tipo_activo', ''), FIELD_LIMITS['tipo_activo']),
        'posicion': valor_busqueda(request.args.get('posicion', ''), FIELD_LIMITS['posicion']),
    }


def filtros_desde_form():
    """Recoge los filtros de los hidden inputs del formulario (f_*)."""
    return {
        'buscar': valor_busqueda(request.form.get('f_buscar', ''), 100),
        'tipo_activo': valor_busqueda(request.form.get('f_tipo_activo', ''), FIELD_LIMITS['tipo_activo']),
        'posicion': valor_busqueda(request.form.get('f_posicion', ''), FIELD_LIMITS['posicion']),
    }

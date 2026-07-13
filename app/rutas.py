"""Rutas de la aplicación de inventario."""
from pathlib import Path

from flask import (abort, render_template, request, redirect, url_for, jsonify, send_file, current_app)
from sqlalchemy.orm import joinedload
from .models import db, TipoActivo, Posicion, Responsable, Activo, DetalleComputo
from . import helpers
from . import reportes_excel


def registrar_rutas(app):

    @app.route('/')
    def index():
        filtro_buscar = helpers.valor_busqueda(request.args.get('buscar', ''), 100)
        filtro_tipo = helpers.valor_busqueda(request.args.get('tipo_activo', ''), helpers.FIELD_LIMITS['tipo_activo'])
        filtro_posicion = helpers.valor_busqueda(request.args.get('posicion', ''), helpers.FIELD_LIMITS['posicion'])

        # outerjoin(Responsable) habilita filtrar por campos del responsable;
        # joinedload precarga responsable y detalles en la misma consulta para
        # evitar N+1 al renderizar la tabla y los modales de edición.
        query = Activo.query.outerjoin(Responsable).options(
            joinedload(Activo.responsable),
            joinedload(Activo.detalles),
        )

        if filtro_buscar:
            query = query.filter(
                (Responsable.num_empleado.like(f"%{filtro_buscar}%")) |
                (Responsable.nombre.like(f"%{filtro_buscar}%")) |
                (Activo.num_serie.like(f"%{filtro_buscar}%"))
            )
        if filtro_posicion:
            query = query.filter(Activo.posicion.like(f"%{filtro_posicion}%"))
        if filtro_tipo:
            query = query.filter(Activo.tipo_activo == filtro_tipo.lower())

        activos = helpers.ordenar_activos(query.all())
        tipos = TipoActivo.query.all()
        posiciones = Posicion.query.order_by(Posicion.nombre).all()
        return render_template('index.html', activos=activos, tipos=tipos, posiciones=posiciones,
                               buscar=filtro_buscar,
                               tipo_seleccionado=filtro_tipo,
                               filtro_posicion=filtro_posicion)

    @app.route('/nuevo_activo', methods=['GET', 'POST'])
    def nuevo_activo():
        if request.method == 'POST':
            tipo = helpers.obtener_o_crear_tipo(request.form)

            num_act = helpers.valor_form(request.form, 'num_activo')

            if num_act != "No aplica":
                existe = Activo.query.filter_by(num_activo=num_act).first()
                if existe:
                    tipos = TipoActivo.query.all()
                    posiciones = Posicion.query.order_by(Posicion.nombre).all()
                    return render_template('formulario.html', tipos=tipos, posiciones=posiciones,
                                           error_duplicado=True,
                                           num_activo_duplicado=num_act), 400

            responsable = helpers.obtener_responsable(request.form)

            nuevo_act = Activo(
                num_activo=num_act,
                tipo_activo=tipo,
                marca=helpers.valor_form(request.form, 'marca'),
                modelo=helpers.valor_form(request.form, 'modelo'),
                num_serie=helpers.valor_form(request.form, 'num_serie'),
                accesorio=helpers.valor_form(request.form, 'accesorio'),
                clasificacion=helpers.valor_form(request.form, 'clasificacion'),
                posicion=helpers.obtener_o_crear_posicion(request.form),
                responsable_id=responsable.id if responsable else None
            )
            db.session.add(nuevo_act)
            db.session.flush()

            det = DetalleComputo(activo_id=nuevo_act.id, **helpers.detalles_desde_form(request.form))
            db.session.add(det)
            db.session.commit()
            # Propagar filtros que venían en la query string del formulario
            redir = helpers.filtros_actuales()
            redir.update(creado='1', id=nuevo_act.id)
            return redirect(url_for('index', **redir))

        tipos = TipoActivo.query.all()
        posiciones = Posicion.query.order_by(Posicion.nombre).all()
        return render_template('formulario.html', tipos=tipos, posiciones=posiciones,
                               error_duplicado=False, num_activo_duplicado='')

    @app.route('/editar_activo/<int:activo_id>', methods=['POST'])
    def editar_activo(activo_id):
        activo = Activo.query.get_or_404(activo_id)

        responsable = helpers.obtener_responsable(request.form)
        activo.responsable_id = responsable.id if responsable else None

        nuevo_num_act = helpers.valor_form(request.form, 'num_activo')
        if nuevo_num_act != activo.num_activo and nuevo_num_act != "No aplica":
            existe = Activo.query.filter(
                Activo.num_activo == nuevo_num_act,
                Activo.id != activo_id
            ).first()
            if existe:
                nuevo_num_act = activo.num_activo

        activo.num_activo = nuevo_num_act
        activo.tipo_activo = helpers.obtener_o_crear_tipo(request.form)
        activo.marca = helpers.valor_form(request.form, 'marca')
        activo.modelo = helpers.valor_form(request.form, 'modelo')
        activo.num_serie = helpers.valor_form(request.form, 'num_serie')
        activo.accesorio = helpers.valor_form(request.form, 'accesorio')
        activo.clasificacion = helpers.valor_form(request.form, 'clasificacion')
        activo.posicion = helpers.obtener_o_crear_posicion(request.form)

        if not activo.detalles:
            activo.detalles = DetalleComputo(activo_id=activo.id)

        for campo, valor in helpers.detalles_desde_form(request.form).items():
            setattr(activo.detalles, campo, valor)

        db.session.commit()
        # Propagar filtros que venían en hidden inputs del form
        redir = helpers.filtros_desde_form()
        redir.update(modificado='1', id=activo.id)
        return redirect(url_for('index', **redir))

    @app.route('/eliminar_activo/<int:activo_id>', methods=['POST'])
    def eliminar_activo(activo_id):
        activo = Activo.query.get_or_404(activo_id)
        db.session.delete(activo)
        db.session.commit()
        redir = helpers.filtros_desde_form()
        redir.update(eliminado='1')
        return redirect(url_for('index', **redir))

    @app.route('/api/responsable/buscar')
    def buscar_responsable_api():
        num_empleado = helpers.valor_busqueda(request.args.get('num_empleado', ''), helpers.FIELD_LIMITS['num_empleado'])
        nombre = helpers.valor_busqueda(request.args.get('nombre', ''), helpers.FIELD_LIMITS['nombre'])
        responsable = None
        if num_empleado:
            responsable = Responsable.query.filter_by(num_empleado=num_empleado).first()
        elif nombre:
            responsable = Responsable.query.filter(
                Responsable.nombre == nombre,
                ~Responsable.num_empleado.like('sin-emp-%')
            ).first()
        if responsable:
            return jsonify({
                'existe': True,
                'num_empleado': 'No aplica' if responsable.num_empleado.startswith('sin-emp-') else responsable.num_empleado,
                'nombre': responsable.nombre,
                'extension': responsable.extension,
                'departamento': responsable.departamento,
                'puesto': responsable.puesto
            })
        return jsonify({'existe': False})

    @app.route('/api/activo/verificar')
    def verificar_num_activo():
        num_activo = helpers.valor_busqueda(request.args.get('num_activo', ''), helpers.FIELD_LIMITS['num_activo'])
        if not num_activo or num_activo.lower() == 'no aplica':
            return jsonify({'existe': False})
        existe = Activo.query.filter_by(num_activo=num_activo).first()
        return jsonify({'existe': bool(existe)})

    @app.route('/reporte', methods=['GET'])
    def reporte_form():
        tipos = TipoActivo.query.all()
        posiciones = Posicion.query.order_by(Posicion.nombre).all()
        responsables = Responsable.query.filter(
            ~Responsable.num_empleado.like('sin-emp-%')
        ).order_by(Responsable.nombre).all()
        return render_template('reportes.html',
                               tipos=tipos,
                               posiciones=posiciones,
                               responsables=responsables)

    @app.route('/reporte/generar', methods=['POST'])
    def reporte_generar():
        filtro_tipo = helpers.valor_busqueda(request.form.get('tipo_activo', ''), helpers.FIELD_LIMITS['tipo_activo'])
        filtro_responsable = helpers.valor_busqueda(request.form.get('responsable', ''), helpers.FIELD_LIMITS['num_empleado'])
        filtro_posicion = helpers.valor_busqueda(request.form.get('posicion', ''), helpers.FIELD_LIMITS['posicion'])

        # Precarga responsable y detalles: el generador de Excel recorre ambos
        # por cada fila, así se evita una consulta por activo (N+1).
        query = Activo.query.outerjoin(Responsable).options(
            joinedload(Activo.responsable),
            joinedload(Activo.detalles),
        )

        if filtro_responsable:
            query = query.filter(Responsable.num_empleado == filtro_responsable)
        if filtro_tipo:
            query = query.filter(Activo.tipo_activo == filtro_tipo.lower())
        if filtro_posicion:
            query = query.filter(Activo.posicion == filtro_posicion)

        activos = helpers.ordenar_activos(query.all())

        if not activos:
            return jsonify({'error': 'sin_datos'}), 204

        ruta_plantilla = _resolver_plantilla_reporte(current_app.config['REPORT_TEMPLATE_PATH'])
        archivo = reportes_excel.generar_reporte(
            activos,
            ruta_plantilla,
            current_app.config['REPORT_SHEET_NAME']
        )
        return send_file(archivo, as_attachment=True,
                         download_name=reportes_excel.nombre_archivo(),
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _resolver_plantilla_reporte(ruta_configurada):
    """Resuelve y valida la plantilla Excel configurada para reportes."""
    base_proyecto = Path(current_app.root_path).parent.resolve()
    ruta = Path(ruta_configurada)
    if not ruta.is_absolute():
        ruta = base_proyecto / ruta
    ruta = ruta.resolve()

    if base_proyecto not in ruta.parents and ruta != base_proyecto:
        abort(400, description='La plantilla de reporte debe estar dentro del proyecto.')
    if ruta.suffix.lower() != '.xlsx':
        abort(400, description='La plantilla de reporte debe ser un archivo .xlsx.')
    if not ruta.is_file():
        abort(500, description='No se encontró la plantilla de reporte configurada.')

    return str(ruta)

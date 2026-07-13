"""Corrige referencias de clave foránea colgantes en inventario.db.

Contexto: una migración manual antigua renombró las tablas `activo` y
`responsable` a `activo_temp` / `responsable_temp` durante el proceso y,
aunque las tablas quedaron con su nombre final, las claves foráneas de
`detalle_computo.activo_id` y `activo.responsable_id` se quedaron apuntando
a los nombres temporales (que ya no existen). Como la app activa
`PRAGMA foreign_keys=ON` en cada conexión, esto rompía crear/editar/eliminar
activos con el error "no such table: main.activo_temp" (o
"...responsable_temp").

Este script es idempotente: si el esquema ya está correcto, no hace nada.
Antes de modificar la base de datos crea un respaldo con timestamp junto al
archivo original.

Uso:
    python scripts/fix_dangling_fk_references.py [ruta_a_inventario.db]

Si no se indica ruta, usa instance/inventario.db relativo a la raíz del
proyecto.
"""
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DANGLING_REFS = {
    'detalle_computo': ('activo_id', '"activo_temp"(id)', 'activo(id)'),
    'activo': ('responsable_id', '"responsable_temp"(id)', 'responsable(id)'),
}


def _tiene_referencia_colgante(cur, tabla, fragmento_roto):
    cur.execute('SELECT sql FROM sqlite_master WHERE name=?', (tabla,))
    row = cur.fetchone()
    return row is not None and fragmento_roto in row[0]


def _reconstruir_tabla_activo(cur):
    cur.execute('''CREATE TABLE activo_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_activo VARCHAR(100) NOT NULL DEFAULT "No aplica",
        tipo_activo VARCHAR(50) NOT NULL,
        marca VARCHAR(50) DEFAULT "No aplica",
        modelo VARCHAR(50) DEFAULT "No aplica",
        num_serie VARCHAR(100) DEFAULT "No aplica",
        accesorio VARCHAR(100) DEFAULT "No aplica",
        clasificacion VARCHAR(50) DEFAULT "No aplica",
        responsable_id INTEGER REFERENCES responsable(id),
        posicion VARCHAR(50) DEFAULT "No aplica"
    )''')
    cur.execute('''INSERT INTO activo_new
        SELECT id, num_activo, tipo_activo, marca, modelo, num_serie,
               accesorio, clasificacion, responsable_id, posicion
        FROM activo''')
    cur.execute('DROP TABLE activo')
    cur.execute('ALTER TABLE activo_new RENAME TO activo')


def _reconstruir_tabla_detalle_computo(cur):
    cur.execute('SELECT sql FROM sqlite_master WHERE name="detalle_computo"')
    old_sql = cur.fetchone()[0]
    new_sql = (
        old_sql
        .replace('CREATE TABLE detalle_computo', 'CREATE TABLE detalle_computo_new')
        .replace('REFERENCES "activo_temp"(id)', 'REFERENCES activo(id)')
    )
    cur.execute(new_sql)
    cur.execute('PRAGMA table_info(detalle_computo)')
    columnas = [r[1] for r in cur.fetchall()]
    lista_cols = ', '.join(columnas)
    cur.execute(
        f'INSERT INTO detalle_computo_new ({lista_cols}) '
        f'SELECT {lista_cols} FROM detalle_computo'
    )
    cur.execute('DROP TABLE detalle_computo')
    cur.execute('ALTER TABLE detalle_computo_new RENAME TO detalle_computo')


def corregir(ruta_db: Path) -> bool:
    """Aplica la corrección si hace falta. Devuelve True si modificó algo."""
    con = sqlite3.connect(str(ruta_db), timeout=10)
    con.execute('PRAGMA busy_timeout=10000')
    try:
        cur = con.cursor()
        necesita_activo = _tiene_referencia_colgante(cur, 'activo', '"responsable_temp"(id)')
        necesita_detalle = _tiene_referencia_colgante(cur, 'detalle_computo', '"activo_temp"(id)')

        if not necesita_activo and not necesita_detalle:
            print('El esquema ya está correcto, no hay nada que corregir.')
            return False

        respaldo = ruta_db.with_name(
            f'{ruta_db.stem}_backup_pre_fix_{datetime.now():%Y%m%d_%H%M%S}{ruta_db.suffix}'
        )
        shutil.copy2(ruta_db, respaldo)
        print(f'Respaldo creado en: {respaldo}')

        con.execute('PRAGMA foreign_keys=OFF')
        cur.execute('BEGIN IMMEDIATE')
        if necesita_activo:
            _reconstruir_tabla_activo(cur)
            print('Tabla "activo" reconstruida (responsable_temp -> responsable).')
        if necesita_detalle:
            _reconstruir_tabla_detalle_computo(cur)
            print('Tabla "detalle_computo" reconstruida (activo_temp -> activo).')
        con.commit()

        con.execute('PRAGMA foreign_keys=ON')
        cur.execute('PRAGMA foreign_key_check')
        violaciones = cur.fetchall()
        cur.execute('PRAGMA integrity_check')
        integridad = cur.fetchone()[0]
        print(f'PRAGMA integrity_check: {integridad}')
        if violaciones:
            print(f'AVISO: quedaron {len(violaciones)} violaciones de FK preexistentes '
                  f'(datos huérfanos, no relacionadas con este fix): {violaciones}')
        else:
            print('PRAGMA foreign_key_check: sin violaciones.')
        return True
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def main():
    if len(sys.argv) > 1:
        ruta_db = Path(sys.argv[1])
    else:
        ruta_db = Path(__file__).resolve().parent.parent / 'instance' / 'inventario.db'

    if not ruta_db.is_file():
        print(f'No se encontró la base de datos en: {ruta_db}')
        sys.exit(1)

    corregir(ruta_db)


if __name__ == '__main__':
    main()

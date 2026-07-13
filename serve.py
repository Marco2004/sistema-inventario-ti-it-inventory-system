"""Servidor WSGI para red interna. Ejecuta: python serve.py"""

from waitress import serve

from app import crear_app

app = crear_app()


if __name__ == '__main__':
    serve(
        app,
        host=app.config['SERVER_HOST'],
        port=app.config['SERVER_PORT'],
        threads=8,
    )

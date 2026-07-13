"""Punto de entrada. Ejecuta:  python run.py"""
import os

from app import crear_app

app = crear_app()

if __name__ == '__main__':
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host=app.config['SERVER_HOST'], port=app.config['SERVER_PORT'], debug=debug)

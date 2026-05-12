"""
WSGI entry point for Gunicorn
"""
from backend import app

if __name__ == "__main__":
    app.run()

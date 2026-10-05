"""Configuración de Lately Café.

Desarrollo por defecto. Para producción (HTTPS) exportar:
    DJANGO_PRODUCCION=1  DJANGO_SECRET_KEY=...  DJANGO_ALLOWED_HOSTS=midominio.com
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PRODUCCION = os.environ.get("DJANGO_PRODUCCION") == "1"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-insecure-cambiar-en-produccion")
if PRODUCCION and SECRET_KEY.startswith("dev-insecure"):
    raise RuntimeError("Definí DJANGO_SECRET_KEY para correr en producción.")

DEBUG = not PRODUCCION
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "usuarios",
    "menu",
    "carrito",
    "pedidos",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "carrito.context_processors.contador_carrito",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ---------- Usuarios y contraseñas ----------
AUTH_USER_MODEL = "usuarios.Usuario"
AUTHENTICATION_BACKENDS = [
    "usuarios.backends.EmailOUsernameBackend",
]
# Hasher por defecto de Django: PBKDF2-SHA256 (contraseñas nunca en texto plano).
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "menu:listado"
LOGOUT_REDIRECT_URL = "menu:listado"

# Recuperación de contraseña: el email se imprime en la consola por ahora.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Lately Café <no-reply@lately.cafe>"

# ---------- HTTPS-ready ----------
SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
if PRODUCCION:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # detrás de un proxy TLS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# ---------- Internacionalización / estáticos ----------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Montevideo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

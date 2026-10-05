# CLAUDE.md

Lately Café: plataforma web para una cafetería de especialidad. Django 5.1+ con SQLite. El README tiene
las reglas de negocio completas (estados de pedido y pago, supuestos de cancelación); léelo antes de tocar `pedidos`.

## Comandos

```bash
source .venv/bin/activate
python manage.py runserver
python manage.py migrate
python manage.py makemigrations
python manage.py test                 # todos los tests
python manage.py test pedidos         # una app
python manage.py test pedidos.tests.NombreDeClase.test_algo
```

## Arquitectura

- `config/`: settings, urls raíz y `reglas.py` (`ReglaDeNegocioError`, `PermisoError` y el helper `ejecutar`).
- `usuarios`: `Usuario` (AUTH_USER_MODEL, rol CLIENTE|ADMIN), `Direccion`, autenticación y `permisos.py`.
- `menu`: `Producto`, menú público y panel ADMIN de productos.
- `carrito`: `Carrito` / `ItemCarrito` (solo CLIENTE).
- `pedidos`: `Local`, `Configuracion`, `Pedido`, `ItemPedido`, `Pago`; checkout, historial y panel ADMIN.
- `templates/` (base, form_simple, registration) y `static/estilos.css` son globales; cada app tiene además sus propios `templates/`.

## Convenciones

- Todo el código, nombres, mensajes y UI están en **español** (`LANGUAGE_CODE = "es"`, zona `America/Montevideo`). Mantenlo así.
- Las reglas de negocio lanzan `ReglaDeNegocioError` (o `PermisoError`); las vistas las ejecutan con `config.reglas.ejecutar(request, accion, exito=...)`, que convierte el error en un mensaje al usuario.
- Permisos por rol con `usuarios.permisos`: `rol_requerido(Rol.X)` para vistas de función, `SoloAdminMixin` / `SoloClienteMixin` para vistas de clase. Anónimo → login, otro rol → 403.
- El registro público siempre crea CLIENTE; solo un ADMIN cambia roles. El superusuario se crea con rol ADMIN.
- Estado del pedido y estado del pago son independientes: ninguno cambia al otro automáticamente. Las transiciones del ADMIN solo avanzan al siguiente estado, sin saltos.
- El pedido guarda una copia del texto de la dirección de entrega (la `Direccion` puede borrarse).
- Cada app tiene su `tests.py`; agrega tests al cambiar reglas de negocio.

## Configuración y seguridad

- `DJANGO_PRODUCCION=1` activa HTTPS, cookies seguras, HSTS y `DEBUG=False`; requiere `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS`.
- El email de recuperación de contraseña se imprime en consola (`EmailBackend` de consola).
- `db.sqlite3`, `.venv/` y `staticfiles/` están en `.gitignore`; no los subas.
- `/django-admin/` es el admin técnico de Django; el panel de negocio vive en `/panel/`.

## Skills

- `.claude/skills/ui-ux-pro-max`: usarla para trabajo de UI/UX (templates, `static/estilos.css`, diseño y accesibilidad). Requiere Python 3 para su script de búsqueda.

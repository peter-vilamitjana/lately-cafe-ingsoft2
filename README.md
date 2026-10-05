# Lately Café

Plataforma web para una cafetería de especialidad. Django + SQLite, arquitectura MVC
(modelo = `models.py`, vista/controlador = `views.py`, template = `templates/`).

## Cómo correrlo

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser      # el superusuario se crea con rol ADMIN
python manage.py runserver
```

- Menú público: http://localhost:8000/
- Panel de productos (solo ADMIN): http://localhost:8000/panel/productos/
- Registro / login / cambio y recuperación de contraseña: `/cuentas/...`
  (el email de recuperación se imprime en la consola del servidor).
- Tests: `python manage.py test`

### Primeros pasos para probar el flujo
1. Entrá a `/django-admin/` con el superusuario y cargá al menos un **Local** (nombre, dirección, horarios).
2. En `/panel/productos/` cargá productos; en `/panel/configuracion/` ajustá el monto mínimo de delivery y el alias de transferencia.
3. Registrá un cliente: cargá una dirección (`/cuentas/direcciones/`), agregá productos desde el menú, andá a Carrito → Hacer el pedido.
4. Como ADMIN, en `/panel/pedidos/` aceptá o rechazá el pago y avanzá el estado del pedido.

## Datos de demo

```bash
python manage.py cargar_demo --password-admin '<clave-admin>' --password-cliente '<clave-cliente>'
```

Es idempotente (se puede correr varias veces sin duplicar; las contraseñas solo se usan al crear cada usuario).
Carga 2 locales, 8 productos (Flat White y Brownie quedan "No disponible"), 2 usuarios y una dirección del cliente.

**Imágenes de demo:** cada producto toma `static/demo/<nombre-en-slug>.jpg` (ej. `espresso.jpg`, `te-chai.jpg`,
`jugo-de-naranja.jpg`); si no existe, usa la de su categoría (`cafe.jpg`, `te.jpg`, `pasteleria.jpg`, `otro.jpg`).
Solo se asigna a productos sin imagen: para reemplazar una ya cargada, quitala desde `/panel/productos/` y volvé a correr el comando.

| Usuario | Email | Contraseña de demo | Rol |
|---|---|---|---|
| `admin_demo` | admin@demo.com | `LatelyAdmin#2026` | ADMIN (accede a `/panel/`) |
| `cliente_demo` | cliente@demo.com | `LatelyCliente#2026` | CLIENTE |

Las contraseñas viven solo acá, no en el código. **No usar estos datos en producción.**

**Valores provisorios (a validar con el negocio):** el monto mínimo de delivery (`500`) y el alias de
transferencia (`lately.cafe`) son provisorios; el comando no los modifica.

## Estructura

| App | Contenido |
|---|---|
| `usuarios` | `Usuario` (rol CLIENTE\|ADMIN), `Direccion`, registro y autenticación |
| `menu` | `Producto`, menú público, panel ADMIN |
| `carrito` | `Carrito`, `ItemCarrito` (solo CLIENTE; no admite productos no disponibles) |
| `pedidos` | `Local`, `Configuracion`, `Pedido`, `ItemPedido`, `Pago`; checkout, historial y panel ADMIN |

## Seguridad

- Contraseñas con PBKDF2-SHA256 (hasher por defecto de Django) y validadores de contraseña.
- El registro público siempre crea CLIENTE; el rol solo lo cambia un ADMIN.
- Permisos por rol: el panel exige ADMIN (anónimo → login, cliente → 403).
- HTTPS-ready: con `DJANGO_PRODUCCION=1` se activan redirección a HTTPS, cookies seguras,
  HSTS y `DEBUG=False`. Requiere `DJANGO_SECRET_KEY` y `DJANGO_ALLOWED_HOSTS`.
  Detrás de un proxy TLS, este debe enviar `X-Forwarded-Proto: https`.

## Estados (separados entre sí)

**Pedido:** `PENDIENTE → EN_PREPARACION → LISTO → ENTREGADO` (retiro) o
`LISTO → EN_CAMINO → ENTREGADO` (delivery; `EN_CAMINO` no existe en retiro). `CANCELADO` es terminal.

**Pago:** `PENDIENTE | ACEPTADO | RECHAZADO` (+ motivo). Nace `PENDIENTE` al confirmar el pedido.
Un rechazo se reintenta (vuelve a `PENDIENTE`, se limpia el motivo) y recién ahí se puede cambiar el método.
Ningún estado cambia al otro automáticamente.

## Supuestos a validar con el negocio

- **Cancelación (quién y cuándo):** el cliente solo cancela en `PENDIENTE`. El ADMIN cancela en
  `PENDIENTE` o `EN_PREPARACION`. Desde `LISTO`, `EN_CAMINO`, `ENTREGADO` y `CANCELADO` no se cancela.
- **Pago aceptado y pedido cancelado:** el pago queda como está (`ACEPTADO`). El reintegro del dinero se
  gestiona fuera del sistema. Un pedido cancelado no admite aceptar, rechazar, reintentar ni cambiar método de pago.
- **Orden de transiciones:** el ADMIN solo puede avanzar al siguiente estado en el orden de arriba (sin saltos
  ni retrocesos). Un pedido en `EN_PREPARACION` puede tener el pago `PENDIENTE` (típico del pago en el local).
- **Pago en el local:** el ADMIN puede aceptar el pago de un pedido `ENTREGADO`.
- **Monto mínimo de delivery:** se compara contra el total de los productos; no hay costo de envío.
- **Dirección borrada:** el pedido conserva una copia del texto de la dirección de entrega.

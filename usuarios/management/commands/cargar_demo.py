from decimal import Decimal

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from menu.models import Categoria, Producto
from pedidos.models import Configuracion, Local
from usuarios.models import Direccion, Rol, Usuario

LOCALES = [
    ("Lately Café Centro", "Av. Corrientes 1234, CABA", "Lun-Vie 8-19, Sáb 9-14"),
    ("Lately Café Palermo", "Honduras 5678, CABA", "Lun-Dom 8-20"),
]

# (nombre, categoría, precio, disponible)
PRODUCTOS = [
    ("Espresso", Categoria.CAFE, 1800, True),
    ("Capuchino", Categoria.CAFE, 2800, True),
    ("Flat White", Categoria.CAFE, 3000, False),
    ("Té Chai", Categoria.TE, 2500, True),
    ("Medialuna", Categoria.PASTELERIA, 900, True),
    ("Cheesecake", Categoria.PASTELERIA, 4200, True),
    ("Brownie", Categoria.PASTELERIA, 2600, False),
    ("Jugo de naranja", Categoria.OTRO, 2200, True),
]

# Imágenes de demo locales en static/demo/: <slug-del-producto>.jpg (ej. te-chai.jpg);
# si no existe, se usa la de la categoría (cafe.jpg, te.jpg, pasteleria.jpg, otro.jpg).
IMAGENES_DEMO = settings.BASE_DIR / "static" / "demo"

# (email, username, rol)
USUARIOS = [
    ("admin@demo.com", "admin_demo", Rol.ADMIN),
    ("cliente@demo.com", "cliente_demo", Rol.CLIENTE),
]


def _imagen_demo(nombre, categoria):
    """Foto propia del producto si existe; si no, la de su categoría; si no, None."""
    for base in (slugify(nombre), categoria.lower()):
        ruta = IMAGENES_DEMO / f"{base}.jpg"
        if ruta.exists():
            return ruta
    return None


class Command(BaseCommand):
    help = "Carga datos de demo (locales, productos, usuarios, dirección). Es idempotente."

    def add_arguments(self, parser):
        parser.add_argument("--password-admin", help="Contraseña de admin@demo.com (solo si se crea).")
        parser.add_argument("--password-cliente", help="Contraseña de cliente@demo.com (solo si se crea).")

    def handle(self, *args, **opciones):
        claves = {Rol.ADMIN: opciones["password_admin"], Rol.CLIENTE: opciones["password_cliente"]}
        faltan = [email for email, _, rol in USUARIOS
                  if not claves[rol] and not Usuario.objects.filter(email=email).exists()]
        if faltan:
            raise CommandError(
                "Faltan contraseñas para crear: " + ", ".join(faltan)
                + ". Usá --password-admin y --password-cliente (ver README, 'Datos de demo').")

        resumen = {}

        def contar(nombre, creado):
            c = resumen.setdefault(nombre, [0, 0])
            c[0 if creado else 1] += 1

        for nombre, direccion, horarios in LOCALES:
            _, creado = Local.objects.update_or_create(
                nombre=nombre, defaults={"direccion": direccion, "horarios": horarios})
            contar("locales", creado)

        for nombre, categoria, precio, disponible in PRODUCTOS:
            producto, creado = Producto.objects.update_or_create(
                nombre=nombre,
                defaults={"categoria": categoria, "precio": Decimal(precio), "disponible": disponible})
            contar("productos", creado)
            origen = _imagen_demo(nombre, categoria)
            if not producto.imagen and origen:  # no pisa imágenes cargadas por el ADMIN
                with origen.open("rb") as archivo:
                    producto.imagen.save(f"{slugify(nombre)}.jpg", File(archivo))

        usuarios = {}
        for email, username, rol in USUARIOS:
            usuario, creado = Usuario.objects.get_or_create(
                email=email, defaults={"username": username, "rol": rol})
            if creado:
                usuario.set_password(claves[rol])
                usuario.save(update_fields=["password"])
            elif usuario.rol != rol:
                usuario.rol = rol
                usuario.save(update_fields=["rol"])
            usuarios[rol] = usuario
            contar("usuarios", creado)

        _, creado = Direccion.objects.get_or_create(
            usuario=usuarios[Rol.CLIENTE], calle="Calle Falsa 123", ciudad="Springfield")
        contar("direcciones", creado)

        # Configuración: se respetan los valores existentes (o los provisorios por defecto).
        creada = not Configuracion.objects.filter(pk=1).exists()
        Configuracion.obtener()
        contar("configuración", creada)

        self.stdout.write("Resumen de carga demo (creados / ya existían):")
        for nombre, (creados, existentes) in resumen.items():
            self.stdout.write(f"  {nombre}: {creados} / {existentes}")

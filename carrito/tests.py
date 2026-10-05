from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from config.reglas import PermisoError, ReglaDeNegocioError
from menu.models import Producto
from usuarios.models import Rol, Usuario

from .models import Carrito


class CarritoTests(TestCase):
    def setUp(self):
        self.ana = Usuario.objects.create_user("ana", "ana@x.com", "pw-segura-123")
        self.cafe = Producto.objects.create(nombre="Espresso", precio=Decimal(100))
        self.agotado = Producto.objects.create(nombre="Budín", precio=Decimal(80), disponible=False)

    def test_no_admite_productos_no_disponibles(self):
        carrito = Carrito.de(self.ana)
        with self.assertRaises(ReglaDeNegocioError):
            carrito.agregar(self.agotado)
        self.client.force_login(self.ana)
        self.client.post(reverse("carrito:agregar", args=[self.agotado.pk]), {"cantidad": 1})
        self.assertFalse(carrito.items.exists())

    def test_agregar_modificar_y_quitar(self):
        carrito = Carrito.de(self.ana)
        carrito.agregar(self.cafe, 2)
        carrito.agregar(self.cafe, 1)  # suma sobre el mismo ítem
        self.assertEqual(carrito.items.get().cantidad, 3)
        carrito.modificar_cantidad(self.cafe, 5)
        self.assertEqual(carrito.total, Decimal(500))
        with self.assertRaises(ReglaDeNegocioError):
            carrito.modificar_cantidad(self.cafe, 0)
        carrito.quitar(self.cafe)
        self.assertFalse(carrito.items.exists())

    def test_solo_cliente_tiene_carrito(self):
        admin = Usuario.objects.create_user("admin", "a@x.com", "pw-segura-123", rol=Rol.ADMIN)
        with self.assertRaises(PermisoError):
            Carrito.de(admin)
        self.client.force_login(admin)
        self.assertEqual(self.client.get(reverse("carrito:ver")).status_code, 403)
        self.assertEqual(self.client.post(reverse("carrito:agregar", args=[self.cafe.pk])).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("carrito:ver")).status_code, 302)

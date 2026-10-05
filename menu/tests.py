from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from usuarios.models import Rol, Usuario

from .models import Categoria, Producto

DATOS = {"nombre": "Nuevo", "descripcion": "", "precio": "100", "categoria": Categoria.CAFE, "disponible": "on"}


class SoloAdminGestionaProductos(TestCase):
    """Regla: solo ADMIN crea, edita, elimina y cambia disponibilidad."""

    def setUp(self):
        self.producto = Producto.objects.create(nombre="Espresso", precio=Decimal(120))
        self.admin = Usuario.objects.create_user("admin", "a@x.com", "pw-segura-123", rol=Rol.ADMIN)
        self.cliente = Usuario.objects.create_user("ana", "ana@x.com", "pw-segura-123")
        pk = self.producto.pk
        self.acciones = [
            ("menu:panel", {}, "get"),
            ("menu:crear", {}, "post"),
            ("menu:editar", {"pk": pk}, "post"),
            ("menu:eliminar", {"pk": pk}, "post"),
            ("menu:disponibilidad", {"pk": pk}, "post"),
        ]

    def _ejecutar(self, nombre, kwargs, metodo):
        url = reverse(nombre, kwargs=kwargs)
        return self.client.get(url) if metodo == "get" else self.client.post(url, DATOS)

    def test_anonimo_es_redirigido_al_login(self):
        for nombre, kwargs, metodo in self.acciones:
            with self.subTest(nombre):
                self.assertEqual(self._ejecutar(nombre, kwargs, metodo).status_code, 302)
        self.assertEqual(Producto.objects.count(), 1)
        self.assertTrue(Producto.objects.get().disponible)

    def test_cliente_recibe_403_y_no_modifica_nada(self):
        self.client.force_login(self.cliente)
        for nombre, kwargs, metodo in self.acciones:
            with self.subTest(nombre):
                self.assertEqual(self._ejecutar(nombre, kwargs, metodo).status_code, 403)
        self.producto.refresh_from_db()
        self.assertEqual((Producto.objects.count(), self.producto.nombre, self.producto.disponible),
                         (1, "Espresso", True))

    def test_admin_crea_edita_cambia_disponibilidad_y_elimina(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("menu:crear"), DATOS)
        self.assertTrue(Producto.objects.filter(nombre="Nuevo").exists())

        self.client.post(reverse("menu:editar", kwargs={"pk": self.producto.pk}), {**DATOS, "nombre": "Doble"})
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, "Doble")

        self.client.post(reverse("menu:disponibilidad", kwargs={"pk": self.producto.pk}))
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.disponible)

        self.client.post(reverse("menu:eliminar", kwargs={"pk": self.producto.pk}))
        self.assertFalse(Producto.objects.filter(pk=self.producto.pk).exists())


class MenuPublico(TestCase):
    def setUp(self):
        Producto.objects.create(nombre="Espresso", precio=1, categoria=Categoria.CAFE)
        Producto.objects.create(nombre="Té verde", precio=1, categoria=Categoria.TE)
        Producto.objects.create(nombre="Croissant", precio=1, categoria=Categoria.PASTELERIA, disponible=False)

    def nombres(self, **params):
        respuesta = self.client.get(reverse("menu:listado"), params)
        self.assertEqual(respuesta.status_code, 200)  # público: sin login
        return {p.nombre for p in respuesta.context["productos"]}

    def test_filtro_por_categoria(self):
        self.assertEqual(self.nombres(categoria=Categoria.TE), {"Té verde"})
        self.assertEqual(len(self.nombres()), 3)

    def test_busqueda_por_nombre(self):
        self.assertEqual(self.nombres(q="espre"), {"Espresso"})
        self.assertEqual(self.nombres(q="inexistente"), set())

    def test_productos_no_disponibles_se_muestran_marcados(self):
        self.assertContains(self.client.get(reverse("menu:listado")), "No disponible", count=1)

    def test_filtro_arranca_en_todas_las_categorias(self):
        respuesta = self.client.get(reverse("menu:listado"))
        # Las categorías son chips; "Todas" arranca activa.
        self.assertContains(respuesta, 'Todas las categorías')
        self.assertContains(respuesta, 'class="chip activo" href="?" aria-current="true">Todas las categorías')

    def test_portada_en_raiz(self):
        # Visitante anónimo
        r = self.client.get(reverse("portada"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Lately Café")
        self.assertContains(r, reverse("menu:listado"))
        self.assertContains(r, reverse("registro"))

        # Usuario autenticado
        user = Usuario.objects.create_user("testuser", "test@x.com", "pw-123")
        self.client.force_login(user)
        r_auth = self.client.get(reverse("portada"))
        self.assertContains(r_auth, "Mi cuenta")


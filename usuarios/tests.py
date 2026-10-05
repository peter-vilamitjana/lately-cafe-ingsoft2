from django.test import TestCase
from django.urls import reverse

from .models import Rol, Usuario


class Cuentas(TestCase):
    def test_registro_crea_cliente_con_contrasena_hasheada(self):
        self.client.post(reverse("registro"), {
            "username": "ana", "email": "ana@x.com",
            "password1": "clave-muy-segura-9", "password2": "clave-muy-segura-9",
            "rol": Rol.ADMIN,  # un intento de escalar el rol se ignora
        })
        usuario = Usuario.objects.get(username="ana")
        self.assertEqual(usuario.rol, Rol.CLIENTE)
        self.assertNotEqual(usuario.password, "clave-muy-segura-9")
        self.assertTrue(usuario.password.startswith("pbkdf2_"))

    def test_login_con_email(self):
        Usuario.objects.create_user("juanito", "juan@ejemplo.com", "clave-segura-123")
        respuesta = self.client.post(reverse("login"), {
            "username": "juan@ejemplo.com",
            "password": "clave-segura-123",
        })
        self.assertRedirects(respuesta, reverse("menu:listado"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), Usuario.objects.get(email="juan@ejemplo.com").pk)

    def test_registro_sin_username_genera_username_desde_email(self):
        respuesta = self.client.post(reverse("registro"), {
            "email": "lucia@x.com",
            "password1": "clave-muy-segura-9",
            "password2": "clave-muy-segura-9",
        })
        self.assertRedirects(respuesta, reverse("menu:listado"))
        usuario = Usuario.objects.get(email="lucia@x.com")
        self.assertEqual(usuario.username, "lucia")
        self.assertEqual(usuario.rol, Rol.CLIENTE)

    def test_registro_email_duplicado_es_rechazado(self):
        Usuario.objects.create_user("existente", "repetido@x.com", "clave-123")
        respuesta = self.client.post(reverse("registro"), {
            "email": "repetido@x.com",
            "password1": "clave-muy-segura-9",
            "password2": "clave-muy-segura-9",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFormError(respuesta.context["form"], "email", "Ya existe una cuenta registrada con este email.")

    def test_registro_genera_username_unico_en_colision(self):
        Usuario.objects.create_user("marta", "otra_marta@x.com", "clave-123")
        self.client.post(reverse("registro"), {
            "email": "marta@nueva.com",
            "password1": "clave-muy-segura-9",
            "password2": "clave-muy-segura-9",
        })
        usuario = Usuario.objects.get(email="marta@nueva.com")
        self.assertEqual(usuario.username, "marta1")


class Direcciones(TestCase):
    def setUp(self):
        self.ana = Usuario.objects.create_user("ana", "ana@x.com", "pw-segura-123")
        self.otra = Usuario.objects.create_user("otra", "otra@x.com", "pw-segura-123")

    def test_crud_de_direcciones_propias(self):
        self.client.force_login(self.ana)
        self.client.post(reverse("direccion_crear"), {"calle": "Calle 1", "ciudad": "Montevideo"})
        direccion = self.ana.direcciones.get()
        self.client.post(reverse("direccion_editar", args=[direccion.pk]), {"calle": "Calle 2", "ciudad": "Salto"})
        direccion.refresh_from_db()
        self.assertEqual((direccion.calle, direccion.ciudad), ("Calle 2", "Salto"))
        self.assertContains(self.client.get(reverse("direcciones")), "Calle 2")
        self.client.post(reverse("direccion_eliminar", args=[direccion.pk]))
        self.assertFalse(self.ana.direcciones.exists())

    def test_no_se_tocan_direcciones_ajenas(self):
        ajena = self.otra.direcciones.create(calle="X", ciudad="Y")
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("direccion_editar", args=[ajena.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("direccion_eliminar", args=[ajena.pk])).status_code, 404)
        self.assertTrue(self.otra.direcciones.exists())
        self.client.logout()
        self.assertEqual(self.client.get(reverse("direcciones")).status_code, 302)


class CargarDemo(TestCase):
    CLAVES = {"password_admin": "clave-admin-test-9", "password_cliente": "clave-cliente-test-9"}

    def correr(self):
        from io import StringIO
        from django.core.management import call_command
        salida = StringIO()
        call_command("cargar_demo", stdout=salida, **self.CLAVES)
        return salida.getvalue()

    def test_idempotente(self):
        from menu.models import Producto
        from pedidos.models import Configuracion, Local
        from .models import Direccion
        self.correr()
        self.correr()
        self.assertEqual(Local.objects.count(), 2)
        self.assertEqual(Producto.objects.count(), 8)
        self.assertEqual(Producto.objects.filter(disponible=False).count(), 2)
        self.assertEqual(Usuario.objects.count(), 2)
        self.assertEqual(Direccion.objects.count(), 1)
        self.assertEqual(Configuracion.objects.count(), 1)
        self.assertEqual(Usuario.objects.get(email="admin@demo.com").rol, Rol.ADMIN)
        self.assertEqual(Usuario.objects.get(email="cliente@demo.com").rol, Rol.CLIENTE)

    def test_sin_contrasenas_falla_si_hay_que_crear_usuarios(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("cargar_demo")

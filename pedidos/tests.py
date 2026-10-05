from decimal import Decimal

from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from carrito.models import Carrito
from config.reglas import PermisoError, ReglaDeNegocioError
from menu.models import Producto
from usuarios.models import Rol, Usuario

from .models import (Configuracion, EstadoPago, EstadoPedido, Local, MetodoPago, Pedido, TipoEntrega)

E, P, M, T = EstadoPedido, EstadoPago, MetodoPago, TipoEntrega


class Base(TestCase):
    def setUp(self):
        self.ana = Usuario.objects.create_user("ana", "ana@x.com", "pw-segura-123")
        self.otra = Usuario.objects.create_user("otra", "otra@x.com", "pw-segura-123")
        self.admin = Usuario.objects.create_user("admin", "a@x.com", "pw-segura-123", rol=Rol.ADMIN)
        self.direccion = self.ana.direcciones.create(calle="Calle 1", ciudad="Montevideo")
        self.local = Local.objects.create(nombre="Centro", direccion="18 de Julio 1", horarios="8-18")
        self.cafe = Producto.objects.create(nombre="Espresso", precio=Decimal(100))
        Configuracion.objects.create(monto_minimo_delivery=Decimal(500), alias_transferencia="lately.alias")

    def pedido(self, tipo=T.RETIRO, metodo=M.TRANSFERENCIA, cantidad=6, usuario=None):
        usuario = usuario or self.ana
        carrito = Carrito.de(usuario)
        carrito.agregar(self.cafe, cantidad)
        return Pedido.crear_desde_carrito(carrito, self.local, tipo, metodo,
                                          self.direccion if tipo == T.DELIVERY else None)


class MontoMinimoDelivery(Base):
    def test_delivery_exige_monto_minimo_configurable(self):
        carrito = Carrito.de(self.ana)
        carrito.agregar(self.cafe, 4)  # $400 < $500
        with self.assertRaises(ReglaDeNegocioError):
            Pedido.crear_desde_carrito(carrito, self.local, T.DELIVERY, M.TRANSFERENCIA, self.direccion)
        self.assertEqual(Pedido.objects.count(), 0)

        Configuracion.objects.update(monto_minimo_delivery=Decimal(400))  # configurable
        pedido = Pedido.crear_desde_carrito(carrito, self.local, T.DELIVERY, M.TRANSFERENCIA, self.direccion)
        self.assertEqual(pedido.total, Decimal(400))

    def test_retiro_no_tiene_monto_minimo(self):
        self.assertEqual(self.pedido(cantidad=1).estado, E.PENDIENTE)

    def test_configuracion_exige_monto_mayor_a_cero_y_solo_admin_edita(self):
        for monto in (0, -5):
            with self.assertRaises(ValidationError):
                Configuracion(monto_minimo_delivery=Decimal(monto), alias_transferencia="x").full_clean()
        url = reverse("pedidos:configuracion")
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        self.client.post(url, {"monto_minimo_delivery": "0", "alias_transferencia": "x"})
        self.assertEqual(Configuracion.obtener().monto_minimo_delivery, Decimal(500))
        self.client.post(url, {"monto_minimo_delivery": "800", "alias_transferencia": "nuevo.alias"})
        self.assertEqual(Configuracion.obtener().monto_minimo_delivery, Decimal(800))


class DeliveryYMetodoDePago(Base):
    def test_delivery_rechaza_pago_en_local(self):
        carrito = Carrito.de(self.ana)
        carrito.agregar(self.cafe, 6)
        with self.assertRaises(ReglaDeNegocioError):
            Pedido.crear_desde_carrito(carrito, self.local, T.DELIVERY, M.EN_LOCAL, self.direccion)

        pedido = self.pedido(T.DELIVERY)
        with self.assertRaises(ReglaDeNegocioError):
            pedido.pago.cambiar_metodo(self.ana, M.EN_LOCAL)
        self.assertEqual(pedido.pago.metodo, M.TRANSFERENCIA)

    def test_retiro_puede_cambiar_de_metodo_solo_con_pago_pendiente(self):
        pedido = self.pedido()
        pedido.pago.cambiar_metodo(self.ana, M.EN_LOCAL)
        self.assertEqual(pedido.pago.metodo, M.EN_LOCAL)
        pedido.pago.rechazar(self.admin, "no coincide")
        with self.assertRaises(ReglaDeNegocioError):  # rechazado: primero reintentar
            pedido.pago.cambiar_metodo(self.ana, M.TRANSFERENCIA)
        pedido.pago.reintentar(self.ana)
        pedido.pago.cambiar_metodo(self.ana, M.TRANSFERENCIA)
        self.assertEqual(pedido.pago.metodo, M.TRANSFERENCIA)

    def test_pedido_guarda_precio_al_momento_de_la_compra(self):
        pedido = self.pedido(cantidad=2)
        self.cafe.precio = Decimal(999)
        self.cafe.save()
        self.assertEqual(pedido.total, Decimal(200))
        self.assertEqual(pedido.pago.monto, Decimal(200))
        self.assertEqual(pedido.pago.estado, P.PENDIENTE)
        self.assertFalse(Carrito.de(self.ana).items.exists())


class SoloAdminConfirmaPagos(Base):
    def test_cliente_no_puede_aceptar_ni_rechazar(self):
        pedido = self.pedido()
        for accion in (lambda: pedido.pago.aceptar(self.ana), lambda: pedido.pago.rechazar(self.ana, "x")):
            with self.assertRaises(PermisoError):
                accion()
        self.client.force_login(self.ana)
        r = self.client.post(reverse("pedidos:panel_aceptar_pago", args=[pedido.pk]))
        self.assertEqual(r.status_code, 403)
        pedido.pago.refresh_from_db()
        self.assertEqual(pedido.pago.estado, P.PENDIENTE)

    def test_admin_acepta_y_rechazo_exige_motivo(self):
        pedido = self.pedido()
        with self.assertRaises(ReglaDeNegocioError):
            pedido.pago.rechazar(self.admin, "  ")
        self.client.force_login(self.admin)
        self.client.post(reverse("pedidos:panel_aceptar_pago", args=[pedido.pk]))
        pedido.pago.refresh_from_db()
        self.assertEqual(pedido.pago.estado, P.ACEPTADO)

    def test_cliente_es_avisado_por_pantalla_y_email_con_el_motivo(self):
        pedido = self.pedido()
        pedido.pago.rechazar(self.admin, "monto incorrecto")
        self.assertIn("monto incorrecto", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["ana@x.com"])
        self.client.force_login(self.ana)
        r = self.client.get(reverse("pedidos:detalle", args=[pedido.pk]))
        self.assertContains(r, "monto incorrecto")
        self.assertContains(r, "Reintentar pago")
        # el aviso en pantalla se muestra una sola vez
        pedido.pago.refresh_from_db()
        self.assertEqual(pedido.pago.aviso_sin_leer, "")

    def test_admin_puede_aceptar_pago_de_pedido_entregado(self):
        pedido = self.pedido(metodo=M.EN_LOCAL)
        for estado in (E.EN_PREPARACION, E.LISTO, E.ENTREGADO):
            pedido.cambiar_estado(self.admin, estado)
        pedido.pago.aceptar(self.admin)
        self.assertEqual(pedido.pago.estado, P.ACEPTADO)

    def test_solo_admin_cambia_estado_del_pedido(self):
        pedido = self.pedido()
        with self.assertRaises(PermisoError):
            pedido.cambiar_estado(self.ana, E.EN_PREPARACION)
        self.client.force_login(self.ana)
        self.assertEqual(self.client.post(reverse("pedidos:panel_estado", args=[pedido.pk]),
                                          {"estado": E.EN_PREPARACION}).status_code, 403)


class CancelacionSegunEstado(Base):
    def test_cliente_cancela_solo_en_pendiente(self):
        self.pedido().cancelar(self.ana)  # PENDIENTE -> ok
        for estado in (E.EN_PREPARACION, E.LISTO):
            pedido = self.pedido()
            pedido.estado = estado
            pedido.save()
            with self.assertRaises(ReglaDeNegocioError):
                pedido.cancelar(self.ana)

    def test_admin_cancela_en_pendiente_o_preparacion_pero_no_despues(self):
        for estado, ok in ((E.PENDIENTE, True), (E.EN_PREPARACION, True), (E.LISTO, False),
                           (E.ENTREGADO, False), (E.CANCELADO, False)):
            pedido = self.pedido()
            pedido.estado = estado
            pedido.save()
            if ok:
                pedido.cancelar(self.admin)
                self.assertEqual(pedido.estado, E.CANCELADO)
            else:
                with self.assertRaises(ReglaDeNegocioError):
                    pedido.cancelar(self.admin)

    def test_en_camino_no_es_cancelable(self):
        pedido = self.pedido(T.DELIVERY)
        for estado in (E.EN_PREPARACION, E.LISTO, E.EN_CAMINO):
            pedido.cambiar_estado(self.admin, estado)
        with self.assertRaises(ReglaDeNegocioError):
            pedido.cancelar(self.admin)

    def test_no_se_cancela_pedido_ajeno(self):
        with self.assertRaises(PermisoError):
            self.pedido().cancelar(self.otra)

    def test_pedido_cancelado_no_admite_aceptar_reintentar_ni_cambiar_metodo(self):
        pedido = self.pedido()
        pedido.cancelar(self.ana)
        for accion in (lambda: pedido.pago.aceptar(self.admin),
                       lambda: pedido.pago.rechazar(self.admin, "x"),
                       lambda: pedido.pago.reintentar(self.ana),
                       lambda: pedido.pago.cambiar_metodo(self.ana, M.EN_LOCAL)):
            with self.assertRaises(ReglaDeNegocioError):
                accion()


class EstadosDelPedido(Base):
    def test_en_camino_solo_para_delivery_y_orden_de_transiciones(self):
        retiro = self.pedido()
        retiro.cambiar_estado(self.admin, E.EN_PREPARACION)
        retiro.cambiar_estado(self.admin, E.LISTO)
        with self.assertRaises(ReglaDeNegocioError):
            retiro.cambiar_estado(self.admin, E.EN_CAMINO)
        retiro.cambiar_estado(self.admin, E.ENTREGADO)

        delivery = self.pedido(T.DELIVERY)
        delivery.cambiar_estado(self.admin, E.EN_PREPARACION)
        delivery.cambiar_estado(self.admin, E.LISTO)
        with self.assertRaises(ReglaDeNegocioError):  # delivery no salta EN_CAMINO
            delivery.cambiar_estado(self.admin, E.ENTREGADO)
        delivery.cambiar_estado(self.admin, E.EN_CAMINO)
        delivery.cambiar_estado(self.admin, E.ENTREGADO)

    def test_modelo_rechaza_en_camino_en_retiro(self):
        pedido = self.pedido()
        pedido.estado = E.EN_CAMINO
        with self.assertRaises(ValidationError):
            pedido.save()

    def test_estados_de_pedido_y_pago_son_independientes(self):
        pedido = self.pedido()
        pedido.cambiar_estado(self.admin, E.EN_PREPARACION)
        self.assertEqual(pedido.pago.estado, P.PENDIENTE)
        pedido.pago.aceptar(self.admin)
        self.assertEqual(pedido.estado, E.EN_PREPARACION)


class FlujoCompleto(Base):
    def test_carrito_a_pedido_a_pago_aceptado(self):
        self.client.force_login(self.ana)
        self.client.post(reverse("carrito:agregar", args=[self.cafe.pk]), {"cantidad": 6})
        datos = {"local": self.local.pk, "tipo_entrega": "DELIVERY",
                 "direccion": self.direccion.pk, "metodo_pago": "TRANSFERENCIA"}
        resumen = self.client.post(reverse("pedidos:nuevo"), datos)
        self.assertContains(resumen, "Confirmar pedido")
        self.assertEqual(Pedido.objects.count(), 0)  # el resumen todavía no guarda nada
        r = self.client.post(reverse("pedidos:nuevo"), {**datos, "confirmar": "1"})
        pedido = Pedido.objects.get()
        self.assertRedirects(r, reverse("pedidos:pago", args=[pedido.pk]))
        self.assertContains(self.client.get(r.url), "lately.alias")

        self.client.force_login(self.admin)
        self.client.post(reverse("pedidos:panel_aceptar_pago", args=[pedido.pk]))
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(reverse("pedidos:historial")), "Aceptado")

    def test_pago_en_local_muestra_te_esperamos_y_locales(self):
        pedido = self.pedido(metodo=M.EN_LOCAL)
        self.client.force_login(self.ana)
        r = self.client.get(reverse("pedidos:pago", args=[pedido.pk]))
        self.assertContains(r, "¡Te esperamos!")
        self.assertContains(r, "18 de Julio 1")

    def test_cliente_no_ve_pedidos_ajenos(self):
        pedido = self.pedido()
        self.client.force_login(self.otra)
        self.assertEqual(self.client.get(reverse("pedidos:detalle", args=[pedido.pk])).status_code, 404)

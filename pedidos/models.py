from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import models, transaction

from config.reglas import PermisoError, ReglaDeNegocioError
from usuarios.models import Rol


class TipoEntrega(models.TextChoices):
    RETIRO = "RETIRO", "Retiro en local"
    DELIVERY = "DELIVERY", "Delivery"


class MetodoPago(models.TextChoices):
    TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
    EN_LOCAL = "EN_LOCAL", "Pago en el local"


class EstadoPedido(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_PREPARACION = "EN_PREPARACION", "En preparación"
    LISTO = "LISTO", "Listo"
    EN_CAMINO = "EN_CAMINO", "En camino"  # solo delivery
    ENTREGADO = "ENTREGADO", "Entregado"
    CANCELADO = "CANCELADO", "Cancelado"


class EstadoPago(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    ACEPTADO = "ACEPTADO", "Aceptado"
    RECHAZADO = "RECHAZADO", "Rechazado"


def _positivo(valor):
    if valor <= 0:
        raise ValidationError("El monto mínimo debe ser mayor que 0.")


class Configuracion(models.Model):
    """Fila única con la configuración editable por el ADMIN."""
    monto_minimo_delivery = models.DecimalField(max_digits=8, decimal_places=2, validators=[_positivo])
    alias_transferencia = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "configuración"

    @classmethod
    def obtener(cls):
        return cls.objects.get_or_create(
            pk=1, defaults={"monto_minimo_delivery": Decimal("500"), "alias_transferencia": "lately.cafe"})[0]

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class Local(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200)
    horarios = models.CharField(max_length=200, help_text="Ej.: Lun-Vie 8-18, Sáb 9-14")

    def __str__(self):
        return self.nombre


def _exigir_admin(usuario):
    if usuario.rol != Rol.ADMIN:
        raise PermisoError("Solo un ADMIN puede realizar esta acción.")


class Pedido(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos")
    local = models.ForeignKey(Local, on_delete=models.PROTECT)
    tipo_entrega = models.CharField(max_length=10, choices=TipoEntrega.choices)
    direccion = models.ForeignKey("usuarios.Direccion", null=True, blank=True, on_delete=models.SET_NULL)
    direccion_texto = models.CharField(max_length=300, blank=True)  # copia por si se borra la dirección
    estado = models.CharField(max_length=20, choices=EstadoPedido.choices, default=EstadoPedido.PENDIENTE)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"Pedido #{self.pk}"

    @property
    def total(self):
        return sum((i.subtotal for i in self.items.all()), Decimal(0))

    @property
    def es_terminal(self):
        return self.estado in (EstadoPedido.ENTREGADO, EstadoPedido.CANCELADO)

    # ----- creación -----

    @staticmethod
    def validar_checkout(carrito, tipo_entrega, metodo_pago, direccion):
        items = list(carrito.items.select_related("producto"))
        if not items:
            raise ReglaDeNegocioError("El carrito está vacío.")
        for item in items:
            if not item.producto.disponible:
                raise ReglaDeNegocioError(f"'{item.producto.nombre}' ya no está disponible: quitalo del carrito.")
        if tipo_entrega == TipoEntrega.DELIVERY:
            minimo = Configuracion.obtener().monto_minimo_delivery
            if carrito.total < minimo:
                raise ReglaDeNegocioError(f"El delivery exige un monto mínimo de ${minimo}.")
            if metodo_pago != MetodoPago.TRANSFERENCIA:
                raise ReglaDeNegocioError("El delivery solo admite pago por transferencia.")
            if direccion is None or direccion.usuario_id != carrito.usuario_id:
                raise ReglaDeNegocioError("El delivery exige elegir una de tus direcciones.")

    @classmethod
    @transaction.atomic
    def crear_desde_carrito(cls, carrito, local, tipo_entrega, metodo_pago, direccion=None):
        """Confirma el pedido: copia los ítems con el precio de hoy, crea el Pago PENDIENTE y vacía el carrito."""
        if tipo_entrega != TipoEntrega.DELIVERY:
            direccion = None
        cls.validar_checkout(carrito, tipo_entrega, metodo_pago, direccion)
        pedido = cls.objects.create(
            usuario=carrito.usuario, local=local, tipo_entrega=tipo_entrega, direccion=direccion,
            direccion_texto=str(direccion) if direccion else "")
        ItemPedido.objects.bulk_create(
            ItemPedido(pedido=pedido, producto=i.producto, nombre_producto=i.producto.nombre,
                       cantidad=i.cantidad, precio_unitario=i.producto.precio)
            for i in carrito.items.select_related("producto"))
        Pago.objects.create(pedido=pedido, metodo=metodo_pago, monto=pedido.total)
        carrito.vaciar()
        return pedido

    # ----- estados -----

    def clean(self):
        if self.estado == EstadoPedido.EN_CAMINO and self.tipo_entrega != TipoEntrega.DELIVERY:
            raise ValidationError("EN_CAMINO solo se usa en pedidos con delivery.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def siguientes_estados(self):
        E = EstadoPedido
        if self.estado == E.PENDIENTE:
            return [E.EN_PREPARACION, E.CANCELADO]
        if self.estado == E.EN_PREPARACION:
            return [E.LISTO, E.CANCELADO]
        if self.estado == E.LISTO:
            return [E.EN_CAMINO] if self.tipo_entrega == TipoEntrega.DELIVERY else [E.ENTREGADO]
        if self.estado == E.EN_CAMINO:
            return [E.ENTREGADO]
        return []

    def cambiar_estado(self, usuario, nuevo):
        _exigir_admin(usuario)
        try:
            nuevo = EstadoPedido(nuevo)
        except ValueError:
            raise ReglaDeNegocioError("Estado inválido.")
        if nuevo == EstadoPedido.EN_CAMINO and self.tipo_entrega != TipoEntrega.DELIVERY:
            raise ReglaDeNegocioError("EN_CAMINO solo se usa en pedidos con delivery.")
        if nuevo not in self.siguientes_estados():
            raise ReglaDeNegocioError(
                f"No se puede pasar de {self.get_estado_display()} a {nuevo.label}.")
        self.estado = nuevo
        self.save(update_fields=["estado"])

    def puede_cancelar(self, usuario):
        """ADMIN: PENDIENTE o EN_PREPARACION. Dueño CLIENTE: solo PENDIENTE."""
        if usuario.rol == Rol.ADMIN:
            return self.estado in (EstadoPedido.PENDIENTE, EstadoPedido.EN_PREPARACION)
        return usuario.pk == self.usuario_id and self.estado == EstadoPedido.PENDIENTE

    def cancelar(self, usuario):
        if usuario.rol != Rol.ADMIN and usuario.pk != self.usuario_id:
            raise PermisoError("Este pedido no es tuyo.")
        if not self.puede_cancelar(usuario):
            raise ReglaDeNegocioError(
                f"Un pedido {self.get_estado_display().lower()} no puede cancelarse"
                + (": contactá al local." if self.estado == EstadoPedido.EN_PREPARACION else "."))
        self.estado = EstadoPedido.CANCELADO
        self.save(update_fields=["estado"])


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey("menu.Producto", null=True, on_delete=models.SET_NULL)
    nombre_producto = models.CharField(max_length=120)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)  # precio al momento de comprar

    class Meta:
        ordering = ["id"]

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class Pago(models.Model):
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name="pago")
    metodo = models.CharField(max_length=15, choices=MetodoPago.choices)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=10, choices=EstadoPago.choices, default=EstadoPago.PENDIENTE)
    motivo = models.TextField(blank=True)  # motivo del rechazo
    aviso_sin_leer = models.TextField(blank=True)  # mensaje para mostrar al cliente en pantalla

    def clean(self):
        if self.pedido.tipo_entrega == TipoEntrega.DELIVERY and self.metodo != MetodoPago.TRANSFERENCIA:
            raise ValidationError("El delivery solo admite pago por transferencia.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def puede_reintentar(self):
        return self.estado == EstadoPago.RECHAZADO and self.pedido.estado != EstadoPedido.CANCELADO

    @property
    def puede_cambiar_metodo(self):
        return self.estado == EstadoPago.PENDIENTE and not self.pedido.es_terminal

    # ----- ADMIN -----

    def aceptar(self, usuario):
        _exigir_admin(usuario)
        self._exigir_pedido_no_cancelado()
        self._exigir_estado(EstadoPago.PENDIENTE)
        self.estado = EstadoPago.ACEPTADO
        self.save(update_fields=["estado"])
        self._avisar(f"Tu pago del pedido #{self.pedido_id} fue ACEPTADO.")

    def rechazar(self, usuario, motivo):
        _exigir_admin(usuario)
        self._exigir_pedido_no_cancelado()
        self._exigir_estado(EstadoPago.PENDIENTE)
        if not motivo or not motivo.strip():
            raise ReglaDeNegocioError("Rechazar un pago exige un motivo.")
        self.estado = EstadoPago.RECHAZADO
        self.motivo = motivo.strip()
        self.save(update_fields=["estado", "motivo"])
        self._avisar(f"Tu pago del pedido #{self.pedido_id} fue RECHAZADO. Motivo: {self.motivo}")

    # ----- CLIENTE -----

    def reintentar(self, usuario):
        self._exigir_dueno(usuario)
        self._exigir_pedido_no_cancelado()
        self._exigir_estado(EstadoPago.RECHAZADO, "Solo se puede reintentar un pago rechazado.")
        self.estado = EstadoPago.PENDIENTE
        self.motivo = ""
        self.save(update_fields=["estado", "motivo"])

    def cambiar_metodo(self, usuario, metodo):
        self._exigir_dueno(usuario)
        self._exigir_pedido_no_cancelado()
        if self.pedido.es_terminal:
            raise ReglaDeNegocioError("El pedido ya terminó: no se puede cambiar el método de pago.")
        self._exigir_estado(
            EstadoPago.PENDIENTE,
            "Solo se puede cambiar el método con el pago pendiente; si fue rechazado, reintentá primero.")
        if metodo not in MetodoPago.values:
            raise ReglaDeNegocioError("Método de pago inválido.")
        if self.pedido.tipo_entrega == TipoEntrega.DELIVERY and metodo != MetodoPago.TRANSFERENCIA:
            raise ReglaDeNegocioError("El delivery solo admite pago por transferencia.")
        self.metodo = metodo
        self.save(update_fields=["metodo"])

    # ----- helpers -----

    def _exigir_dueno(self, usuario):
        if usuario.rol != Rol.CLIENTE or usuario.pk != self.pedido.usuario_id:
            raise PermisoError("Este pago no es tuyo.")

    def _exigir_pedido_no_cancelado(self):
        if self.pedido.estado == EstadoPedido.CANCELADO:
            raise ReglaDeNegocioError("El pedido está cancelado: el pago no admite cambios.")

    def _exigir_estado(self, esperado, mensaje="El pago ya fue resuelto."):
        if self.estado != esperado:
            raise ReglaDeNegocioError(mensaje)

    def _avisar(self, mensaje):
        """Aviso en pantalla (se muestra al cliente en su próxima visita) + email."""
        self.aviso_sin_leer = mensaje
        self.save(update_fields=["aviso_sin_leer"])
        email = self.pedido.usuario.email
        send_mail(f"Lately Café · Pedido #{self.pedido_id}", mensaje, None, [email] if email else [])

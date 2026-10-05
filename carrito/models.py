from django.conf import settings
from django.db import models

from config.reglas import PermisoError, ReglaDeNegocioError


class Carrito(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carrito")

    @classmethod
    def de(cls, usuario):
        if usuario.es_admin:
            raise PermisoError("Solo un CLIENTE tiene carrito.")
        return cls.objects.get_or_create(usuario=usuario)[0]

    @property
    def total(self):
        return sum((i.subtotal for i in self.items.select_related("producto")), 0)

    def agregar(self, producto, cantidad=1):
        self._validar(producto, cantidad)
        item, creado = ItemCarrito.objects.get_or_create(
            carrito=self, producto=producto, defaults={"cantidad": cantidad})
        if not creado:
            item.cantidad += cantidad
            item.save(update_fields=["cantidad"])
        return item

    def modificar_cantidad(self, producto, cantidad):
        self._validar(producto, cantidad)
        item = self.items.filter(producto=producto).first()
        if item is None:
            raise ReglaDeNegocioError("Ese producto no está en el carrito.")
        item.cantidad = cantidad
        item.save(update_fields=["cantidad"])

    def quitar(self, producto):
        self.items.filter(producto=producto).delete()

    def vaciar(self):
        self.items.all().delete()

    @staticmethod
    def _validar(producto, cantidad):
        if not producto.disponible:
            raise ReglaDeNegocioError(f"'{producto.nombre}' no está disponible.")
        if cantidad < 1:
            raise ReglaDeNegocioError("La cantidad debe ser al menos 1.")


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey("menu.Producto", on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["carrito", "producto"], name="item_unico_por_carrito")]
        ordering = ["id"]

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad

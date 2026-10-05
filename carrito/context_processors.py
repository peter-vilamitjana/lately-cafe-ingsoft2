from django.db.models import Sum

from .models import ItemCarrito


def contador_carrito(request):
    """Cantidad de unidades en el carrito del cliente, para el ícono de la barra."""
    usuario = request.user
    if not usuario.is_authenticated or usuario.es_admin:
        return {}
    total = ItemCarrito.objects.filter(carrito__usuario=usuario).aggregate(n=Sum("cantidad"))["n"]
    return {"carrito_cantidad": total or 0}

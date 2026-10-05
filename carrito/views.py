from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.reglas import ejecutar
from menu.models import Producto
from usuarios.models import Rol
from usuarios.permisos import rol_requerido

from .models import Carrito

cliente = rol_requerido(Rol.CLIENTE)


def _cantidad(request):
    try:
        return int(request.POST.get("cantidad", 1))
    except ValueError:
        return 0


@cliente
def ver(request):
    carrito = Carrito.de(request.user)
    return render(request, "carrito/ver.html",
                  {"carrito": carrito, "items": carrito.items.select_related("producto")})


@cliente
@require_POST
def agregar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    ejecutar(request, lambda: Carrito.de(request.user).agregar(producto, _cantidad(request)),
             f"{producto.nombre} agregado al carrito.")
    return redirect("menu:listado")


@cliente
@require_POST
def modificar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    ejecutar(request, lambda: Carrito.de(request.user).modificar_cantidad(producto, _cantidad(request)))
    return redirect("carrito:ver")


@cliente
@require_POST
def quitar(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    Carrito.de(request.user).quitar(producto)
    return redirect("carrito:ver")

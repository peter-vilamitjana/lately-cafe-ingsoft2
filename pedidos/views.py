from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from carrito.models import Carrito
from config.reglas import ReglaDeNegocioError, ejecutar
from usuarios.models import Rol
from usuarios.permisos import rol_requerido

from .forms import CheckoutForm, ConfiguracionForm
from .models import Configuracion, Local, Pago, Pedido

cliente = rol_requerido(Rol.CLIENTE)
admin = rol_requerido(Rol.ADMIN)


def _mis_pedidos(request):
    return Pedido.objects.filter(usuario=request.user).select_related("pago", "local")


def _mostrar_avisos(request, pedidos):
    """Muestra una sola vez los avisos de cambio de estado del pago."""
    for pedido in pedidos:
        if pedido.pago.aviso_sin_leer:
            messages.info(request, pedido.pago.aviso_sin_leer)
            Pago.objects.filter(pk=pedido.pago.pk).update(aviso_sin_leer="")


# ---------- CLIENTE ----------

@cliente
def historial(request):
    pedidos = list(_mis_pedidos(request))
    _mostrar_avisos(request, pedidos)
    return render(request, "pedidos/historial.html", {"pedidos": pedidos})


@cliente
def nuevo(request):
    """Elegir local/entrega/pago -> resumen -> confirmar (mismo formulario, dos pasos)."""
    carrito = Carrito.de(request.user)
    if not carrito.items.exists():
        messages.error(request, "Tu carrito está vacío.")
        return redirect("carrito:ver")
    form = CheckoutForm(request.POST or None, usuario=request.user)
    contexto = {"form": form, "carrito": carrito, "config": Configuracion.obtener(),
                "hay_locales": Local.objects.exists()}
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            Pedido.validar_checkout(carrito, d["tipo_entrega"], d["metodo_pago"], d["direccion"])
            if "confirmar" in request.POST:
                pedido = Pedido.crear_desde_carrito(
                    carrito, d["local"], d["tipo_entrega"], d["metodo_pago"], d["direccion"])
                messages.success(request, f"Pedido #{pedido.pk} confirmado. Tu pago está pendiente.")
                return redirect("pedidos:pago", pk=pedido.pk)
            return render(request, "pedidos/resumen.html", {**contexto, "datos": d})
        except ReglaDeNegocioError as e:
            messages.error(request, str(e))
    return render(request, "pedidos/nuevo.html", contexto)


def _pedido_propio(request, pk):
    return get_object_or_404(_mis_pedidos(request), pk=pk)


@cliente
def detalle(request, pk):
    pedido = _pedido_propio(request, pk)
    _mostrar_avisos(request, [pedido])
    pedido.refresh_from_db()
    return render(request, "pedidos/detalle.html",
                  {"pedido": pedido, "pago": Pago.objects.get(pedido=pedido),
                   "puede_cancelar": pedido.puede_cancelar(request.user)})


@cliente
def pago(request, pk):
    """Información de pago: transferencia (total, artículos, alias) o 'Te esperamos' (locales)."""
    pedido = _pedido_propio(request, pk)
    return render(request, "pedidos/pago.html",
                  {"pedido": pedido, "pago": pedido.pago, "config": Configuracion.obtener(),
                   "locales": Local.objects.all()})


@cliente
@require_POST
def cancelar(request, pk):
    pedido = _pedido_propio(request, pk)
    ejecutar(request, lambda: pedido.cancelar(request.user), "Pedido cancelado.")
    return redirect("pedidos:detalle", pk=pk)


@cliente
@require_POST
def reintentar_pago(request, pk):
    pedido = _pedido_propio(request, pk)
    ejecutar(request, lambda: pedido.pago.reintentar(request.user), "Pago nuevamente pendiente.")
    return redirect("pedidos:detalle", pk=pk)


@cliente
@require_POST
def cambiar_metodo(request, pk):
    pedido = _pedido_propio(request, pk)
    ejecutar(request, lambda: pedido.pago.cambiar_metodo(request.user, request.POST.get("metodo")),
             "Método de pago actualizado.")
    return redirect("pedidos:pago", pk=pk)


# ---------- ADMIN ----------

@admin
def panel_lista(request):
    pedidos = Pedido.objects.select_related("usuario", "local", "pago")
    return render(request, "pedidos/panel_lista.html", {"pedidos": pedidos})


@admin
def panel_detalle(request, pk):
    pedido = get_object_or_404(Pedido.objects.select_related("usuario", "local", "pago"), pk=pk)
    return render(request, "pedidos/panel_detalle.html",
                  {"pedido": pedido, "pago": pedido.pago, "siguientes": pedido.siguientes_estados()})


def _accion_admin(request, pk, accion, exito):
    pedido = get_object_or_404(Pedido, pk=pk)
    ejecutar(request, lambda: accion(pedido), exito)
    return redirect("pedidos:panel_detalle", pk=pk)


@admin
@require_POST
def panel_estado(request, pk):
    return _accion_admin(request, pk,
                         lambda p: p.cambiar_estado(request.user, request.POST.get("estado")),
                         "Estado del pedido actualizado.")


@admin
@require_POST
def panel_aceptar_pago(request, pk):
    return _accion_admin(request, pk, lambda p: p.pago.aceptar(request.user), "Pago aceptado.")


@admin
@require_POST
def panel_rechazar_pago(request, pk):
    return _accion_admin(request, pk,
                         lambda p: p.pago.rechazar(request.user, request.POST.get("motivo")),
                         "Pago rechazado.")


@admin
def configuracion(request):
    form = ConfiguracionForm(request.POST or None, instance=Configuracion.obtener())
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Configuración guardada.")
        return redirect("pedidos:configuracion")
    return render(request, "pedidos/configuracion.html", {"form": form})

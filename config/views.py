from django.views.generic import TemplateView

from menu.models import Producto
from pedidos.models import Local


class PortadaView(TemplateView):
    """Portada: destacados y locales salen de la base; si no hay datos, el template oculta la sección."""
    template_name = "portada.html"

    def get_context_data(self, **kwargs):
        # Destacados: productos disponibles, primero los que tienen foto.
        destacados = sorted(Producto.objects.filter(disponible=True), key=lambda p: not p.imagen)[:4]
        return super().get_context_data(destacados=destacados, locales=Local.objects.all(), **kwargs)

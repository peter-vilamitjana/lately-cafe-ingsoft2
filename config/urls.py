from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from .views import PortadaView

urlpatterns = [
    path("", PortadaView.as_view(), name="portada"),
    path("django-admin/", admin.site.urls),  # admin técnico de Django; el panel de negocio está en /panel/
    path("cuentas/", include("usuarios.urls")),
    path("", include("menu.urls")),
    path("", include("carrito.urls")),
    path("", include("pedidos.urls")),
]

# Las imágenes subidas se sirven desde Django solo en desarrollo.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

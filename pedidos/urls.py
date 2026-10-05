from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    # cliente
    path("pedidos/", views.historial, name="historial"),
    path("pedidos/nuevo/", views.nuevo, name="nuevo"),
    path("pedidos/<int:pk>/", views.detalle, name="detalle"),
    path("pedidos/<int:pk>/pago/", views.pago, name="pago"),
    path("pedidos/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
    path("pedidos/<int:pk>/pago/reintentar/", views.reintentar_pago, name="reintentar_pago"),
    path("pedidos/<int:pk>/pago/metodo/", views.cambiar_metodo, name="cambiar_metodo"),
    # admin
    path("panel/pedidos/", views.panel_lista, name="panel_lista"),
    path("panel/pedidos/<int:pk>/", views.panel_detalle, name="panel_detalle"),
    path("panel/pedidos/<int:pk>/estado/", views.panel_estado, name="panel_estado"),
    path("panel/pedidos/<int:pk>/pago/aceptar/", views.panel_aceptar_pago, name="panel_aceptar_pago"),
    path("panel/pedidos/<int:pk>/pago/rechazar/", views.panel_rechazar_pago, name="panel_rechazar_pago"),
    path("panel/configuracion/", views.configuracion, name="configuracion"),
]

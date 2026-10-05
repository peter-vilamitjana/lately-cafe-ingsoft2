from django.urls import path

from . import views

app_name = "carrito"

urlpatterns = [
    path("carrito/", views.ver, name="ver"),
    path("carrito/agregar/<int:producto_id>/", views.agregar, name="agregar"),
    path("carrito/modificar/<int:producto_id>/", views.modificar, name="modificar"),
    path("carrito/quitar/<int:producto_id>/", views.quitar, name="quitar"),
]

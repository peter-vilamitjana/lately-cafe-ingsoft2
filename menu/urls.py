from django.urls import path

from . import views

app_name = "menu"

urlpatterns = [
    path("menu/", views.MenuView.as_view(), name="listado"),
    path("panel/productos/", views.PanelListView.as_view(), name="panel"),
    path("panel/productos/nuevo/", views.ProductoCreateView.as_view(), name="crear"),
    path("panel/productos/<int:pk>/editar/", views.ProductoUpdateView.as_view(), name="editar"),
    path("panel/productos/<int:pk>/eliminar/", views.ProductoDeleteView.as_view(), name="eliminar"),
    path("panel/productos/<int:pk>/disponibilidad/", views.ToggleDisponibilidadView.as_view(), name="disponibilidad"),
]

from django.contrib.auth import views as auth_views
from django.urls import include, path

from . import views
from .forms import EmailAuthenticationForm

# django.contrib.auth.urls aporta: login, logout, password_change, password_reset (+ confirm/done/complete)
urlpatterns = [
    path("login/", auth_views.LoginView.as_view(authentication_form=EmailAuthenticationForm), name="login"),
    path("registro/", views.registro, name="registro"),
    path("direcciones/", views.DireccionListView.as_view(), name="direcciones"),
    path("direcciones/nueva/", views.DireccionCreateView.as_view(), name="direccion_crear"),
    path("direcciones/<int:pk>/editar/", views.DireccionUpdateView.as_view(), name="direccion_editar"),
    path("direcciones/<int:pk>/eliminar/", views.DireccionDeleteView.as_view(), name="direccion_eliminar"),
    path("", include("django.contrib.auth.urls")),
]

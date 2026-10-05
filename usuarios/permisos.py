from functools import wraps

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import Rol


def rol_requerido(rol):
    """Anónimo -> login; autenticado con otro rol -> 403."""
    def decorador(vista):
        @wraps(vista)
        def envuelta(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.rol != rol:
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envuelta
    return decorador


class _RolMixin(UserPassesTestMixin):
    rol = None

    def test_func(self):
        usuario = self.request.user
        return usuario.is_authenticated and usuario.rol == self.rol


class SoloAdminMixin(_RolMixin):
    rol = Rol.ADMIN


class SoloClienteMixin(_RolMixin):
    rol = Rol.CLIENTE

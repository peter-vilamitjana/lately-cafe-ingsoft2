"""Errores de reglas de negocio y helper para ejecutarlos desde las vistas."""
from django.contrib import messages


class ReglaDeNegocioError(Exception):
    pass


class PermisoError(ReglaDeNegocioError):
    pass


def ejecutar(request, accion, exito=None):
    """Corre accion(); si rompe una regla de negocio muestra el error. Devuelve True si salió bien."""
    try:
        accion()
    except ReglaDeNegocioError as e:
        messages.error(request, str(e))
        return False
    if exito:
        messages.success(request, exito)
    return True

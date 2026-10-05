from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Direccion, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Lately Café", {"fields": ("rol",)}),)
    list_display = ("username", "email", "rol", "is_staff")


admin.site.register(Direccion)

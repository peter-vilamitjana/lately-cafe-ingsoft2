from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models


class Rol(models.TextChoices):
    CLIENTE = "CLIENTE", "Cliente"
    ADMIN = "ADMIN", "Administrador"


class UsuarioManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra):
        extra.setdefault("rol", Rol.ADMIN)
        return super().create_superuser(username, email, password, **extra)


class Usuario(AbstractUser):
    email = models.EmailField("email", unique=True)
    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.CLIENTE)

    objects = UsuarioManager()

    @property
    def es_admin(self):
        return self.rol == Rol.ADMIN

    def __str__(self):
        return self.get_full_name() or self.username


class Direccion(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="direcciones")
    calle = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "direcciones"

    def __str__(self):
        return f"{self.calle}, {self.ciudad}"

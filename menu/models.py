from django.db import models


class Categoria(models.TextChoices):
    CAFE = "CAFE", "Café"
    TE = "TE", "Té"
    PASTELERIA = "PASTELERIA", "Pastelería"
    OTRO = "OTRO", "Otro"


class Producto(models.Model):
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    categoria = models.CharField(max_length=20, choices=Categoria.choices, default=Categoria.CAFE)
    disponible = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to="productos/", blank=True)

    class Meta:
        ordering = ["categoria", "nombre"]

    def __str__(self):
        return self.nombre

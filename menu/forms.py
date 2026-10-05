from django import forms

from .models import Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ("nombre", "descripcion", "precio", "categoria", "imagen", "disponible")
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 3})}

    def clean_precio(self):
        precio = self.cleaned_data["precio"]
        if precio < 0:
            raise forms.ValidationError("El precio no puede ser negativo.")
        return precio

from django import forms

from .models import Configuracion, Local, MetodoPago, TipoEntrega


class CheckoutForm(forms.Form):
    local = forms.ModelChoiceField(Local.objects.all(), label="Local", empty_label=None)
    tipo_entrega = forms.ChoiceField(choices=TipoEntrega.choices, label="Entrega", initial=TipoEntrega.RETIRO)
    direccion = forms.ModelChoiceField(None, required=False, label="Dirección (solo delivery)")
    metodo_pago = forms.ChoiceField(choices=MetodoPago.choices, label="Método de pago")

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["direccion"].queryset = usuario.direcciones.all()


class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = Configuracion
        fields = ("monto_minimo_delivery", "alias_transferencia")

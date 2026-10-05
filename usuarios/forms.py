from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Rol, Usuario


class EmailAuthenticationForm(AuthenticationForm):
    """Formulario de inicio de sesión que solicita el email en lugar del username."""

    username = forms.CharField(
        label="Email",
        widget=forms.TextInput(attrs={
            "autofocus": True,
            "placeholder": "tu@email.com",
            "autocomplete": "email",
        }),
    )

    error_messages = {
        "invalid_login": "Por favor ingresá un email y contraseña correctos.",
        "inactive": "Esta cuenta está inactiva.",
    }


class RegistroForm(UserCreationForm):
    """El rol no es editable: todo registro público es CLIENTE.
    El campo username se oculta de la UI y se genera automáticamente a partir del email."""

    class Meta:
        model = Usuario
        fields = ("username", "email", "first_name", "last_name")
        widgets = {
            "username": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False
        self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise forms.ValidationError("El email es obligatorio.")
        qs = Usuario.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe una cuenta registrada con este email.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        email = cleaned_data.get("email")

        # Si el usuario no ingresó un username (ej. registro simplificado de la UI),
        # lo generamos a partir del email garantizando unicidad.
        if not username and email:
            base = email.split("@")[0].strip() or "usuario"
            candidate = base
            counter = 1
            while Usuario.objects.filter(username__iexact=candidate).exists():
                candidate = f"{base}{counter}"
                counter += 1
            cleaned_data["username"] = candidate
            self.cleaned_data["username"] = candidate
            self.instance.username = candidate

        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.rol = Rol.CLIENTE
        if not usuario.username:
            usuario.username = self.cleaned_data.get("username")
        if commit:
            usuario.save()
        return usuario

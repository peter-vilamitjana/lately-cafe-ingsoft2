from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import RegistroForm
from .models import Direccion


def registro(request):
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.save())
        return redirect("menu:listado")
    return render(request, "registration/registro.html", {"form": form})


class _DireccionMixin(LoginRequiredMixin):
    """Cada usuario solo ve y modifica sus propias direcciones."""
    model = Direccion
    success_url = reverse_lazy("direcciones")

    def get_queryset(self):
        return Direccion.objects.filter(usuario=self.request.user)


class DireccionListView(_DireccionMixin, ListView):
    template_name = "usuarios/direcciones_lista.html"
    context_object_name = "direcciones"


class DireccionCreateView(_DireccionMixin, CreateView):
    fields = ("calle", "ciudad")
    template_name = "usuarios/direccion_form.html"

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        return super().form_valid(form)


class DireccionUpdateView(_DireccionMixin, UpdateView):
    fields = ("calle", "ciudad")
    template_name = "usuarios/direccion_form.html"


class DireccionDeleteView(_DireccionMixin, DeleteView):
    template_name = "usuarios/direccion_confirmar_eliminar.html"

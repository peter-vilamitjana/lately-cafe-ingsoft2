from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from usuarios.permisos import SoloAdminMixin

from .forms import ProductoForm
from .models import Categoria, Producto


class MenuView(ListView):
    """Menú público: listado + filtro por categoría (?categoria=) + búsqueda por nombre (?q=)."""
    model = Producto
    template_name = "menu/listado.html"
    context_object_name = "productos"

    def get_queryset(self):
        productos = super().get_queryset()
        categoria = self.request.GET.get("categoria", "")
        q = self.request.GET.get("q", "").strip()
        if categoria in Categoria.values:
            productos = productos.filter(categoria=categoria)
        if q:
            productos = productos.filter(nombre__icontains=q)
        return productos

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            categorias=Categoria.choices,
            categoria=self.request.GET.get("categoria", ""),
            q=self.request.GET.get("q", ""),
            **kwargs)


class PanelListView(SoloAdminMixin, ListView):
    model = Producto
    template_name = "menu/panel_lista.html"
    context_object_name = "productos"


class ProductoCreateView(SoloAdminMixin, CreateView):
    model = Producto
    form_class = ProductoForm
    template_name = "menu/producto_form.html"
    success_url = reverse_lazy("menu:panel")


class ProductoUpdateView(SoloAdminMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = "menu/producto_form.html"
    success_url = reverse_lazy("menu:panel")


class ProductoDeleteView(SoloAdminMixin, DeleteView):
    model = Producto
    template_name = "menu/producto_confirmar_eliminar.html"
    success_url = reverse_lazy("menu:panel")


class ToggleDisponibilidadView(SoloAdminMixin, View):
    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        producto.disponible = not producto.disponible
        producto.save(update_fields=["disponible"])
        messages.success(request, f"{producto.nombre}: {'disponible' if producto.disponible else 'no disponible'}.")
        return redirect("menu:panel")

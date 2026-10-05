# Diagrama de secuencia — El cliente confirma un pedido

Flujo real de la vista `pedidos.views.nuevo` (URL `pedidos/nuevo/`, name `pedidos:nuevo`), protegida con `rol_requerido(Rol.CLIENTE)`. Es un mismo formulario (`CheckoutForm`) en dos pasos: "Ver resumen" y "Confirmar pedido" (`name="confirmar"`).

```mermaid
sequenceDiagram
    actor C as Cliente
    participant T as Template<br/>(nuevo.html / resumen.html)
    participant V as View<br/>(pedidos.views.nuevo)
    participant M as Modelos<br/>(Pedido, ItemPedido, Pago)
    participant DB as Base de datos

    C->>T: Completa local, tipo_entrega, direccion, metodo_pago
    C->>T: Click "Ver resumen" (POST)
    T->>V: POST pedidos:nuevo
    V->>DB: Carrito.de(request.user) / carrito.items.exists()
    V->>V: CheckoutForm(request.POST, usuario=request.user).is_valid()
    V->>M: Pedido.validar_checkout(carrito, tipo_entrega, metodo_pago, direccion)
    M->>DB: carrito.items.select_related("producto")

    alt Carrito vacío
        M-->>V: ReglaDeNegocioError("El carrito está vacío.")
        V-->>T: messages.error + render nuevo.html
    else Producto no disponible al confirmar
        M-->>V: ReglaDeNegocioError("'X' ya no está disponible: quitalo del carrito.")
        V-->>T: messages.error + render nuevo.html
    else Delivery por debajo del monto mínimo
        M->>DB: Configuracion.obtener().monto_minimo_delivery
        M-->>V: ReglaDeNegocioError("El delivery exige un monto mínimo de $...")
        V-->>T: messages.error + render nuevo.html
    else Delivery con método de pago no permitido (EN_LOCAL)
        M-->>V: ReglaDeNegocioError("El delivery solo admite pago por transferencia.")
        V-->>T: messages.error + render nuevo.html
    else Delivery sin dirección propia
        M-->>V: ReglaDeNegocioError("El delivery exige elegir una de tus direcciones.")
        V-->>T: messages.error + render nuevo.html
    else Validación correcta
        V-->>T: render resumen.html (datos, carrito)
        T-->>C: Muestra resumen del pedido
        C->>T: Click "Confirmar pedido" (POST con confirmar=1)
        T->>V: POST pedidos:nuevo
        V->>M: Pedido.validar_checkout(...) (se repite)
        Note over V,M: Si falla, mismas ramas de error de arriba
        V->>M: Pedido.crear_desde_carrito(carrito, local, tipo_entrega, metodo_pago, direccion)
        Note over M,DB: transaction.atomic
        M->>M: validar_checkout(...) (tercera validación)
        M->>DB: Pedido.objects.create(estado=PENDIENTE, direccion_texto=str(direccion))
        M->>DB: ItemPedido.objects.bulk_create(nombre_producto, cantidad, precio_unitario = producto.precio de hoy)
        M->>DB: Pago.objects.create(pedido, metodo, monto=pedido.total) estado=PENDIENTE
        M->>DB: carrito.vaciar() (borra ItemCarrito)
        M-->>V: pedido
        V-->>T: messages.success + redirect pedidos:pago (pk)
        T-->>C: "Pedido #N confirmado. Tu pago está pendiente."
    end
```

Notas:

- Si `tipo_entrega` no es DELIVERY, `crear_desde_carrito` fuerza `direccion = None`.
- Las ramas de error son excepciones `ReglaDeNegocioError` que la vista captura en un `try/except` propio dentro de `nuevo` (no usa `config.reglas.ejecutar`). El orden de las validaciones es el de `Pedido.validar_checkout`.
- Si `CheckoutForm` no es válido (por ejemplo, local o método inexistente), la vista vuelve a renderizar `nuevo.html` con los errores del formulario, sin llegar a los modelos.
- Si el carrito está vacío al entrar a la vista, redirige a `carrito:ver` con "Tu carrito está vacío." antes de procesar el formulario.
- Si `crear_desde_carrito` falla a mitad de camino, `transaction.atomic` revierte todo y el carrito queda intacto.

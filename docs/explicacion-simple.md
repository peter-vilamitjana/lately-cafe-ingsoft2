# Explicación simple de Lately Café

Guía para entender el diseño si recién estás aprendiendo MVC y UML. Complementa [diagrama-de-clases.md](diagrama-de-clases.md) y [diagrama-de-secuencia-confirmar-pedido.md](diagrama-de-secuencia-confirmar-pedido.md).

## a) Cómo se lee cada diagrama

### Diagrama de clases (qué cosas existen y cómo se relacionan)

Cada caja es una clase (en Django, un modelo = una tabla). Arriba va el nombre, abajo los atributos (datos) y los métodos (acciones).

**Flechas y líneas**

| Símbolo | Significa | Ejemplo del proyecto |
|---|---|---|
| `A --> B` | A conoce a B (tiene una clave foránea hacia B). | `Pedido --> Local`: cada pedido apunta a un local. |
| `A *-- B` (rombo lleno) | B es parte de A y no tiene sentido sin A (composición). | `Pedido *-- ItemPedido`: si se borra el pedido, se borran sus ítems. |
| `A ..> B` (punteada) | A usa el enum B. | `Pago ..> EstadoPago`. |

**Multiplicidad**: los números en los extremos dicen cuántos objetos participan.

- `1` = exactamente uno. `0..1` = ninguno o uno. `0..*` = ninguno o muchos. `1..*` = al menos uno.
- `Usuario "1" --> "0..*" Pedido`: un usuario tiene cero o muchos pedidos.
- `Pedido "1" *-- "1" Pago` (1..1): un pedido tiene exactamente un pago.
- `Pedido "1" *-- "1..*" ItemPedido`: un pedido tiene al menos un ítem (lo garantiza el código al rechazar carritos vacíos, no la base de datos).

**Enums de estado** (cajas con `<<enumeration>>`): son listas cerradas de valores posibles. `EstadoPedido` (PENDIENTE, EN_PREPARACION, LISTO, EN_CAMINO, ENTREGADO, CANCELADO) y `EstadoPago` (PENDIENTE, ACEPTADO, RECHAZADO) indican en qué etapa de su vida está un pedido o un pago. `MetodoPago` y `TipoEntrega` son enums de opciones, no de estados.

### Diagrama de secuencia (qué pasa y en qué orden)

Se lee de arriba hacia abajo: el tiempo avanza hacia abajo.

- **Participantes** (cajas arriba, con línea vertical): quienes intervienen. Acá: Cliente, Template, View, Modelos y Base de datos.
- **Flecha continua `->>`**: un participante le pide algo a otro (llama a un método, envía un formulario).
- **Flecha punteada `-->>`**: la respuesta o el resultado, incluidos los errores.
- **`Note`**: aclaración que no es un mensaje.
- **Bloque `alt` / `else`**: alternativas excluyentes; ocurre una sola. Cada `else` es una rama: carrito vacío, producto no disponible, delivery bajo el mínimo, método no permitido, o el caso exitoso.

## b) MVC clásico vs. Django

Cuidado con los nombres: Django cambia las etiquetas. La **View de Django es el controlador** del MVC clásico, y el **Template de Django es la vista** del MVC clásico.

| MVC clásico | En Django | Qué hace | Ejemplo en el proyecto |
|---|---|---|---|
| Modelo | **Model** | Datos y reglas de negocio. | [pedidos/models.py](../pedidos/models.py): `Pedido`, `Pago`, `Pedido.validar_checkout`. También [carrito/models.py](../carrito/models.py) y [menu/models.py](../menu/models.py). |
| Controlador | **View** | Recibe la petición, llama al modelo y decide qué responder. | [pedidos/views.py](../pedidos/views.py): `nuevo`, `cancelar`. Las URLs que las enlazan están en [pedidos/urls.py](../pedidos/urls.py). |
| Vista | **Template** | HTML que ve el usuario. | [pedidos/templates/pedidos/nuevo.html](../pedidos/templates/pedidos/nuevo.html) y [resumen.html](../pedidos/templates/pedidos/resumen.html); el layout común es [templates/base.html](../templates/base.html). |

Además aparece una pieza que no está en el MVC clásico: el **Form** ([pedidos/forms.py](../pedidos/forms.py), `CheckoutForm`), que valida los datos que escribe el usuario antes de tocar las reglas de negocio.

## c) El recorrido de "confirmar pedido" en 8 pasos

1. **El cliente entra a "Nuevo pedido".** La URL `pedidos/nuevo/` (nombre `pedidos:nuevo`, en [pedidos/urls.py](../pedidos/urls.py)) ejecuta `pedidos.views.nuevo`, protegida por `rol_requerido(Rol.CLIENTE)`: un anónimo va al login y un ADMIN recibe 403.
2. **La vista prepara el contexto.** En [pedidos/views.py](../pedidos/views.py), `nuevo` obtiene el carrito con `Carrito.de(request.user)`. Si no tiene ítems, avisa "Tu carrito está vacío." y redirige a `carrito:ver`.
3. **Se muestra el formulario.** `CheckoutForm` ([pedidos/forms.py](../pedidos/forms.py)) pide local, tipo de entrega, dirección y método de pago, y limita las direcciones a las del usuario. Se renderiza con `pedidos/nuevo.html`.
4. **"Ver resumen" (POST).** La vista valida el formulario y llama a `Pedido.validar_checkout(...)` ([pedidos/models.py](../pedidos/models.py)). Si todo está bien, renderiza `pedidos/resumen.html`; si lanza `ReglaDeNegocioError`, muestra el mensaje con `messages.error` y vuelve a `nuevo.html`.
5. **El cliente presiona "Confirmar pedido".** `resumen.html` reenvía los mismos campos ocultos más `confirmar=1`. Vuelve a entrar a `nuevo`.
6. **La vista valida otra vez.** Como el código de validación está antes del `if "confirmar" in request.POST`, `validar_checkout` corre de nuevo con el estado actual del carrito.
7. **Se crea el pedido.** `Pedido.crear_desde_carrito(...)` corre dentro de `transaction.atomic`: vuelve a llamar a `validar_checkout`, crea el `Pedido` (estado PENDIENTE, con la copia `direccion_texto`), crea los `ItemPedido` con `nombre_producto` y `precio_unitario` del producto de hoy, crea el `Pago` en PENDIENTE con `monto=pedido.total` y vacía el carrito con `carrito.vaciar()`.
8. **Respuesta al cliente.** La vista muestra "Pedido #N confirmado. Tu pago está pendiente." y redirige a `pedidos:pago` (vista `pago`, template `pedidos/pago.html`), que muestra cómo pagar según el método.

## d) Por qué Pedido y Pago tienen estados separados

El pedido responde "¿en qué punto está la preparación y entrega?" y el pago responde "¿se cobró?". Son dos procesos distintos que no avanzan juntos. Lo dice la regla del proyecto: ninguno cambia al otro automáticamente, y en el código `Pago.aceptar` no toca `Pedido.estado` ni `Pedido.cambiar_estado` toca `Pago.estado`.

**Ejemplo con pago EN_LOCAL:** el cliente retira y paga en el mostrador. El ADMIN pasa el pedido a EN_PREPARACION y a LISTO, pero el pago sigue PENDIENTE porque el cliente todavía no pagó. Recién cuando el cliente paga en el local, el ADMIN acepta el pago. Con un solo estado mezclado no se podría expresar "pedido en preparación con pago pendiente".

La única conexión son restricciones puntuales: un pedido CANCELADO no admite cambios en su pago, y el método de pago de un pedido terminado no se puede cambiar.

## e) Preguntas posibles en la defensa de diseño

**1. ¿Por qué `Pago` es una clase aparte y no un campo de `Pedido`?**
Porque tiene su propio ciclo de vida (PENDIENTE, ACEPTADO, RECHAZADO), motivo de rechazo, aviso para el cliente y acciones propias (`aceptar`, `rechazar`, `reintentar`, `cambiar_metodo`). Es una relación 1 a 1 (`OneToOneField`).

**2. ¿Por qué `ItemPedido` guarda `nombre_producto` y `precio_unitario` si ya apunta a `Producto`?**
Para congelar lo que el cliente compró. Si el precio o el nombre del producto cambian después, el pedido no se altera; y si el producto se borra, la FK queda en NULL (`SET_NULL`) pero el ítem conserva sus datos.

**3. ¿Por qué el pedido guarda `direccion_texto` además de la FK a `Direccion`?**
Porque la `Direccion` puede borrarse (la FK pasa a NULL). La copia en texto mantiene la dirección a la que se entregó.

**4. ¿Dónde viven las reglas de negocio y por qué no en las vistas?**
En los modelos (`Pedido`, `Pago`, `Carrito`), que lanzan `ReglaDeNegocioError` o `PermisoError`. Las vistas solo capturan el error y lo muestran (con `try/except` en `nuevo` o con `config.reglas.ejecutar` en las demás). Así las reglas se pueden probar y reutilizar sin pasar por HTML.

**5. ¿Por qué `validar_checkout` se ejecuta varias veces?**
Respuesta honesta: parte es redundancia y parte tiene sentido.
- En el paso "Ver resumen", la vista lo llama para no mostrar un resumen de un pedido que no se podría confirmar. Esa llamada es útil.
- En el POST de confirmar, el flujo de la vista lo llama otra vez (porque la validación está antes del `if "confirmar"`) y luego `crear_desde_carrito` lo llama por tercera vez en total del recorrido. Entre el resumen y el clic pudo pasar tiempo: un producto pudo dejar de estar disponible o el monto mínimo pudo cambiar, así que revalidar con datos actuales es correcto.
- Dentro de `crear_desde_carrito` la validación garantiza que el método sea seguro sin importar quién lo llame, y queda dentro de la transacción.
- Lo redundante: en el POST de confirmar, la llamada de la vista y la de `crear_desde_carrito` validan lo mismo, una justo después de la otra. Con quitar la de la vista en esa rama no cambiaría el resultado. No hay bloqueo de filas (`select_for_update`), así que la repetición no protege contra concurrencia real, solo reduce la ventana de datos viejos.

**6. ¿Qué pasa si falla algo a mitad de `crear_desde_carrito`?**
Está decorado con `@transaction.atomic`: si algo falla, se revierte todo (no queda un pedido sin ítems ni sin pago) y el carrito no se vacía.

## Archivo creado

- [docs/explicacion-simple.md](explicacion-simple.md)

## Inconsistencias encontradas

1. **Cantidad de validaciones.** El pedido hablaba de "tres veces en la confirmación". En el código, el POST de confirmar valida **dos** veces (vista y `crear_desde_carrito`); la tercera ocurre en el POST anterior, "Ver resumen". Es decir, tres en todo el recorrido, dos en la petición de confirmar. Mi resumen anterior decía "tres veces en el paso de confirmar", que era impreciso; el diagrama de secuencia sí lo muestra correctamente como "se repite" y "tercera validación" dentro del flujo completo, aunque la nota "tercera" puede leerse como si fuera en una sola petición.
2. **El `1..*` de `Pedido → ItemPedido`** no existe en la base de datos: depende de `validar_checkout`.
3. **Nada impide ENTREGADO con pago PENDIENTE.** `cambiar_estado` no mira el pago, coherente con la independencia de estados pero conviene saberlo si preguntan.
4. **`Carrito.total` usa el precio vigente** del producto (no está congelado hasta que se crea el `ItemPedido`).

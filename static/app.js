/* Lately Café · interacciones mínimas (sin dependencias). */
(function () {
  "use strict";

  // Barra: sombra al hacer scroll
  var barra = document.getElementById("barra");
  function alScrollear() { if (barra) barra.classList.toggle("scrolled", window.scrollY > 8); }
  window.addEventListener("scroll", alScrollear, { passive: true });
  alScrollear();

  // Menú hamburguesa
  var boton = document.getElementById("hamburguesa");
  var nav = document.getElementById("nav-principal");
  function alternarNav(abrir) {
    nav.classList.toggle("abierto", abrir);
    boton.setAttribute("aria-expanded", abrir ? "true" : "false");
    boton.setAttribute("aria-label", abrir ? "Cerrar menú" : "Abrir menú");
  }
  if (boton && nav) {
    boton.addEventListener("click", function () { alternarNav(!nav.classList.contains("abierto")); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && nav.classList.contains("abierto")) { alternarNav(false); boton.focus(); }
    });
  }

  // Toasts
  var contenedor = document.getElementById("toasts");
  function mostrarToast(texto, tipo) {
    if (!contenedor) return;
    var p = document.createElement("p");
    p.className = "toast " + (tipo || "success");
    p.textContent = texto;
    contenedor.appendChild(p);
    p.addEventListener("animationend", function () { p.remove(); });
  }

  function actualizarContador(cantidad) {
    var c = document.getElementById("carrito-contador");
    if (!c) return;
    c.textContent = cantidad;
    c.hidden = !Number(cantidad);
    c.classList.remove("salto");
    void c.offsetWidth;
    c.classList.add("salto");
  }

  // "Agregar" al carrito sin recargar: se envía el formulario, se lee el mensaje y el contador
  // de la página a la que redirige la vista y se muestra el toast. Si algo falla, envío normal.
  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form.classList || !form.classList.contains("js-agregar") || !window.fetch) return;
    e.preventDefault();
    var btn = form.querySelector("button");
    if (btn) btn.disabled = true;
    fetch(form.action, { method: "POST", body: new FormData(form), credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("http " + r.status);
        return r.text();
      })
      .then(function (html) {
        var doc = new DOMParser().parseFromString(html, "text/html");
        var msgs = doc.querySelectorAll("[data-toast]");
        msgs.forEach(function (m) {
          mostrarToast(m.textContent.trim(), m.classList.contains("error") ? "error" : "success");
        });
        var c = doc.getElementById("carrito-contador");
        if (c) actualizarContador(c.getAttribute("data-cantidad"));
      })
      .catch(function () { form.classList.remove("js-agregar"); form.submit(); })
      .then(function () { if (btn) btn.disabled = false; });
  });
})();

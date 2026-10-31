// Aplica el tema antes de pintar para evitar un destello del tema equivocado. Cada visita
// empieza en claro: sessionStorage solo recuerda el cambio mientras dure la pestaña.
document.documentElement.dataset.theme = sessionStorage.getItem("orbita-theme") || "light";

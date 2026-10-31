// Aplica el tema antes de pintar para evitar un destello del tema equivocado.
document.documentElement.dataset.theme = localStorage.getItem("orbita-theme") || "dark";

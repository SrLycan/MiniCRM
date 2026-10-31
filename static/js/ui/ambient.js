/** Parallax suave del fondo. Solo con puntero preciso y sin preferencia de movimiento reducido. */

export function initAmbient() {
  const canUseParallax =
    matchMedia("(pointer: fine)").matches &&
    !matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (!canUseParallax) return;

  const ambient = document.querySelector(".ambient");
  let frameRequested = false;

  window.addEventListener("pointermove", (event) => {
    if (frameRequested) return;
    frameRequested = true;
    requestAnimationFrame(() => {
      ambient.style.setProperty("--pointer-x", (event.clientX / innerWidth - 0.5).toFixed(3));
      ambient.style.setProperty("--pointer-y", (event.clientY / innerHeight - 0.5).toFixed(3));
      frameRequested = false;
    });
  });
}

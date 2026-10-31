/** Comportamiento común de los <dialog>: cierre animado, por fondo, botón o Esc. */

export function closeDialog(dialog) {
  if (!dialog.open || dialog.classList.contains("is-closing")) return;

  dialog.classList.add("is-closing");
  const finishClosing = () => {
    dialog.classList.remove("is-closing");
    dialog.close();
  };

  if (dialog.getAnimations().length > 0) {
    dialog.addEventListener("animationend", finishClosing, { once: true });
  } else {
    finishClosing();
  }
}

export function setUpDialog(dialog) {
  dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
    closeDialog(dialog);
  });

  dialog.addEventListener("click", (event) => {
    const clickedBackdrop = event.target === dialog;
    if (clickedBackdrop || event.target.closest("[data-dialog-close]")) {
      closeDialog(dialog);
    }
  });
}

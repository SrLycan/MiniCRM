import { createElement, createIcon } from "../core/dom.js";

const TOAST_DURATION_MS = 4000;

const ICONS = { success: "check", error: "alert" };

/** Muestra un toast. Con `actionLabel` y `onAction` añade un botón y lo devuelve. */
export function showToast(
  message,
  type = "success",
  { actionLabel, onAction, durationMs = TOAST_DURATION_MS } = {},
) {
  const icon = createIcon(ICONS[type]);
  icon.classList.add("toast__icon");

  const toast = createElement("div", { class: `toast toast--${type}` }, icon, createElement("p", {}, message));
  document.querySelector("#toasts").append(toast);

  const dismiss = () => {
    clearTimeout(timeoutId);
    toast.classList.add("is-leaving");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  };
  const timeoutId = setTimeout(dismiss, durationMs);

  if (!actionLabel) return null;

  const actionButton = createElement("button", { class: "toast__action", type: "button" }, actionLabel);
  actionButton.addEventListener("click", () => {
    dismiss();
    onAction();
  });
  toast.append(actionButton);
  return actionButton;
}

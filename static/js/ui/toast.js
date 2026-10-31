import { createElement, createIcon } from "../core/dom.js";

const TOAST_DURATION_MS = 4000;

const ICONS = { success: "check", error: "alert" };

export function showToast(message, type = "success") {
  const icon = createIcon(ICONS[type]);
  icon.classList.add("toast__icon");

  const toast = createElement("div", { class: `toast toast--${type}` }, icon, createElement("p", {}, message));
  document.querySelector("#toasts").append(toast);

  setTimeout(() => {
    toast.classList.add("is-leaving");
    toast.addEventListener("animationend", () => toast.remove(), { once: true });
  }, TOAST_DURATION_MS);
}

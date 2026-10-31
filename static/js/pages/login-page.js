import { initAmbient } from "../ui/ambient.js";

initAmbient();

const passwordInput = document.querySelector("#id_password");
const passwordToggle = document.querySelector("[data-password-toggle]");
const submitButton = document.querySelector("[data-loading-submit]");

passwordToggle.addEventListener("click", () => {
  const isHidden = passwordInput.type === "password";
  passwordInput.type = isHidden ? "text" : "password";
  passwordToggle.setAttribute("aria-pressed", String(isHidden));
  passwordToggle.setAttribute("aria-label", isHidden ? "Ocultar contraseña" : "Mostrar contraseña");
});

submitButton.form.addEventListener("submit", () => {
  submitButton.disabled = true;
  submitButton.classList.add("is-loading");
});

// Al volver con el botón atrás el navegador restaura el botón bloqueado.
window.addEventListener("pageshow", () => {
  submitButton.disabled = false;
  submitButton.classList.remove("is-loading");
});

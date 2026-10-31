import { clientsApi } from "../core/api.js";
import { setButtonLoading } from "../core/dom.js";
import { validateClient, validateField } from "../core/validation.js";
import { closeDialog, setUpDialog } from "../ui/dialog.js";
import { showToast } from "../ui/toast.js";
import { notifyClientsChanged } from "./client-events.js";

const FIELD_NAMES = ["name", "email", "company", "phone", "status"];

const dialog = document.querySelector("#client-dialog");
const form = document.querySelector("#client-form");
const submitButton = form.querySelector('[type="submit"]');
const title = document.querySelector("#client-dialog-title");
const eyebrow = document.querySelector("#client-dialog-eyebrow");
const submitLabel = document.querySelector("#client-submit-label");

let editingClientId = null;

function setFieldError(fieldName, message) {
  const input = form.elements[fieldName];
  document.querySelector(`#client-${fieldName}-error`).textContent = message;
  if (message) {
    input.setAttribute("aria-invalid", "true");
  } else {
    input.removeAttribute("aria-invalid");
  }
}

function showErrors(errors) {
  FIELD_NAMES.forEach((fieldName) => setFieldError(fieldName, errors[fieldName] ?? ""));
  const firstInvalid = FIELD_NAMES.find((fieldName) => errors[fieldName]);
  if (firstInvalid) form.elements[firstInvalid].focus();
}

function readValues() {
  return Object.fromEntries(new FormData(form));
}

/** La API devuelve una lista por campo; la interfaz muestra el primer mensaje. */
function firstMessages(apiErrors) {
  return Object.fromEntries(
    Object.entries(apiErrors).map(([fieldName, messages]) => [fieldName, messages[0]]),
  );
}

export function openClientForm(client = null) {
  editingClientId = client?.id ?? null;
  form.reset();
  FIELD_NAMES.forEach((fieldName) => {
    setFieldError(fieldName, "");
    if (client) form.elements[fieldName].value = client[fieldName];
  });

  eyebrow.textContent = client ? "Editar registro" : "Nuevo registro";
  title.textContent = client ? "Editar cliente" : "Nuevo cliente";
  submitLabel.textContent = client ? "Guardar cambios" : "Guardar cliente";

  dialog.showModal();
  form.elements.name.focus();
}

async function handleSubmit(event) {
  event.preventDefault();

  const values = readValues();
  const errors = validateClient(values);
  if (Object.keys(errors).length > 0) {
    showErrors(errors);
    return;
  }

  setButtonLoading(submitButton, true);
  try {
    if (editingClientId) {
      await clientsApi.update(editingClientId, values);
    } else {
      await clientsApi.create(values);
    }
    closeDialog(dialog);
    showToast(editingClientId ? "Cliente actualizado." : "Cliente registrado.");
    notifyClientsChanged();
  } catch (error) {
    if (error.code === "VALIDATION_ERROR") {
      showErrors(firstMessages(error.errors));
    } else {
      showToast(error.message, "error");
    }
    if (error.code === "CLIENT_NOT_FOUND") {
      closeDialog(dialog);
      notifyClientsChanged();
    }
  } finally {
    setButtonLoading(submitButton, false);
  }
}

export function initClientForm() {
  setUpDialog(dialog);
  form.addEventListener("submit", handleSubmit);

  form.addEventListener("focusout", ({ target }) => {
    if (target.name && target.value) setFieldError(target.name, validateField(target.name, target.value));
  });

  form.addEventListener("input", ({ target }) => {
    if (target.getAttribute("aria-invalid") === "true") {
      setFieldError(target.name, validateField(target.name, target.value));
    }
  });

  document.addEventListener("click", (event) => {
    if (event.target.closest("[data-new-client]")) openClientForm();
  });
}

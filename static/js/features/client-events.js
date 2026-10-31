/** Avisa a la página activa, sea cual sea, que debe volver a cargar sus datos. */

const CLIENTS_CHANGED = "clients:changed";

export function notifyClientsChanged() {
  document.dispatchEvent(new CustomEvent(CLIENTS_CHANGED));
}

export function onClientsChanged(listener) {
  document.addEventListener(CLIENTS_CHANGED, listener);
}

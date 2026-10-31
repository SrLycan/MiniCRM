import { clientsApi } from "../core/api.js";
import { createDeferredActions } from "../core/utils.js";
import { closeDialog, setUpDialog } from "../ui/dialog.js";
import { showToast } from "../ui/toast.js";
import { notifyClientsChanged } from "./client-events.js";

const UNDO_WINDOW_MS = 6000;

const dialog = document.querySelector("#delete-dialog");
const nameLabel = document.querySelector("#delete-dialog-name");
const confirmButton = document.querySelector("#delete-confirm");

const pendingDeletions = createDeferredActions(UNDO_WINDOW_MS);

let clientToDelete = null;

/** Un cliente en espera de Deshacer sigue en el servidor, pero ya no se muestra. */
export function withoutPendingDeletions(results, total) {
  const clients = results.filter(({ id }) => !pendingDeletions.has(id));
  return { clients, total: total - (results.length - clients.length) };
}

export function openDeleteDialog(client) {
  clientToDelete = client;
  nameLabel.textContent = client.name;
  dialog.showModal();
}

async function deleteClient(client, { keepalive = false } = {}) {
  try {
    await clientsApi.remove(client.id, { keepalive });
  } catch (error) {
    if (keepalive) return;
    if (error.code !== "CLIENT_NOT_FOUND") {
      showToast(`No pudimos eliminar a ${client.name}. ${error.message}`, "error");
    }
  }
  if (!keepalive) notifyClientsChanged();
}

function undoDelete(client) {
  if (!pendingDeletions.cancel(client.id)) return;
  showToast(`${client.name} sigue en tu cartera.`);
  notifyClientsChanged();
}

function confirmDelete() {
  const client = clientToDelete;
  pendingDeletions.schedule(client.id, (options) => deleteClient(client, options));

  const undoButton = showToast(`Se eliminó a ${client.name}.`, "success", {
    actionLabel: "Deshacer",
    onAction: () => undoDelete(client),
    durationMs: UNDO_WINDOW_MS,
  });
  // El botón que abrió el diálogo desaparece con la fila, así que el foco no puede volver ahí.
  dialog.addEventListener("close", () => undoButton.focus(), { once: true });

  closeDialog(dialog);
  notifyClientsChanged();
}

export function initDeleteDialog() {
  setUpDialog(dialog);
  confirmButton.addEventListener("click", confirmDelete);
  window.addEventListener("pagehide", () => pendingDeletions.flush({ keepalive: true }));
}

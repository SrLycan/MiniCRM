import { clientsApi } from "../core/api.js";
import { setButtonLoading } from "../core/dom.js";
import { closeDialog, setUpDialog } from "../ui/dialog.js";
import { showToast } from "../ui/toast.js";
import { notifyClientsChanged } from "./client-events.js";

const dialog = document.querySelector("#delete-dialog");
const nameLabel = document.querySelector("#delete-dialog-name");
const confirmButton = document.querySelector("#delete-confirm");

let clientToDelete = null;

export function openDeleteDialog(client) {
  clientToDelete = client;
  nameLabel.textContent = client.name;
  dialog.showModal();
}

async function confirmDelete() {
  setButtonLoading(confirmButton, true);
  try {
    await clientsApi.remove(clientToDelete.id);
    showToast("Cliente eliminado.");
    closeDialog(dialog);
    notifyClientsChanged();
  } catch (error) {
    showToast(error.message, "error");
    if (error.code === "CLIENT_NOT_FOUND") {
      closeDialog(dialog);
      notifyClientsChanged();
    }
  } finally {
    setButtonLoading(confirmButton, false);
  }
}

export function initDeleteDialog() {
  setUpDialog(dialog);
  confirmButton.addEventListener("click", confirmDelete);
}

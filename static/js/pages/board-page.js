import { ApiError, clientsApi } from "../core/api.js";
import { clientCountLabel, debounce } from "../core/utils.js";
import {
  boardStatuses,
  initBoardDragging,
  moveCard,
  renderBoard,
  renderBoardSkeleton,
} from "../features/client-board.js";
import { openDeleteDialog, withoutPendingDeletions } from "../features/client-delete.js";
import { onClientsChanged } from "../features/client-events.js";
import { openClientForm } from "../features/client-form.js";
import { renderListState } from "../features/list-state.js";
import { showToast } from "../ui/toast.js";

const SEARCH_DELAY_MS = 250;
const COLUMN_SIZE = 50;

const board = document.querySelector("#client-board");
const stateBox = document.querySelector("#client-state");
const countLabel = document.querySelector("#client-count");
const searchInput = document.querySelector("#client-search");

let searchText = new URLSearchParams(location.search).get("q") ?? "";
let currentClients = [];
let activeRequest = null;
const movingClientIds = new Set();

function syncUrl() {
  const query = searchText ? `?${new URLSearchParams({ q: searchText })}` : location.pathname;
  history.replaceState(null, "", query);
}

function showState(content) {
  renderListState(stateBox, content);
  board.hidden = true;
}

function hideState() {
  stateBox.hidden = true;
  board.hidden = false;
}

function renderEmptyState() {
  if (searchText) {
    showState({
      title: "Sin resultados",
      text: "Ningún cliente coincide con tu búsqueda.",
      actionLabel: "Limpiar búsqueda",
      onAction: () => applySearch(""),
    });
  } else {
    showState({
      title: "Aún no hay clientes",
      text: "Registra el primero para empezar a llenar tu órbita.",
      actionLabel: "Registrar cliente",
      onAction: () => openClientForm(),
    });
  }
}

async function loadColumn(status, signal) {
  const params = { status, page_size: COLUMN_SIZE, ...(searchText && { q: searchText }) };
  const { results, pagination } = await clientsApi.list(params, signal);
  return [status, withoutPendingDeletions(results, pagination.total)];
}

async function loadBoard({ showSkeleton = true } = {}) {
  activeRequest?.abort();
  const request = new AbortController();
  activeRequest = request;

  if (showSkeleton) {
    hideState();
    renderBoardSkeleton(board);
  }

  try {
    const statuses = boardStatuses(board).map(({ value }) => value);
    const columns = Object.fromEntries(
      await Promise.all(statuses.map((status) => loadColumn(status, request.signal))),
    );
    currentClients = Object.values(columns).flatMap(({ clients }) => clients);
    const total = Object.values(columns).reduce((sum, column) => sum + column.total, 0);

    hideState();
    renderBoard(board, columns);
    countLabel.textContent = clientCountLabel(total);
    if (total === 0) renderEmptyState();
  } catch (error) {
    if (error.name === "AbortError") return;
    countLabel.textContent = "";
    showState({
      title: "No pudimos cargar el tablero",
      text: error instanceof ApiError ? error.message : "Ocurrió un error inesperado.",
      actionLabel: "Reintentar",
      onAction: () => loadBoard(),
    });
  }
}

function applySearch(value) {
  searchText = value;
  searchInput.value = value;
  syncUrl();
  loadBoard();
}

/** Mueve la tarjeta al instante y la devuelve a su columna si el servidor lo rechaza. */
async function moveClient(clientId, status) {
  const client = currentClients.find(({ id }) => id === clientId);
  if (!client || client.status === status) return;

  // Un cambio pendiente manda: se descarta el segundo para no cruzar respuestas.
  if (movingClientIds.has(clientId)) return;

  movingClientIds.add(clientId);
  const previousStatus = client.status;
  moveCard(board, clientId, status);

  try {
    Object.assign(client, await clientsApi.updateStatus(clientId, status));
    showToast(`${client.name} pasó a ${client.status_label}.`);
  } catch (error) {
    moveCard(board, clientId, previousStatus);
    showToast(error.message, "error");
    if (error.code === "CLIENT_NOT_FOUND") loadBoard({ showSkeleton: false });
  } finally {
    movingClientIds.delete(clientId);
  }
}

const searchClients = debounce((value) => applySearch(value.trim()), SEARCH_DELAY_MS);
searchInput.addEventListener("input", () => searchClients(searchInput.value));

board.addEventListener("click", (event) => {
  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) return;

  const clientId = Number(actionButton.closest("[data-client-id]").dataset.clientId);
  const client = currentClients.find(({ id }) => id === clientId);
  if (actionButton.dataset.action === "edit") openClientForm(client);
  else openDeleteDialog(client);
});

board.addEventListener("change", ({ target }) => {
  if (!target.matches("[data-status-select]")) return;

  const clientId = Number(target.closest("[data-client-id]").dataset.clientId);
  const { status } = currentClients.find(({ id }) => id === clientId);
  if (movingClientIds.has(clientId)) target.value = status;
  else moveClient(clientId, target.value);
});

initBoardDragging(board, moveClient);
onClientsChanged(() => loadBoard({ showSkeleton: false }));

searchInput.value = searchText;
loadBoard();

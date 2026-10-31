import { ApiError, clientsApi } from "../core/api.js";
import { createElement, setButtonLoading } from "../core/dom.js";
import { clientCountLabel, debounce } from "../core/utils.js";
import {
  boardStatuses,
  initBoardDragging,
  moveCard,
  renderBoard,
  renderBoardSkeleton,
} from "../features/client-board.js";
import { openDeleteDialog } from "../features/client-delete.js";
import { notifyClientsChanged, onClientsChanged } from "../features/client-events.js";
import { openClientForm } from "../features/client-form.js";
import { renderRows, renderSkeleton } from "../features/client-table.js";
import { showToast } from "../ui/toast.js";

const SEARCH_DELAY_MS = 250;
const BOARD_COLUMN_SIZE = 50;

const toolbar = document.querySelector("#client-toolbar");
const table = document.querySelector("#client-table");
const rows = document.querySelector("#client-rows");
const board = document.querySelector("#client-board");
const viewButtons = [...document.querySelectorAll(".view-switch__button")];
const simulateButton = document.querySelector("#simulate-whatsapp");
const stateBox = document.querySelector("#client-state");
const countLabel = document.querySelector("#client-count");
const pagination = document.querySelector("#client-pagination");
const searchInput = document.querySelector("#client-search");
const sortSelect = document.querySelector("#client-sort");
const statusChips = [...document.querySelectorAll(".chip")];
const sortableHeaders = [...document.querySelectorAll("th[data-sort]")];

const urlParams = new URLSearchParams(location.search);
const state = {
  view: urlParams.get("view") === "board" ? "board" : "table",
  q: urlParams.get("q") ?? "",
  status: urlParams.get("status") ?? "",
  sort: urlParams.get("sort") ?? "",
  page: Number(urlParams.get("page")) || 1,
};

let currentClients = [];
let activeRequest = null;
const movingClientIds = new Set();

function queryParams() {
  const params = {};
  if (state.q) params.q = state.q;
  if (state.status) params.status = state.status;
  if (state.sort) params.sort = state.sort;
  if (state.page > 1) params.page = state.page;
  return params;
}

function isBoardView() {
  return state.view === "board";
}

function syncUrl() {
  const params = { ...(isBoardView() && { view: "board" }), ...queryParams() };
  const query = new URLSearchParams(params).toString();
  history.replaceState(null, "", query ? `?${query}` : location.pathname);
}

function syncFilters() {
  toolbar.dataset.view = state.view;
  viewButtons.forEach((button) => {
    button.setAttribute("aria-pressed", String(button.dataset.view === state.view));
  });
  searchInput.value = state.q;
  sortSelect.value = state.sort;
  statusChips.forEach((chip) => {
    chip.setAttribute("aria-pressed", String(chip.dataset.status === state.status));
  });
  sortableHeaders.forEach((header) => {
    const field = header.dataset.sort;
    if (state.sort === field) header.setAttribute("aria-sort", "ascending");
    else if (state.sort === `-${field}`) header.setAttribute("aria-sort", "descending");
    else header.removeAttribute("aria-sort");
  });
}

function hasActiveFilters() {
  return Boolean(state.q || (state.status && !isBoardView()));
}

function showState({ title, text, actionLabel, onAction }) {
  const button = createElement("button", { class: "button button--ghost", type: "button" }, actionLabel);
  button.addEventListener("click", onAction);
  stateBox.replaceChildren(
    createElement("div", { class: "table-state__orbit", "aria-hidden": "true" }),
    createElement("h2", { class: "table-state__title" }, title),
    createElement("p", {}, text),
    button,
  );
  stateBox.hidden = false;
  table.hidden = true;
  board.hidden = true;
}

function hideState() {
  stateBox.hidden = true;
  table.hidden = isBoardView();
  board.hidden = !isBoardView();
}

function clearFilters() {
  Object.assign(state, { q: "", status: "", page: 1 });
  applyChanges();
}

function renderEmptyState() {
  if (hasActiveFilters()) {
    showState({
      title: "Sin resultados",
      text: "Ningún cliente coincide con tu búsqueda.",
      actionLabel: "Limpiar filtros",
      onAction: clearFilters,
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

function createPageButton(label, page, { isCurrent = false, isDisabled = false, ariaLabel } = {}) {
  const button = createElement(
    "button",
    { class: "page-button", type: "button", "aria-label": ariaLabel ?? `Página ${page}` },
    String(label),
  );
  button.disabled = isDisabled;
  if (isCurrent) button.setAttribute("aria-current", "page");
  button.addEventListener("click", () => {
    state.page = page;
    applyChanges();
  });
  return button;
}

function renderPagination({ page, pages }) {
  if (pages <= 1) {
    pagination.replaceChildren();
    return;
  }

  const pageButtons = Array.from({ length: pages }, (_, index) =>
    createPageButton(index + 1, index + 1, { isCurrent: index + 1 === page }),
  );
  pagination.replaceChildren(
    createPageButton("‹", page - 1, { isDisabled: page === 1, ariaLabel: "Página anterior" }),
    ...pageButtons,
    createPageButton("›", page + 1, { isDisabled: page === pages, ariaLabel: "Página siguiente" }),
  );
}

async function loadTable(signal) {
  const { results, pagination: pageInfo } = await clientsApi.list(queryParams(), signal);
  currentClients = results;
  state.page = pageInfo.page;
  syncUrl();

  hideState();
  renderRows(rows, results);
  renderPagination(pageInfo);
  return pageInfo.total;
}

async function loadColumn(status, signal) {
  const params = { status, page_size: BOARD_COLUMN_SIZE, ...(state.q && { q: state.q }) };
  const { results, pagination: pageInfo } = await clientsApi.list(params, signal);
  return [status, { clients: results, total: pageInfo.total }];
}

async function loadBoard(signal) {
  const statuses = boardStatuses(board).map(({ value }) => value);
  const columns = Object.fromEntries(
    await Promise.all(statuses.map((status) => loadColumn(status, signal))),
  );
  currentClients = Object.values(columns).flatMap(({ clients }) => clients);

  hideState();
  renderBoard(board, columns);
  pagination.replaceChildren();
  return Object.values(columns).reduce((sum, { total }) => sum + total, 0);
}

async function loadClients({ showSkeleton = true } = {}) {
  activeRequest?.abort();
  const request = new AbortController();
  activeRequest = request;

  if (showSkeleton) {
    hideState();
    if (isBoardView()) renderBoardSkeleton(board);
    else renderSkeleton(rows);
  }
  table.setAttribute("aria-busy", "true");

  try {
    const load = isBoardView() ? loadBoard : loadTable;
    const total = await load(request.signal);
    countLabel.textContent = clientCountLabel(total);
    if (total === 0) renderEmptyState();
  } catch (error) {
    if (error.name === "AbortError") return;
    const message = error instanceof ApiError ? error.message : "Ocurrió un error inesperado.";
    countLabel.textContent = "";
    pagination.replaceChildren();
    showState({
      title: "No pudimos cargar los clientes",
      text: message,
      actionLabel: "Reintentar",
      onAction: () => loadClients(),
    });
  } finally {
    if (activeRequest === request) table.setAttribute("aria-busy", "false");
  }
}

function applyChanges(options) {
  syncFilters();
  syncUrl();
  loadClients(options);
}

function toggleSort(field) {
  if (state.sort === field) state.sort = `-${field}`;
  else if (state.sort === `-${field}`) state.sort = "";
  else state.sort = field;
  state.page = 1;
  applyChanges();
}

const searchClients = debounce((value) => {
  state.q = value.trim();
  state.page = 1;
  applyChanges();
}, SEARCH_DELAY_MS);

viewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    if (button.dataset.view === state.view) return;
    state.view = button.dataset.view;
    applyChanges();
  });
});

simulateButton.addEventListener("click", simulateWhatsAppMessage);

searchInput.addEventListener("input", () => searchClients(searchInput.value));

statusChips.forEach((chip) => {
  chip.addEventListener("click", () => {
    state.status = chip.dataset.status;
    state.page = 1;
    applyChanges();
  });
});

sortSelect.addEventListener("change", () => {
  state.sort = sortSelect.value;
  state.page = 1;
  applyChanges();
});

sortableHeaders.forEach((header) => {
  header.querySelector("button").addEventListener("click", () => toggleSort(header.dataset.sort));
});

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
    if (error.code === "CLIENT_NOT_FOUND") loadClients({ showSkeleton: false });
  } finally {
    movingClientIds.delete(clientId);
  }
}

async function simulateWhatsAppMessage() {
  setButtonLoading(simulateButton, true);
  try {
    const client = await clientsApi.simulateWhatsApp();
    showToast(`Simulación: ${client.name} escribió por WhatsApp y quedó como prospecto.`);
    notifyClientsChanged();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setButtonLoading(simulateButton, false);
  }
}

function handleClientAction(event) {
  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) return;

  const clientId = Number(actionButton.closest("[data-client-id]").dataset.clientId);
  const client = currentClients.find(({ id }) => id === clientId);
  if (actionButton.dataset.action === "edit") openClientForm(client);
  else openDeleteDialog(client);
}

rows.addEventListener("click", handleClientAction);
board.addEventListener("click", handleClientAction);

board.addEventListener("change", ({ target }) => {
  if (!target.matches("[data-status-select]")) return;

  const clientId = Number(target.closest("[data-client-id]").dataset.clientId);
  const { status } = currentClients.find(({ id }) => id === clientId);
  if (movingClientIds.has(clientId)) target.value = status;
  else moveClient(clientId, target.value);
});

initBoardDragging(board, moveClient);

onClientsChanged(() => loadClients({ showSkeleton: false }));

syncFilters();
loadClients();

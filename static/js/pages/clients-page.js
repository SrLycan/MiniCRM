import { ApiError, clientsApi } from "../core/api.js";
import { createElement } from "../core/dom.js";
import { clientCountLabel, debounce } from "../core/utils.js";
import { openDeleteDialog } from "../features/client-delete.js";
import { onClientsChanged } from "../features/client-events.js";
import { openClientForm } from "../features/client-form.js";
import { renderRows, renderSkeleton } from "../features/client-table.js";

const SEARCH_DELAY_MS = 250;

const table = document.querySelector("#client-table");
const rows = document.querySelector("#client-rows");
const stateBox = document.querySelector("#client-state");
const countLabel = document.querySelector("#client-count");
const pagination = document.querySelector("#client-pagination");
const searchInput = document.querySelector("#client-search");
const sortSelect = document.querySelector("#client-sort");
const statusChips = [...document.querySelectorAll(".chip")];
const sortableHeaders = [...document.querySelectorAll("th[data-sort]")];

const urlParams = new URLSearchParams(location.search);
const state = {
  q: urlParams.get("q") ?? "",
  status: urlParams.get("status") ?? "",
  sort: urlParams.get("sort") ?? "",
  page: Number(urlParams.get("page")) || 1,
};

let currentClients = [];
let activeRequest = null;

function queryParams() {
  const params = {};
  if (state.q) params.q = state.q;
  if (state.status) params.status = state.status;
  if (state.sort) params.sort = state.sort;
  if (state.page > 1) params.page = state.page;
  return params;
}

function syncUrl() {
  const query = new URLSearchParams(queryParams()).toString();
  history.replaceState(null, "", query ? `?${query}` : location.pathname);
}

function syncFilters() {
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
  return Boolean(state.q || state.status);
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
}

function hideState() {
  stateBox.hidden = true;
  table.hidden = false;
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

async function loadClients({ showSkeleton = true } = {}) {
  activeRequest?.abort();
  const request = new AbortController();
  activeRequest = request;

  if (showSkeleton) {
    hideState();
    renderSkeleton(rows);
  }
  table.setAttribute("aria-busy", "true");

  try {
    const { results, pagination: pageInfo } = await clientsApi.list(queryParams(), request.signal);
    currentClients = results;
    state.page = pageInfo.page;
    syncUrl();

    hideState();
    renderRows(rows, results);
    renderPagination(pageInfo);
    countLabel.textContent = clientCountLabel(pageInfo.total);
    if (results.length === 0) renderEmptyState();
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

rows.addEventListener("click", (event) => {
  const actionButton = event.target.closest("[data-action]");
  if (!actionButton) return;

  const clientId = Number(actionButton.closest("tr").dataset.clientId);
  const client = currentClients.find(({ id }) => id === clientId);
  if (actionButton.dataset.action === "edit") openClientForm(client);
  else openDeleteDialog(client);
});

onClientsChanged(() => loadClients({ showSkeleton: false }));

syncFilters();
loadClients();

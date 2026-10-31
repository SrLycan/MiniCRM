import { createAvatar, createElement } from "../core/dom.js";
import { boardColumnNote } from "../core/utils.js";
import { createActionButton } from "./client-table.js";

const SKELETON_CARDS = 3;

function columnsOf(board) {
  return [...board.querySelectorAll(".board-column")];
}

function cardsOf(column) {
  return column.querySelector("[data-column-cards]");
}

function createStatusSelect(client, statuses) {
  const options = statuses.map(({ value, label }) => {
    const option = createElement("option", { value }, label);
    option.selected = value === client.status;
    return option;
  });
  return createElement(
    "select",
    {
      class: "input board-card__status",
      "data-status-select": "",
      "aria-label": `Estado de ${client.name}`,
    },
    ...options,
  );
}

function createCard(client, index, statuses) {
  const card = createElement("article", {
    class: "board-card",
    style: `--order: ${index}`,
    draggable: "true",
    "data-client-id": client.id,
  });

  const identity = createElement(
    "div",
    { class: "client-identity" },
    createAvatar(client.name),
    createElement("span", { class: "board-card__name" }, client.name),
  );
  card.append(identity);

  if (client.company) {
    card.append(createElement("p", { class: "board-card__company" }, client.company));
  }

  card.append(
    createElement(
      "div",
      { class: "board-card__footer" },
      createStatusSelect(client, statuses),
      createActionButton({ icon: "edit", label: `Editar a ${client.name}`, action: "edit" }),
      createActionButton({
        icon: "trash",
        label: `Eliminar a ${client.name}`,
        action: "delete",
        isDanger: true,
      }),
    ),
  );
  return card;
}

function updateColumnSummary(column, total) {
  const note = column.querySelector("[data-column-note]");
  const text = boardColumnNote(cardsOf(column).children.length, total);
  column.dataset.total = total;
  column.querySelector("[data-column-count]").textContent = total;
  note.textContent = text;
  note.hidden = !text;
}

function columnOf(board, status) {
  return board.querySelector(`.board-column[data-status="${status}"]`);
}

function findCard(board, clientId) {
  return board.querySelector(`.board-card[data-client-id="${clientId}"]`);
}

/** Pasa la tarjeta a otra columna y conserva el foco de quien usa el teclado. */
export function moveCard(board, clientId, status) {
  const card = findCard(board, clientId);
  if (!card) return;

  const source = card.closest(".board-column");
  const target = columnOf(board, status);
  const select = card.querySelector("[data-status-select]");
  const hadFocus = document.activeElement === select;

  select.value = status;
  if (source === target) return;

  cardsOf(target).prepend(card);
  updateColumnSummary(source, Number(source.dataset.total) - 1);
  updateColumnSummary(target, Number(target.dataset.total) + 1);
  if (hadFocus) select.focus();
}

/** Arrastre con ratón; en táctil y con teclado se usa el selector de cada tarjeta. */
export function initBoardDragging(board, onMove) {
  let draggedCard = null;

  function clearDropTargets() {
    board.querySelectorAll(".is-drop-target").forEach((column) => {
      column.classList.remove("is-drop-target");
    });
  }

  board.addEventListener("dragstart", (event) => {
    draggedCard = event.target.closest?.(".board-card") ?? null;
    if (!draggedCard) return;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", draggedCard.dataset.clientId);
    draggedCard.classList.add("is-dragging");
  });

  board.addEventListener("dragover", (event) => {
    const column = event.target.closest(".board-column");
    if (!draggedCard || !column) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    if (column.classList.contains("is-drop-target")) return;
    clearDropTargets();
    column.classList.add("is-drop-target");
  });

  board.addEventListener("dragleave", (event) => {
    if (!board.contains(event.relatedTarget)) clearDropTargets();
  });

  board.addEventListener("drop", (event) => {
    const column = event.target.closest(".board-column");
    if (!draggedCard || !column) return;
    event.preventDefault();
    onMove(Number(draggedCard.dataset.clientId), column.dataset.status);
  });

  board.addEventListener("dragend", () => {
    draggedCard?.classList.remove("is-dragging");
    draggedCard = null;
    clearDropTargets();
  });
}

export function boardStatuses(board) {
  return columnsOf(board).map(({ dataset }) => ({ value: dataset.status, label: dataset.label }));
}

export function renderBoard(board, columns) {
  const statuses = boardStatuses(board);
  columnsOf(board).forEach((column) => {
    const { clients, total } = columns[column.dataset.status];
    cardsOf(column).replaceChildren(
      ...clients.map((client, index) => createCard(client, index, statuses)),
    );
    updateColumnSummary(column, total);
  });
}

export function renderBoardSkeleton(board) {
  columnsOf(board).forEach((column) => {
    const cards = Array.from({ length: SKELETON_CARDS }, () =>
      createElement(
        "div",
        { class: "board-card board-card--skeleton" },
        createElement("span", { class: "skeleton" }),
        createElement("span", { class: "skeleton" }),
      ),
    );
    cardsOf(column).replaceChildren(...cards);
    column.querySelector("[data-column-count]").textContent = "";
    column.querySelector("[data-column-note]").hidden = true;
  });
}

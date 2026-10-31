import { createClientIdentity, createElement, createIcon, createStatusBadge } from "../core/dom.js";

const SKELETON_ROWS = 6;
const COLUMN_COUNT = 6;

function createCell(label, ...content) {
  const isEmpty = content.length === 1 && content[0] === "";
  return createElement(
    "td",
    { "data-label": label, ...(isEmpty && { class: "is-empty" }) },
    ...(isEmpty ? ["Sin dato"] : content),
  );
}

export function createActionButton({ icon, label, action, isDanger = false }) {
  const className = isDanger ? "icon-button icon-button--danger" : "icon-button";
  return createElement(
    "button",
    { class: className, type: "button", "data-action": action, "aria-label": label, title: label },
    createIcon(icon),
  );
}

function createEmailContent({ email }) {
  if (!email) return "";
  return createElement("a", { class: "client-email", href: `mailto:${email}`, title: email }, email);
}

function createRow(client, index) {
  const row = createElement("tr", {
    class: "client-row",
    style: `--order: ${index}`,
    "data-client-id": client.id,
  });

  row.append(
    createCell("Nombre", createClientIdentity(client)),
    createCell("Empresa", client.company),
    createCell("Correo", createEmailContent(client)),
    createCell("Teléfono", client.phone),
    createCell("Estado", createStatusBadge(client)),
    createElement(
      "td",
      { class: "client-actions" },
      createActionButton({ icon: "edit", label: `Editar a ${client.name}`, action: "edit" }),
      createActionButton({
        icon: "trash",
        label: `Eliminar a ${client.name}`,
        action: "delete",
        isDanger: true,
      }),
    ),
  );
  return row;
}

export function renderRows(tbody, clients) {
  tbody.replaceChildren(...clients.map(createRow));
}

export function renderSkeleton(tbody) {
  const rows = Array.from({ length: SKELETON_ROWS }, () => {
    const cells = Array.from({ length: COLUMN_COUNT }, () =>
      createElement("td", {}, createElement("span", { class: "skeleton" })),
    );
    return createElement("tr", { class: "client-row client-row--skeleton" }, ...cells);
  });
  tbody.replaceChildren(...rows);
}

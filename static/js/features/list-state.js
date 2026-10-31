import { createElement } from "../core/dom.js";

/** Pinta el aviso de lista vacía, sin resultados o con error, con su acción. */
export function renderListState(box, { title, text, actionLabel, onAction }) {
  const button = createElement("button", { class: "button button--ghost", type: "button" }, actionLabel);
  button.addEventListener("click", onAction);
  box.replaceChildren(
    createElement("div", { class: "table-state__orbit", "aria-hidden": "true" }),
    createElement("h2", { class: "table-state__title" }, title),
    createElement("p", {}, text),
    button,
  );
  box.hidden = false;
}

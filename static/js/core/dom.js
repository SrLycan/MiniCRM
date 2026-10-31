import { hueFromText, initials } from "./utils.js";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

/**
 * Crea un elemento. El texto siempre entra como nodo de texto, nunca como HTML,
 * así que los datos de un cliente no pueden inyectar marcado.
 */
export function createElement(tag, attributes = {}, ...children) {
  const element = document.createElement(tag);
  for (const [name, value] of Object.entries(attributes)) {
    element.setAttribute(name, value);
  }
  element.append(...children);
  return element;
}

export function createIcon(name) {
  const svg = document.createElementNS(SVG_NAMESPACE, "svg");
  const use = document.createElementNS(SVG_NAMESPACE, "use");
  svg.setAttribute("aria-hidden", "true");
  use.setAttribute("href", `#icon-${name}`);
  svg.append(use);
  return svg;
}

export function createAvatar(name) {
  return createElement(
    "span",
    { class: "avatar", style: `--avatar-hue: ${hueFromText(name)}`, "aria-hidden": "true" },
    initials(name),
  );
}

export function createStatusBadge(client) {
  return createElement("span", { class: `badge badge--${client.status}` }, client.status_label);
}

/** Avatar, nombre y, si vino por WhatsApp, la insignia de origen. */
export function createClientIdentity(client) {
  const details = createElement(
    "div",
    { class: "client-identity__details" },
    createElement("span", { class: "client-identity__name" }, client.name),
  );
  if (client.source === "whatsapp") {
    details.append(createElement("span", { class: "badge badge--source" }, "WhatsApp"));
  }
  return createElement("div", { class: "client-identity" }, createAvatar(client.name), details);
}

export function setButtonLoading(button, isLoading) {
  button.disabled = isLoading;
  button.classList.toggle("is-loading", isLoading);
}

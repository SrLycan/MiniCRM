import { createAvatar, createElement, createStatusBadge } from "../core/dom.js";
import { formatMessageTime } from "../core/utils.js";

function createConversationItem({ client, last_message: lastMessage }, activeClientId) {
  const prefix = lastMessage.direction === "out" ? "Tú: " : "";
  const button = createElement(
    "button",
    { class: "chat-item", type: "button", "data-client-id": client.id },
    createAvatar(client.name),
    createElement(
      "span",
      { class: "chat-item__text" },
      createElement("span", { class: "chat-item__name" }, client.name),
      createElement("span", { class: "chat-item__preview" }, `${prefix}${lastMessage.body}`),
    ),
    createElement("time", { class: "chat-item__time" }, formatMessageTime(lastMessage.created_at)),
  );
  if (client.id === activeClientId) button.setAttribute("aria-current", "true");
  return createElement("li", {}, button);
}

export function renderConversations(list, conversations, activeClientId) {
  list.replaceChildren(
    ...conversations.map((conversation) => createConversationItem(conversation, activeClientId)),
  );
}

export function createMessageBubble(message) {
  const label = message.direction === "out" ? "Tú" : "Cliente";
  return createElement(
    "li",
    { class: `chat-bubble chat-bubble--${message.direction}` },
    createElement("span", { class: "visually-hidden" }, `${label}: `),
    createElement("p", { class: "chat-bubble__text" }, message.body),
    createElement("time", { class: "chat-bubble__time" }, formatMessageTime(message.created_at)),
  );
}

export function renderMessages(list, messages) {
  list.replaceChildren(...messages.map(createMessageBubble));
  list.scrollTop = list.scrollHeight;
}

export function appendMessage(list, message) {
  list.append(createMessageBubble(message));
  list.scrollTop = list.scrollHeight;
}

/** Muestra los datos del cliente para que se vea que el chat es suyo. */
export function renderClientHeader(box, client) {
  const details = [client.phone, client.company || "Sin empresa", client.email || "Sin correo"];
  box.replaceChildren(
    createAvatar(client.name),
    createElement(
      "div",
      { class: "chat-header__text" },
      createElement(
        "h2",
        { class: "chat-header__name" },
        client.name,
        " ",
        createStatusBadge(client),
      ),
      createElement("p", { class: "chat-header__details" }, details.filter(Boolean).join(" · ")),
    ),
  );
}

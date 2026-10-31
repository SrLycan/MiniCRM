import { clientsApi, conversationsApi } from "../core/api.js";
import { setButtonLoading } from "../core/dom.js";
import {
  appendMessage,
  renderClientHeader,
  renderConversations,
  renderMessages,
} from "../features/chat-view.js";
import { onClientsChanged } from "../features/client-events.js";
import { openClientForm } from "../features/client-form.js";
import { renderListState } from "../features/list-state.js";
import { showToast } from "../ui/toast.js";

const chat = document.querySelector("#chat");
const conversationList = document.querySelector("#conversation-list");
const conversationState = document.querySelector("#conversation-state");
const placeholder = document.querySelector("#chat-placeholder");
const room = document.querySelector("#chat-room");
const clientBox = document.querySelector("#chat-client");
const messageList = document.querySelector("#chat-messages");
const form = document.querySelector("#chat-form");
const input = document.querySelector("#chat-input");
const sendButton = document.querySelector("#chat-send");
const errorLabel = document.querySelector("#chat-error");
const unavailableNotice = document.querySelector("#chat-unavailable");
const simulateReplyButton = document.querySelector("#chat-simulate-reply");
const simulateNewButton = document.querySelector("#simulate-new-chat");

let activeClient = null;
let conversations = [];
let openRequest = null;

function syncUrl() {
  const query = activeClient ? `?cliente=${activeClient.id}` : location.pathname;
  history.replaceState(null, "", query);
}

function showPane(pane) {
  chat.dataset.pane = pane;
}

function closeConversation() {
  openRequest?.abort();
  activeClient = null;
  room.hidden = true;
  placeholder.hidden = false;
  showPane("list");
  syncUrl();
  renderConversations(conversationList, conversations, null);
}

async function loadConversations() {
  try {
    ({ results: conversations } = await conversationsApi.list());
    renderConversations(conversationList, conversations, activeClient?.id);
    if (conversations.length > 0) {
      conversationState.hidden = true;
    } else {
      renderListState(conversationState, {
        title: "Aún no hay conversaciones",
        text: "Simula el mensaje de un cliente nuevo o abre el chat de uno desde Clientes.",
        actionLabel: "Simular cliente nuevo",
        onAction: simulateNewClient,
      });
    }
  } catch (error) {
    conversationList.replaceChildren();
    renderListState(conversationState, {
      title: "No pudimos cargar los chats",
      text: error.message,
      actionLabel: "Reintentar",
      onAction: loadConversations,
    });
  }
}

async function openConversation(clientId) {
  openRequest?.abort();
  const request = new AbortController();
  openRequest = request;

  try {
    const { client, messages, can_chat: canChat } = await conversationsApi.get(
      clientId,
      request.signal,
    );
    const isSameChat = activeClient?.id === client.id;
    activeClient = client;

    placeholder.hidden = true;
    room.hidden = false;
    form.hidden = !canChat;
    unavailableNotice.hidden = canChat;
    if (!isSameChat) {
      input.value = "";
      errorLabel.textContent = "";
    }

    renderClientHeader(clientBox, client);
    renderMessages(messageList, messages);
    renderConversations(conversationList, conversations, client.id);
    showPane("room");
    syncUrl();
  } catch (error) {
    if (error.name === "AbortError") return;
    showToast(error.message, "error");
    closeConversation();
  }
}

async function sendMessage(event) {
  event.preventDefault();
  const body = input.value.trim();
  if (!body) {
    errorLabel.textContent = "Escribe un mensaje.";
    input.focus();
    return;
  }

  errorLabel.textContent = "";
  setButtonLoading(sendButton, true);
  try {
    appendMessage(messageList, await conversationsApi.send(activeClient.id, body));
    input.value = "";
    await loadConversations();
  } catch (error) {
    // El texto queda en la caja para no perderlo si el envío falla.
    errorLabel.textContent = error.errors?.body?.[0] ?? error.message;
    if (error.code === "CLIENT_NOT_FOUND") closeConversation();
  } finally {
    setButtonLoading(sendButton, false);
    input.focus();
  }
}

async function simulateReply() {
  setButtonLoading(simulateReplyButton, true);
  try {
    appendMessage(messageList, await conversationsApi.simulateReply(activeClient.id));
    await loadConversations();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setButtonLoading(simulateReplyButton, false);
  }
}

async function simulateNewClient() {
  setButtonLoading(simulateNewButton, true);
  try {
    const client = await clientsApi.simulateWhatsApp();
    await loadConversations();
    await openConversation(client.id);
    showToast(`Simulación: ${client.name} escribió por WhatsApp.`);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setButtonLoading(simulateNewButton, false);
  }
}

form.addEventListener("submit", sendMessage);

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});

conversationList.addEventListener("click", (event) => {
  const item = event.target.closest("[data-client-id]");
  if (item) openConversation(Number(item.dataset.clientId));
});

simulateReplyButton.addEventListener("click", simulateReply);
simulateNewButton.addEventListener("click", simulateNewClient);
document.querySelector("#chat-back").addEventListener("click", closeConversation);
document.querySelector("#chat-edit").addEventListener("click", () => openClientForm(activeClient));

onClientsChanged(async () => {
  await loadConversations();
  if (activeClient) await openConversation(activeClient.id);
});

await loadConversations();

const requestedClientId = Number(new URLSearchParams(location.search).get("cliente"));
if (requestedClientId) await openConversation(requestedClientId);

const CLIENTS_URL = "/api/clients/";
const CONVERSATIONS_URL = "/api/conversations/";
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

export class ApiError extends Error {
  constructor(message, { code = "UNKNOWN", status = 0, errors = {} } = {}) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.errors = errors;
  }
}

function redirectToLogin() {
  const next = encodeURIComponent(location.pathname + location.search);
  location.assign(`/login/?next=${next}`);
}

async function request(url, { method = "GET", body, signal, keepalive = false } = {}) {
  let response;
  try {
    response = await fetch(url, {
      method,
      signal,
      keepalive,
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (error) {
    if (error.name === "AbortError") throw error;
    throw new ApiError("No pudimos conectar con el servidor. Revisa tu conexión.", {
      code: "NETWORK_ERROR",
    });
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (response.ok) return data;

  if (response.status === 401) redirectToLogin();
  if (response.status === 403) {
    throw new ApiError("Tu sesión cambió. Recarga la página.", { code: "FORBIDDEN", status: 403 });
  }
  throw new ApiError(data?.message ?? "Ocurrió un error inesperado. Inténtalo de nuevo.", {
    code: data?.code,
    status: response.status,
    errors: data?.errors,
  });
}

export const clientsApi = {
  list(params, signal) {
    return request(`${CLIENTS_URL}?${new URLSearchParams(params)}`, { signal });
  },
  stats() {
    return request(`${CLIENTS_URL}stats/`);
  },
  create(values) {
    return request(CLIENTS_URL, { method: "POST", body: values });
  },
  update(id, values) {
    return request(`${CLIENTS_URL}${id}/`, { method: "PUT", body: values });
  },
  updateStatus(id, status) {
    return request(`${CLIENTS_URL}${id}/`, { method: "PATCH", body: { status } });
  },
  remove(id, { keepalive = false } = {}) {
    return request(`${CLIENTS_URL}${id}/`, { method: "DELETE", keepalive });
  },
  simulateWhatsApp() {
    return request(`${CLIENTS_URL}simulate-whatsapp/`, { method: "POST" });
  },
};

export const conversationsApi = {
  list() {
    return request(CONVERSATIONS_URL);
  },
  get(clientId, signal) {
    return request(`${CONVERSATIONS_URL}${clientId}/`, { signal });
  },
  send(clientId, body) {
    return request(`${CONVERSATIONS_URL}${clientId}/messages/`, { method: "POST", body: { body } });
  },
  simulateReply(clientId) {
    return request(`${CONVERSATIONS_URL}${clientId}/simulate-reply/`, { method: "POST" });
  },
};

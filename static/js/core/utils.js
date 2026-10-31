/** Funciones puras, sin DOM, para poder probarlas con node:test. */

export function debounce(callback, waitMs) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => callback(...args), waitMs);
  };
}

/**
 * Guarda acciones que se ejecutan tras una espera, salvo que se cancelen antes.
 * `flush` las ejecuta de inmediato con las opciones recibidas, para no perderlas al salir.
 */
export function createDeferredActions(delayMs) {
  const pending = new Map();

  function take(id) {
    const entry = pending.get(id);
    if (!entry) return null;
    clearTimeout(entry.timeoutId);
    pending.delete(id);
    return entry.action;
  }

  return {
    schedule(id, action) {
      take(id);
      const timeoutId = setTimeout(() => take(id)?.(), delayMs);
      pending.set(id, { action, timeoutId });
    },
    cancel(id) {
      return take(id) !== null;
    },
    has(id) {
      return pending.has(id);
    },
    flush(options) {
      for (const id of [...pending.keys()]) take(id)(options);
    },
  };
}

export function initials(name) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const first = words[0]?.[0] ?? "?";
  const last = words.length > 1 ? words[words.length - 1][0] : "";
  return `${first}${last}`.toUpperCase();
}

/** Tono estable para que cada persona conserve siempre el color de su avatar. */
export function hueFromText(text) {
  let hash = 0;
  for (const character of text) {
    hash = (hash * 31 + character.codePointAt(0)) % 360;
  }
  return hash;
}

export function percentage(part, total) {
  return total === 0 ? 0 : Math.round((part / total) * 100);
}

export function formatDate(isoDate) {
  return new Intl.DateTimeFormat("es-EC", { day: "numeric", month: "short" }).format(new Date(isoDate));
}

export function clientCountLabel(total) {
  return total === 1 ? "1 cliente" : `${total} clientes`;
}

/** Aviso de una columna del tablero; vacío si se ven todos sus clientes. */
export function boardColumnNote(shown, total) {
  return shown < total ? `Se muestran ${shown} de ${total}. Usa la búsqueda.` : "";
}

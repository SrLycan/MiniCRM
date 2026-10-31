/** Funciones puras, sin DOM, para poder probarlas con node:test. */

export function debounce(callback, waitMs) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => callback(...args), waitMs);
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

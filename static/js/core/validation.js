/**
 * Validación inmediata para el usuario. Replica las reglas de `clients/models.py`;
 * el backend sigue siendo quien decide.
 */

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_PATTERN = /^\+?[\d\s-]+$/;
const PHONE_MIN_DIGITS = 7;
const PHONE_MAX_DIGITS = 15;

const FIELD_RULES = {
  name(value) {
    if (!value) return "Ingresa el nombre del cliente.";
    if (value.length < 2) return "El nombre debe tener al menos 2 caracteres.";
    return "";
  },
  email(value) {
    if (!value) return "Ingresa el correo del cliente.";
    return EMAIL_PATTERN.test(value) ? "" : "Ingresa un correo válido.";
  },
  phone(value) {
    if (!value) return "";
    const digitCount = value.replace(/\D/g, "").length;
    const isValid =
      PHONE_PATTERN.test(value) && digitCount >= PHONE_MIN_DIGITS && digitCount <= PHONE_MAX_DIGITS;
    return isValid ? "" : "Ingresa un teléfono válido, de 7 a 15 dígitos.";
  },
};

export function validateField(fieldName, rawValue) {
  const rule = FIELD_RULES[fieldName];
  return rule ? rule(rawValue.trim()) : "";
}

export function validateClient(values) {
  const errors = {};
  for (const fieldName of Object.keys(FIELD_RULES)) {
    const message = validateField(fieldName, values[fieldName] ?? "");
    if (message) errors[fieldName] = message;
  }
  return errors;
}

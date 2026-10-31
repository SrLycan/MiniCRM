import assert from "node:assert/strict";
import { test } from "node:test";

import { validateClient, validateField } from "../../static/js/core/validation.js";

const validClient = {
  name: "Juan Pérez",
  email: "juan@example.com",
  company: "",
  phone: "0999999999",
  status: "prospect",
};

test("acepta un cliente válido con campos opcionales vacíos", () => {
  assert.deepEqual(validateClient(validClient), {});
  assert.deepEqual(validateClient({ ...validClient, phone: "" }), {});
});

test("exige nombre y correo", () => {
  const errors = validateClient({ ...validClient, name: "   ", email: "" });
  assert.equal(errors.name, "Ingresa el nombre del cliente.");
  assert.equal(errors.email, "Ingresa el correo del cliente.");
});

test("rechaza nombres de un solo carácter", () => {
  assert.match(validateField("name", " A "), /al menos 2/);
});

test("rechaza correos sin dominio", () => {
  for (const email of ["juan", "juan@", "juan@example", "ju an@example.com"]) {
    assert.equal(validateField("email", email), "Ingresa un correo válido.", email);
  }
});

test("aplica las mismas reglas de teléfono que el backend", () => {
  for (const phone of ["0999999999", "+593 99 999 9999", "02-234-5678"]) {
    assert.equal(validateField("phone", phone), "", phone);
  }
  for (const phone of ["abc", "123", "1234567890123456", "099+999999"]) {
    assert.match(validateField("phone", phone), /teléfono válido/, phone);
  }
});

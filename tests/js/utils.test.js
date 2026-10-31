import assert from "node:assert/strict";
import { test } from "node:test";

import {
  boardColumnNote,
  clientCountLabel,
  debounce,
  hueFromText,
  initials,
  percentage,
} from "../../static/js/core/utils.js";

test("boardColumnNote avisa solo si la columna no muestra a todos", () => {
  assert.equal(boardColumnNote(50, 72), "Se muestran 50 de 72. Usa la búsqueda.");
  assert.equal(boardColumnNote(12, 12), "");
  assert.equal(boardColumnNote(0, 0), "");
});

test("initials usa la primera y la última palabra", () => {
  assert.equal(initials("Ana María Ruiz"), "AR");
  assert.equal(initials("  ana "), "A");
  assert.equal(initials(""), "?");
});

test("hueFromText es estable y queda dentro del círculo de color", () => {
  assert.equal(hueFromText("Ana"), hueFromText("Ana"));
  assert.ok(hueFromText("Ñandú Ñ") >= 0 && hueFromText("Ñandú Ñ") < 360);
});

test("percentage no divide por cero", () => {
  assert.equal(percentage(1, 0), 0);
  assert.equal(percentage(1, 3), 33);
});

test("clientCountLabel respeta el singular", () => {
  assert.equal(clientCountLabel(1), "1 cliente");
  assert.equal(clientCountLabel(0), "0 clientes");
});

test("debounce ejecuta solo la última llamada", (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const calls = [];
  const debounced = debounce((value) => calls.push(value), 100);
  debounced("a");
  debounced("b");
  context.mock.timers.tick(100);
  assert.deepEqual(calls, ["b"]);
});

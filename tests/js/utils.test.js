import assert from "node:assert/strict";
import { test } from "node:test";

import {
  boardColumnNote,
  clientCountLabel,
  createDeferredActions,
  debounce,
  hueFromText,
  initials,
  percentage,
} from "../../static/js/core/utils.js";

test("createDeferredActions ejecuta la acción al terminar la espera", (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const actions = createDeferredActions(100);
  let runs = 0;
  actions.schedule(1, () => runs++);

  context.mock.timers.tick(99);
  assert.equal(runs, 0);
  assert.equal(actions.has(1), true);

  context.mock.timers.tick(1);
  assert.equal(runs, 1);
  assert.equal(actions.has(1), false);
});

test("createDeferredActions cancela una acción sin tocar las demás", (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const actions = createDeferredActions(100);
  const executed = [];
  actions.schedule(1, () => executed.push(1));
  actions.schedule(2, () => executed.push(2));

  assert.equal(actions.cancel(1), true);
  assert.equal(actions.cancel(1), false);
  context.mock.timers.tick(100);
  assert.deepEqual(executed, [2]);
});

test("createDeferredActions no cancela una acción ya ejecutada", (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const actions = createDeferredActions(100);
  actions.schedule(1, () => {});
  context.mock.timers.tick(100);
  assert.equal(actions.cancel(1), false);
});

test("createDeferredActions adelanta todo con flush y no repite", (context) => {
  context.mock.timers.enable({ apis: ["setTimeout"] });
  const actions = createDeferredActions(100);
  const received = [];
  actions.schedule(1, (options) => received.push([1, options]));
  actions.schedule(2, (options) => received.push([2, options]));

  actions.flush({ keepalive: true });
  context.mock.timers.tick(100);
  assert.deepEqual(received, [
    [1, { keepalive: true }],
    [2, { keepalive: true }],
  ]);
});

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

"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const code = fs.readFileSync(path.join(root, "app.js"), "utf8");
const context = vm.createContext({
  console,
  Date,
  URL,
  Blob,
  setTimeout,
  clearTimeout,
  document: { addEventListener() {} },
});
vm.runInContext(code, context);

const now = Date.parse("2026-09-01T18:00:00Z");
const recent = { startedAt: "2026-09-01T17:00:00Z", completedAt: null };
const stale = { startedAt: "2026-08-30T17:00:00Z", completedAt: null };
const invalid = { startedAt: "sin-fecha", completedAt: null };

assert.equal(context.isSavedStateFresh(recent, 24, now), true, "Un recorrido reciente debe conservarse.");
assert.equal(context.isSavedStateFresh(stale, 24, now), false, "Un recorrido mayor a 24 horas debe caducar.");
assert.equal(context.isSavedStateFresh(invalid, 24, now), false, "Una fecha inválida debe rechazarse.");

vm.runInContext(`
  questions = [{id:"q01"},{id:"q02"},{id:"q03"},{id:"q04"}];
  state = {answers:{q01:{status:"cumple"},q02:{status:"cumple"},q03:{status:"no_cumple",comment:"Corregir"},q04:{status:"na"}}};
`, context);
const stats = vm.runInContext("calculateStats()", context);
assert.equal(stats.score, 66.7, "No aplica debe excluirse del cálculo.");
assert.equal(stats.na, 1);

console.log("Lógica web válida: retención de 24 h y puntuación sin N/A.");

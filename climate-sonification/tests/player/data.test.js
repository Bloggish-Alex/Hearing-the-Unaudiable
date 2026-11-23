import test from "node:test";
import assert from "node:assert/strict";

import {
  barAt,
  seriesValueAt,
  tempoAtBar,
  validateSong,
} from "../../player/js/data.js";

const song = {
  meta: { start: 1925, end: 2024, duration: 277.691 },
  bars: [
    { label: "1925", year: 1925, t: 0, d: 2.9 },
    { label: "1926", year: 1926, t: 2.9, d: 2.9 },
  ],
  series: { temp: [0.1, null] },
  tempo: [[0, 82], [10, 78]],
  notes: [],
  presentation: { header: { title: "Test" } },
};

test("validateSong accepts a complete payload", () => {
  assert.deepEqual(validateSong(song), { ok: true });
});

test("validateSong rejects missing or malformed payloads", () => {
  assert.equal(validateSong(null).ok, false);
  assert.equal(validateSong({ ...song, presentation: undefined }).ok, false);
  assert.equal(validateSong({ ...song, bars: [] }).ok, false);
});

test("barAt and seriesValueAt", () => {
  assert.equal(barAt(song, 1).label, "1926");
  assert.equal(barAt(song, 9), null);
  assert.equal(seriesValueAt(song, "temp", 0), 0.1);
  assert.equal(seriesValueAt(song, "temp", 1), null);
  assert.equal(seriesValueAt(song, "missing", 0), null);
});

test("tempoAtBar follows the tempo map", () => {
  assert.equal(tempoAtBar(song, 0), 82);
  assert.equal(tempoAtBar(song, 9), 82);
  assert.equal(tempoAtBar(song, 10), 78);
  assert.equal(tempoAtBar(song, 99), 78);
});

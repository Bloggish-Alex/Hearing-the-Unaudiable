import test from "node:test";
import assert from "node:assert/strict";

import {
  formatPeriod,
  formatTempo,
  formatTime,
  formatValue,
} from "../../player/js/format.js";

test("formatValue handles signed temperature", () => {
  assert.equal(
    formatValue(0.1234, { format: "signed", decimals: 2, unit: "°C" }),
    "+0.12°C",
  );
  assert.equal(
    formatValue(-0.5, { format: "signed", decimals: 2, unit: "°C" }),
    "-0.50°C",
  );
});

test("formatValue handles fixed CO2 and missing values", () => {
  assert.equal(
    formatValue(315.3, { format: "fixed", decimals: 0, unit: "ppm" }),
    "315 ppm",
  );
  assert.equal(formatValue(null, { decimals: 2 }), "—");
  assert.equal(formatValue(undefined, { decimals: 2 }), "—");
});

test("formatPeriod uses label then year", () => {
  assert.equal(formatPeriod({ label: "1925", year: 1925 }), "1925");
  assert.equal(formatPeriod({ year: 1925 }), "1925");
  assert.equal(formatPeriod(null), "—");
});

test("formatTempo and formatTime", () => {
  assert.equal(formatTempo(82), "82 BPM");
  assert.equal(formatTempo(null), "—");
  assert.equal(formatTime(125), "2:05");
  assert.equal(formatTime(277.691), "4:37");
});

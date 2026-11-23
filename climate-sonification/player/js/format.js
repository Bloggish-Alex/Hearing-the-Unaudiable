export function formatValue(value, spec = {}) {
  if (value === null || value === undefined) {
    return "—";
  }

  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "—";
  }

  const decimals = spec.decimals ?? 2;
  let text = number.toFixed(decimals);
  if (spec.format === "signed" && number >= 0) {
    text = "+" + text;
  }

  const unit = spec.unit ?? "";
  if (unit) {
    const separator = unit.startsWith("°") || unit === "%" ? "" : " ";
    text += separator + unit;
  }

  return text;
}

export function formatPeriod(bar) {
  if (!bar) {
    return "—";
  }

  if (bar.label !== undefined && bar.label !== null) {
    return String(bar.label);
  }

  if (bar.year !== undefined && bar.year !== null) {
    return String(bar.year);
  }
  
  return "—";
}

export function formatTempo(bpm) {
  return bpm === null || bpm === undefined ? "—" : `${bpm} BPM`;
}

export function formatTime(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${String(rest).padStart(2, "0")}`;
}

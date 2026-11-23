import {
  barAt,
  seriesValueAt,
  tempoAtBar,
  validateSong,
} from "./data.js";
import {
  formatPeriod,
  formatTempo,
  formatTime,
  formatValue,
} from "./format.js";

const song = window.SONG;
const check = validateSong(song);

if (!check.ok) {
  renderError(check.error);
} else {
  render(song);
}

function make(tag, className = "", text = undefined) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }

  if (text !== undefined) {
    element.textContent = text;
  }

  return element;
}

function clear(selector) {
  const element = document.querySelector(selector);
  if (element) {
    element.replaceChildren();
  }

  return element;
}

function render(song) {
  const presentation = song.presentation;
  const header = presentation.header ?? {};
  const title = header.title || song.meta.title || "Climate Sonification";
  const accent = header.accent || "";

  document.title = [title, accent].filter(Boolean).join(" ");
  renderAppTitle(header, title, accent);
  renderSummary(song);
  renderReadout(presentation.readout ?? [], song, 0);
  renderVoices(presentation.voices ?? []);
  renderFooter(header.footer ?? []);

  window.__player = { song };
}

function renderAppTitle(header, title, accent) {
  const apptitle = clear("#apptitle");
  if (!apptitle) {
    return;
  }

  if (header.eyebrow) {
    apptitle.append(make("div", "eyebrow", header.eyebrow));
  }

  const heading = make("h1");
  heading.append(document.createTextNode(title));
  if (accent) {
    heading.append(make("em", "", ` ${accent}`));
  }
  apptitle.append(heading);

  if (header.dek) {
    apptitle.append(make("p", "dek", header.dek));
  }
}

function renderSummary(song) {
  const summary = clear("#summary");
  if (!summary) {
    return;
  }

  const card = make("div", "summary-card");
  const first = song.bars[0]?.label ?? song.meta.start ?? "—";
  const last = song.bars[song.bars.length - 1]?.label ?? song.meta.end ?? "—";
  const stats = [
    ["PERIOD", `${first}–${last}`],
    ["BARS", String(song.bars.length)],
    ["NOTES", String(song.notes.length)],
    ["DURATION", formatTime(song.meta.duration)],
  ];

  for (const [label, value] of stats) {
    const stat = make("div", "summary-stat");
    stat.append(make("span", "", label), make("b", "", value));
    card.append(stat);
  }

  summary.append(card);
}

function readoutValue(song, spec, barIndex) {
  if (spec.kind === "period") {
    return formatPeriod(barAt(song, barIndex));
  }

  if (spec.kind === "tempo") {
    return formatTempo(tempoAtBar(song, barIndex));
  }

  return formatValue(
    seriesValueAt(song, spec.series, barIndex),
    spec,
  );
}

function renderReadout(specs, song, barIndex) {
  const readout = clear("#readout");
  if (!readout) {
    return;
  }

  for (const spec of specs) {
    const stat = make("div", "stat");
    const value = make("b", "", readoutValue(song, spec, barIndex));
    if (spec.color) {
      value.style.color = spec.color;
    }

    stat.append(make("span", "", spec.label ?? spec.series ?? ""), value);
    readout.append(stat);
  }
}

function renderVoices(voices) {
  const legend = clear("#legend");
  if (!legend) {
    return;
  }

  for (const voice of voices) {
    const chip = make("span", "chip");
    const dot = make("i");

    if (voice.color) {
      dot.style.setProperty("--c", voice.color);
    }
    chip.append(dot, document.createTextNode(` ${voice.label ?? ""}`));

    if (voice.instrument) {
      chip.append(make("small", "", ` ${voice.instrument}`));
    }
    legend.append(chip);
  }
}

function renderFooter(lines) {
  const notes = clear("#notes");
  if (!notes) {
    return;
  }

  for (const line of lines) {
    notes.append(make("p", "", line));
  }
}

function renderError(message) {
  const hero = clear("#hero");
  if (hero) {
    hero.append(make("h1", "", "Player unavailable"));
    hero.append(make("p", "dek", message));
  }
  clear("#summary");
  clear("#readout");
  clear("#legend");
  clear("#notes");
}

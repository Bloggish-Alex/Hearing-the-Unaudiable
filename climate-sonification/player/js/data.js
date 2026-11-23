export function validateSong(song) {
  if (!song || typeof song !== "object") {
    return { ok: false, error: "player_data.js is missing or empty." };
  }

  for (const key of ["meta", "bars", "series", "notes", "presentation"]) {
    if (!(key in song)) {
      return { ok: false, error: `player data is missing "${key}".` };
    }
  }

  if (!Array.isArray(song.bars) || song.bars.length === 0) {
    return { ok: false, error: "player data has no bars." };
  }

  if (!song.presentation || !song.presentation.header) {
    return { ok: false, error: "player presentation is missing." };
  }

  return { ok: true };
}

export function barAt(song, index) {
  return song.bars?.[index] ?? null;
}

export function seriesValueAt(song, id, index) {
  const values = song.series?.[id];
  if (!Array.isArray(values) || index < 0 || index >= values.length) {
    return null;
  }

  return values[index] ?? null;
}

export function tempoAtBar(song, bar) {
  const tempo = song.tempo ?? [];
  if (!tempo.length) {
    return null;
  }

  let bpm = tempo[0][1];
  for (const [index, value] of tempo) {
    if (index <= bar) {
      bpm = value;
    } else {
      break;
    }
  }

  return bpm;
}

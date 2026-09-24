(() => {
  const API = (window.API_BASE || "").replace(/\/$/, "");
  const GREEN = "#1db954", MUTED = "#8e9993", GRID = "#262c29";
  const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
  const nf = new Intl.NumberFormat("pt-BR");
  const nf1 = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

  const STATIC = window.DATA_MODE !== "api";

  // "/api/top-artists?limit=15" -> "data/top-artists.json" (os parametros ja foram fixados no export)
  const get = async (path) => {
    const url = STATIC ? "data/" + path.replace(/^\/api\//, "").split("?")[0] + ".json" : API + path;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${path}: ${r.status}`);
    return r.json();
  };

  // Todo texto vindo da API entra via textContent (nunca innerHTML).
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text !== undefined) n.textContent = text;
    return n;
  };
  const dateBR = (iso) => iso.split("-").reverse().join("/");

  Chart.defaults.color = MUTED;
  Chart.defaults.borderColor = GRID;
  Chart.defaults.font.family = "system-ui, sans-serif";

  const bar = (id, labels, data, label, extra = {}) =>
    new Chart(document.getElementById(id), {
      type: extra.type || "bar",
      data: { labels, datasets: [{ label, data, backgroundColor: GREEN, borderColor: GREEN, ...(extra.ds || {}) }] },
      options: { maintainAspectRatio: false, plugins: { legend: { display: false } }, ...(extra.options || {}) },
    });

  function cards(s) {
    const items = [
      [nf.format(Math.round(s.total_hours)), "horas ouvidas"],
      [nf.format(s.total_days), "dias no período"],
      [nf.format(s.total_plays), "plays"],
      [nf.format(s.unique_artists), "artistas únicos"],
      [nf.format(s.unique_tracks), "músicas únicas"],
      [nf1.format(s.skip_rate * 100) + "%", "taxa de skip"],
    ];
    const root = document.getElementById("cards");
    items.forEach(([v, l]) => {
      const c = el("div", "card");
      c.append(el("b", null, v), el("span", null, l));
      root.append(c);
    });
    document.getElementById("range").textContent = `${dateBR(s.first_date)} → ${dateBR(s.last_date)}`;
  }

  function dominant(rows) {
    const root = document.getElementById("dominant");
    rows.forEach((r) => {
      const d = el("div");
      d.append(el("small", null, `${r.year} · ${nf1.format(r.hours)} h`), el("b", null, r.artist_name));
      root.append(d);
    });
  }

  function heatmap(rows) {
    const grid = {};
    let max = 0;
    rows.forEach((r) => { grid[`${r.weekday}-${r.hour}`] = r.hours; max = Math.max(max, r.hours); });
    const root = document.getElementById("heat");
    root.append(el("span"));
    for (let h = 0; h < 24; h++) root.append(el("span", "hh", String(h)));
    WEEKDAYS.forEach((name, i) => {
      root.append(el("b", null, name));
      for (let h = 0; h < 24; h++) {
        const v = grid[`${i + 1}-${h}`] || 0;
        const cell = el("i");
        cell.style.opacity = String(0.06 + 0.94 * (v / max));
        cell.title = `${name} ${h}h: ${nf1.format(v)} h`;
        root.append(cell);
      }
    });
  }

  function barList(id, rows, { name, sub, value, valueText }) {
    const root = document.getElementById(id);
    const max = Math.max(...rows.map(value));
    rows.forEach((r) => {
      const li = el("li");
      const lb = el("div", "lb");
      lb.append(el("span", null, name(r)));
      if (sub) lb.append(el("small", null, sub(r)));
      const tr = el("div", "tr");
      const fill = el("i");
      fill.style.width = `${(value(r) / max) * 100}%`;
      tr.append(fill);
      li.append(lb, tr, el("div", "vl", valueText(r)));
      root.append(li);
    });
  }

  function table(id, rows, cols) {
    const body = document.querySelector(`#${id} tbody`);
    rows.forEach((r) => {
      const tr = el("tr");
      cols.forEach(([fn, cls]) => {
        const td = el("td", cls, fn(r));
        td.title = td.textContent;
        tr.append(td);
      });
      body.append(tr);
    });
  }

  async function main() {
    const [summary, byYear, dominantRows, heat, byHour, byWeekday, diversity, discovery, artists, tracks, obsession, skips] =
      await Promise.all([
        get("/api/summary"), get("/api/by-year"), get("/api/dominant-artist-per-year"), get("/api/heatmap"),
        get("/api/by-hour"), get("/api/by-weekday"), get("/api/diversity-per-year"),
        get("/api/discovery?artists=15"), get("/api/top-artists?limit=15"), get("/api/top-tracks?limit=12"),
        get("/api/obsession-days?limit=12"), get("/api/skip-rate?limit=20"),
      ]);

    cards(summary);
    bar("c-year", byYear.map((r) => r.year), byYear.map((r) => r.hours), "Horas");
    dominant(dominantRows);
    heatmap(heat);
    bar("c-hour", byHour.map((r) => `${r.hour}h`), byHour.map((r) => r.hours), "Horas");
    bar("c-weekday", byWeekday.map((r) => WEEKDAYS[r.weekday - 1]), byWeekday.map((r) => r.hours), "Horas");

    new Chart(document.getElementById("c-div"), {
      type: "line",
      data: {
        labels: diversity.map((r) => r.year),
        datasets: [
          { label: "Artistas", data: diversity.map((r) => r.unique_artists), borderColor: GREEN, backgroundColor: GREEN, tension: 0.25 },
          { label: "Músicas", data: diversity.map((r) => r.unique_tracks), borderColor: MUTED, backgroundColor: MUTED, tension: 0.25 },
        ],
      },
      options: { maintainAspectRatio: false },
    });

    table("t-discovery", discovery, [
      [(r) => r.artist_name], [(r) => dateBR(r.first_play)],
      [(r) => nf1.format(r.hours), "n"], [(r) => nf.format(r.plays), "n"],
    ]);
    barList("l-artists", artists, {
      name: (r) => r.artist_name, sub: (r) => `${nf.format(r.plays)} plays`,
      value: (r) => r.hours, valueText: (r) => `${nf1.format(r.hours)} h`,
    });
    barList("l-tracks", tracks, {
      name: (r) => r.track_name, sub: (r) => r.artist_name,
      value: (r) => r.plays, valueText: (r) => `${nf.format(r.plays)}×`,
    });
    table("t-obsession", obsession, [
      [(r) => dateBR(r.date)], [(r) => r.track_name], [(r) => r.artist_name], [(r) => nf.format(r.plays), "n"],
    ]);
    barList("l-skip", skips, {
      name: (r) => r.artist_name, sub: (r) => `${nf.format(r.plays)} plays`,
      value: (r) => r.skip_rate, valueText: (r) => `${nf1.format(r.skip_rate * 100)}%`,
    });
  }

  main().catch((e) => {
    console.error(e);
    const box = document.getElementById("error");
    box.hidden = false;
    box.textContent = "Não consegui carregar os dados agora. Tente novamente em instantes.";
  });
})();

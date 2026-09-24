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

  // paragrafo com destaques: partes normais via txt("..."), o resto vira <b>
  const txt = (t) => ({ t });
  const para = (id, ...parts) => {
    const root = document.getElementById(id);
    parts.forEach((p) => {
      if (p && p.t !== undefined) root.append(document.createTextNode(p.t));
      else root.append(el("b", null, String(p)));
    });
  };

  function story(st, dominantRows) {
    const last = st.share_by_year[st.share_by_year.length - 1].year; // ultimo ano e parcial
    const share = st.share_by_year.filter((r) => r.year < last);
    const peak = share.reduce((m, r) => (r.share > m.share ? r : m));
    const now = share[share.length - 1];
    para("s1", st.top_artist, txt(" foi a trilha de quase tudo: em "), peak.year, txt(" chegou a "), `${nf1.format(peak.share)}%`, txt(" de todas as horas do ano. Em "), now.year, txt(", caiu para "), `${nf1.format(now.share)}%`, txt("."));
    bar("c-share", share.map((r) => r.year), share.map((r) => r.share), "% das horas do ano", {
      type: "line", ds: { tension: 0.25 }, options: { scales: { y: { ticks: { callback: (v) => v + "%" } } } },
    });

    const nw = st.new_artists_by_year.filter((r) => r.year >= 2017 && r.year < last);
    const low = nw.reduce((m, r) => (r.new_artists < m.new_artists ? r : m));
    const hi = nw.reduce((m, r) => (r.new_artists > m.new_artists ? r : m));
    para("s2", txt("Depois do começo, o gosto foi se fechando: em "), low.year, txt(" só "), nf.format(low.new_artists), txt(" artistas novos entraram na rotação. Em "), hi.year, txt(" foram "), nf.format(hi.new_artists), txt(", o maior número desde então."));
    bar("c-new", nw.map((r) => r.year), nw.map((r) => r.new_artists), "Artistas novos");

    const pd = st.hours_per_day_by_year.filter((r) => r.year < last);
    const early = pd.filter((r) => r.year >= 2016 && r.year <= 2021);
    const avg = early.reduce((s, r) => s + r.hours_per_day, 0) / early.length;
    const top = pd.reduce((m, r) => (r.hours_per_day > m.hours_per_day ? r : m));
    para("s3", txt("Entre 2016 e 2021, um dia de escuta rendia cerca de "), `${nf1.format(avg)} h`, txt(". Em "), top.year, txt(" chegou a "), `${nf1.format(top.hours_per_day)} h`, txt(" por dia ativo, cerca de "), `${nf1.format(top.hours_per_day / avg)}×`, txt(" mais."));
    bar("c-pace", pd.map((r) => r.year), pd.map((r) => r.hours_per_day), "Horas por dia ativo");

    para("s4", `${nf1.format(st.night_share)}%`, txt(" de tudo que ouvi foi entre meia-noite e 6h. A maior sequência foi de "), nf.format(st.longest_streak.days), txt(" dias seguidos ("), dateBR(st.longest_streak.start), txt(" a "), dateBR(st.longest_streak.end), txt("), e o dia mais intenso teve "), `${nf1.format(st.biggest_day.hours)} h`, txt(" de música ("), dateBR(st.biggest_day.date), txt(")."));

    const flip = dominantRows.find((r) => r.artist_name !== st.top_artist);
    if (flip) para("s5", txt("Em "), flip.year, txt(", pela primeira vez, "), flip.artist_name, txt(" passou "), st.top_artist, txt(" como artista mais ouvido do ano. A casa continua lá, mas agora divide o espaço com muito mais gente."));
    else para("s5", st.top_artist, txt(" continua sendo o artista mais ouvido de todos os anos."));
  }

  const REASONS = {
    trackdone: "Tocou até o fim", fwdbtn: "Avançar", clickrow: "Escolhi a faixa", backbtn: "Voltar",
    endplay: "Parei / encerrei", appload: "Abri o app", playbtn: "Play", remote: "Controle remoto",
    "unexpected-exit-while-paused": "Saída com pausa", "unexpected-exit": "Saída inesperada", logout: "Logout",
    unknown: "Desconhecido", outros: "Outros",
  };
  function reasonList(id, rows, overrides = {}) {
    const root = document.getElementById(id);
    const shown = rows.slice(0, 5);
    const rest = rows.slice(5).reduce((s, r) => s + r.share, 0);
    if (rest > 0) shown.push({ reason: "outros", share: rest });
    shown.forEach((r) => {
      const li = el("li");
      const lb = el("div", "lb");
      lb.append(el("span", null, overrides[r.reason] || REASONS[r.reason] || r.reason));
      li.append(lb, el("div", "vl", `${nf1.format(r.share)}%`));
      root.append(li);
    });
  }

  async function main() {
    const [summary, byYear, dominantRows, heat, byHour, byWeekday, diversity, discovery, artists, tracks, obsession, skips, st, endings] =
      await Promise.all([
        get("/api/summary"), get("/api/by-year"), get("/api/dominant-artist-per-year"), get("/api/heatmap"),
        get("/api/by-hour"), get("/api/by-weekday"), get("/api/diversity-per-year"),
        get("/api/discovery?artists=15"), get("/api/top-artists?limit=15"), get("/api/top-tracks?limit=12"),
        get("/api/obsession-days?limit=12"), get("/api/skip-rate?limit=20"),
        get("/api/story"), get("/api/endings"),
      ]);

    cards(summary);
    story(st, dominantRows);
    reasonList("l-start", endings.start, { trackdone: "Veio da faixa anterior", fwdbtn: "Avancei da anterior", backbtn: "Voltei à anterior" });
    reasonList("l-end", endings.end);
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

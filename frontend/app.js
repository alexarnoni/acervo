(() => {
  const API = (window.API_BASE || "").replace(/\/$/, "");
  const GREEN = "#f5a524", MUTED = "#8e9993", GRID = "#262c29";
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

  // dados que so existem como JSON estatico (gerados por src/insights.py)
  const getStatic = async (name) => {
    const r = await fetch(`data/${name}.json`);
    if (!r.ok) throw new Error(`${name}: ${r.status}`);
    return r.json();
  };
  const MONTHS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
  const ym = (s) => { const [y, m] = s.split("-"); return `${MONTHS[+m - 1]}/${y}`; };
  const join = (names) => names.join(", ");

  function eras(data) {
    const bar = document.getElementById("eras-bar");
    const root = document.getElementById("eras");
    const total = data.eras.reduce((s, e) => s + e.months, 0);
    data.eras.forEach((e, i) => {
      const seg = el("i");
      seg.style.flex = `${e.months} 1 0`;
      seg.style.opacity = String(0.35 + 0.65 * ((i + 1) / data.eras.length));
      seg.title = `${ym(e.start)} a ${ym(e.end)}`;
      bar.append(seg);

      const c = el("div", "era");
      c.append(el("small", null, `Fase ${i + 1} · ${e.months} meses`));
      c.append(el("h4", null, `${ym(e.start)} a ${ym(e.end)}`));
      const p1 = el("p");
      p1.append(el("b", null, "Mais ouvidos: "), document.createTextNode(join(e.top_artists.map((a) => a.artist_name))));
      const p2 = el("p");
      p2.append(el("b", null, "Marca da fase: "), document.createTextNode(join(e.signature_artists)));
      const p3 = el("p");
      p3.append(el("b", null, `${nf.format(Math.round(e.hours))} h`), document.createTextNode(` (${nf1.format((100 * e.months) / total)}% do tempo)`));
      c.append(p1, p2, p3);
      root.append(c);
    });
  }

  function calendar(data) {
    const byDate = new Map(data.days);
    const vals = data.days.map((d) => d[1]).filter((v) => v > 0).sort((a, b) => a - b);
    const q = (p) => vals[Math.floor(p * (vals.length - 1))];
    const t1 = q(0.25), t2 = q(0.5), t3 = q(0.75);
    const level = (h) => (h <= 0 ? 0 : h < t1 ? 1 : h < t2 ? 2 : h < t3 ? 3 : 4);
    const years = [...new Set(data.days.map((d) => +d[0].slice(0, 4)))];
    const root = document.getElementById("cal");
    years.forEach((y) => {
      const row = el("div", "cal-year");
      row.append(el("b", null, String(y)));
      const grid = el("div", "cal-grid");
      const start = new Date(Date.UTC(y, 0, 1));
      const end = new Date(Date.UTC(y, 11, 31));
      const offset = (start.getUTCDay() + 6) % 7; // segunda = 0
      for (let d = new Date(start), i = 0; d <= end; d.setUTCDate(d.getUTCDate() + 1), i++) {
        const iso = d.toISOString().slice(0, 10);
        const h = byDate.get(iso) || 0;
        const cell = el("i", level(h) ? `l${level(h)}` : "");
        if (i === 0) cell.style.gridRowStart = String(offset + 1);
        cell.title = `${dateBR(iso)}: ${nf1.format(h)} h`;
        grid.append(cell);
      }
      row.append(grid);
      root.append(row);
    });
  }

  function survival(s) {
    const at = (curve, yrs) => curve[s.years.indexOf(yrs)];
    const p5 = Math.round(at(s.all, 5) * 100);
    document.getElementById("surv-text").textContent =
      `${p5}% dos artistas que ouvi pelo menos 3 vezes ainda estavam na rotação 5 anos depois de descobertos. As curvas mostram cada geração de descobertas.`;
    document.getElementById("surv-rule").textContent = `Curva de sobrevivência (Kaplan-Meier). ${s.rule}.`;
    const COLORS = ["#f5a524", "#22d3ee", "#a78bfa", "#f472b6"];
    new Chart(document.getElementById("c-surv"), {
      type: "line",
      data: {
        labels: s.years,
        datasets: s.cohorts.map((c, i) => ({
          label: `${c.cohort} (${c.artists} artistas)`,
          data: c.survival.map((v) => Math.round(v * 100)),
          borderColor: COLORS[i % COLORS.length], backgroundColor: COLORS[i % COLORS.length],
          pointRadius: 0, tension: 0.15, borderWidth: 2,
        })),
      },
      options: {
        maintainAspectRatio: false,
        scales: { y: { min: 0, max: 100, ticks: { callback: (v) => v + "%" } }, x: { title: { display: true, text: "anos desde a descoberta" } } },
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  function rediscoveries(r) {
    const years = r.by_year.filter((y) => y.year >= 2016);
    const peak = years.reduce((m, y) => (y.share > m.share ? y : m));
    const early = years.filter((y) => y.year <= 2020);
    const avg = early.reduce((s, y) => s + y.share, 0) / early.length;
    document.getElementById("redis-text").textContent =
      `Em ${peak.year}, ${nf1.format(peak.share)}% dos plays foram de músicas que voltaram depois de mais de um ano paradas, contra ${nf1.format(avg)}% entre 2016 e 2020.`;
    bar("c-redis", years.map((y) => y.year), years.map((y) => y.share), "% dos plays", {
      options: { scales: { y: { ticks: { callback: (v) => v + "%" } } } },
    });
    const root = document.getElementById("l-redis");
    r.longest.slice(0, 5).forEach((t) => {
      const li = el("li");
      const lb = el("div", "lb");
      lb.append(el("span", null, t.track_name), el("small", null, t.artist_name));
      li.append(lb, el("div", "vl", `${nf1.format(t.gap_years)} anos`));
      root.append(li);
    });
  }

  function detector(a) {
    document.getElementById("detector").textContent =
      `Detector de escutas atípicas: sinalizou ${a.flagged_artists} artistas com mais da metade dos plays concentrada em 21 dias. Depois de revisar à mão, removi ${nf.format(a.removed_plays)} plays (${nf1.format(a.removed_hours)} h) de outras pessoas que usaram a conta.`;
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
    Promise.all([getStatic("eras"), getStatic("calendar"), getStatic("survival"), getStatic("rediscoveries"), getStatic("anomalies")])
      .then(([er, cal, sv, rd, an]) => { eras(er); calendar(cal); survival(sv); rediscoveries(rd); detector(an); })
      .catch((e) => console.error(e));
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

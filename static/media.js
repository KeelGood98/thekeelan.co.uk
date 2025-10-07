// Lightweight fetch that tries API first (on the Pi) and falls back to static json (on GH Pages)
async function fetchSmart(apiUrl, staticPath) {
  try {
    const r = await fetch(apiUrl, { cache: "no-store" });
    if (!r.ok) throw 0;
    return await r.json();
  } catch {
    const r2 = await fetch(staticPath, { cache: "no-store" });
    if (!r2.ok) throw new Error(staticPath + " -> " + r2.status);
    return await r2.json();
  }
}

function fmtDate(iso) {
  if (!iso) return "TBC";
  const d = new Date(iso);
  if (Number.isNaN(d)) return iso;
  return d.toLocaleDateString(undefined, { year:"numeric", month:"short", day:"2-digit" });
}

function renderMediaGrid(el, items) {
  el.innerHTML = items.map(x => `
    <div class="media-item">
      ${x.poster
        ? `<img src="${x.poster}" alt="">`
        : `<div style="width:92px;height:138px;background:#0b1220;border-radius:8px"></div>`}
      <div class="meta">
        <div class="title">${x.title ?? ""}</div>
        <div class="date">${fmtDate(x.date)}</div>
        ${x.rating ? `<div class="rating">★ ${Number(x.rating).toFixed(1)}</div>` : ``}
        ${x.overview ? `<div class="ov">${x.overview.slice(0,160)}${x.overview.length>160?"…":""}</div>` : ``}
      </div>
    </div>
  `).join("");
}

async function loadMedia() {
  try {
    const [movies, shows] = await Promise.all([
      fetchSmart("/api/media/movies", "./data/media_movies.json"),
      fetchSmart("/api/media/tv",     "./data/media_tv.json"),
    ]);

    const m = movies.movies ?? [];
    const s = shows.shows ?? [];
    const stamp = movies.updated || shows.updated || "";
    const updatedEl = document.querySelector("#media-updated");
    if (updatedEl) updatedEl.textContent = stamp ? `Updated ${stamp}` : "";

    renderMediaGrid(document.querySelector("#movies-grid"), m);
    renderMediaGrid(document.querySelector("#tv-grid"), s);
  } catch (e) {
    console.error("Media load failed:", e);
    const mg = document.querySelector("#movies-grid");
    const tg = document.querySelector("#tv-grid");
    if (mg) mg.innerHTML = `<p>Couldn’t load movies.</p>`;
    if (tg) tg.innerHTML = `<p>Couldn’t load TV shows.</p>`;
  }
}

// Hook up the Media tab without touching your existing JS
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.querySelector("#btn-media");
  if (!btn) return;
  btn.addEventListener("click", () => {
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
    const panel = document.querySelector("#panel-media");
    if (panel) panel.classList.add("active");
    loadMedia();
  });
});

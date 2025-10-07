/* Media page renderer — prefers snapshot JSON, falls back to /api/media if present */
(function () {
  const $ = (s) => document.querySelector(s);

  async function fetchMedia() {
    // try snapshot first (works on GitHub Pages)
    try {
      const r = await fetch("/data/media.json", { cache: "no-store" });
      if (r.ok) return await r.json();
    } catch {}
    // optional fallback to a live API if you expose one on the Pi
    try {
      const r2 = await fetch("/api/media", { cache: "no-store" });
      if (r2.ok) return await r2.json();
    } catch {}
    throw new Error("No media data available");
  }

  const fmtDate = (s) => {
    try {
      const d = new Date(s);
      return isNaN(d) ? s : d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    } catch { return s; }
  };

  function card(i) {
    const providers = (i.providers || []);
    const provHtml = providers.map(p => {
      if (p.logo) return `<span class="prov"><img class="prov__logo" src="${p.logo}" alt="${p.name}" title="${p.name}"></span>`;
      return `<span class="prov">${p.name}</span>`;
    }).join("");

    return `
      <article class="media-card">
        <div class="poster">
          ${i.poster ? `<img src="${i.poster}" alt="${i.title}">` : `<div class="no-poster">No image</div>`}
        </div>
        <div class="meta">
          <h4 class="title">${i.title || ""}</h4>
          <div class="sub">${i.kind === "movie" ? "Movie" : "TV"} • ${fmtDate(i.date || "")}</div>
          <div class="providers">${provHtml || `<span class="prov prov--tba">TBA</span>`}</div>
          ${i.overview ? `<p class="ov">${i.overview}</p>` : ""}
        </div>
      </article>
    `;
  }

  function render(list, rootSel) {
    const root = $(rootSel);
    if (!root) return;
    root.innerHTML = list.length ? list.map(card).join("") : `<div class="muted">Nothing found in this window.</div>`;
  }

  async function init() {
    try {
      const data = await fetchMedia();
      render(data.movies || [], "#movies");
      render(data.shows  || [], "#shows");
    } catch (e) {
      console.error(e);
      render([], "#movies");
      render([], "#shows");
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();

/* Media page: load /api/media (Pi live) or /data/media.json (snapshot) and render */

async function fetchSmart(apiUrl, staticPath) {
  // Same pattern as the Football/Gaming pages
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

function el(tag, cls, text) {
  const x = document.createElement(tag);
  if (cls) x.className = cls;
  if (text) x.textContent = text;
  return x;
}

function card(item) {
  const c = el("article", "media-card");
  const img = el("img", "media-card__poster");
  img.alt = item.title || "";
  img.loading = "lazy";
  img.src = item.poster || "/static/bg.jpg";
  c.appendChild(img);

  const body = el("div", "media-card__body");
  body.appendChild(el("h3", "media-card__title", item.title || ""));
  if (item.date) body.appendChild(el("div", "muted", new Date(item.date).toLocaleDateString("en-GB")));
  if (item.overview) body.appendChild(el("p", "media-card__ov", item.overview));

  const provRow = el("div", "media-card__providers");
  (item.providers || []).forEach(p => {
    const span = el("span", "prov");
    if (p.logo) {
      const logo = el("img", "prov__logo");
      logo.alt = p.name;
      logo.src = p.logo;
      logo.title = p.name;
      span.appendChild(logo);
    } else {
      span.textContent = p.name;
    }
    provRow.appendChild(span);
  });
  if (!provRow.childNodes.length) provRow.appendChild(el("span", "muted", "TBC"));
  body.appendChild(provRow);

  c.appendChild(body);
  return c;
}

function renderList(rootId, list) {
  const root = document.getElementById(rootId);
  root.innerHTML = "";
  if (!list || !list.length) {
    root.appendChild(el("div", "muted", "Nothing found in this window."));
    return;
  }
  list.forEach(item => root.appendChild(card(item)));
}

(async function init() {
  try {
    const data = await fetchSmart("/api/media", "/data/media.json");
    renderList("movies", data.movies);
    renderList("shows",  data.shows);
  } catch (e) {
    console.error(e);
    document.getElementById("movies").textContent = "Failed to load.";
    document.getElementById("shows").textContent  = "Failed to load.";
  }
})();

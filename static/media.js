/* Media page renderer
   - Reads /data/media.json (already built by update_media.py)
   - Renders two sections: movies & tv
   - Robust against slightly different key names (title/name, release_date/first_air_date, poster/poster_path)
*/

(async function () {
  const toJSON = async (u) => {
    const r = await fetch(u, { cache: "no-store" });
    if (!r.ok) throw new Error(`${u} -> ${r.status}`);
    return r.json();
  };

  let data;
  try {
    data = await toJSON("./data/media.json");
  } catch (e) {
    console.error("Failed to load media.json", e);
    byId("movies-empty").textContent = "Couldn't load media data.";
    byId("tv-empty").textContent = "Couldn't load media data.";
    return;
  }

  const windowInfo = data?.window || {};
  if (windowInfo.updated) {
    setText("movies-updated", `Updated ${fmtDate(windowInfo.updated)}`);
    setText("tv-updated", `Updated ${fmtDate(windowInfo.updated)}`);
  }

  const movies = Array.isArray(data?.movies) ? data.movies : [];
  const tv = Array.isArray(data?.tv) ? data.tv : [];

  renderList("movies-grid", "movies-empty", movies, "movie");
  renderList("tv-grid", "tv-empty", tv, "tv");
})();

/* ----------------- helpers ----------------- */

function byId(id) { return document.getElementById(id); }
function setText(id, t) { const el = byId(id); if (el) el.textContent = t || ""; }
function fmtDate(s) { try { const d = new Date(s); return isNaN(d) ? s : d.toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" }); } catch { return s; } }
function truncate(s, n) {
  if (!s) return "";
  if (s.length <= n) return s;
  const cut = s.slice(0, n).lastIndexOf(" ");
  return s.slice(0, cut > 0 ? cut : n) + "…";
}
function coalescePoster(p) {
  if (!p) return "";
  // If it already looks like a URL, use it; otherwise assume TMDb path
  if (/^https?:\/\//i.test(p)) return p;
  return `https://image.tmdb.org/t/p/w342${p}`;
}
function kindLabel(t) { return (t === "movie" ? "Film" : "TV"); }

function providerDotClass(name="") {
  const s = name.toLowerCase();
  if (s.includes("netflix")) return "netflix";
  if (s.includes("disney"))  return "disney";
  if (s.includes("prime") || s.includes("amazon")) return "prime";
  if (s.includes("now"))     return "now";
  if (s.includes("sky"))     return "sky";
  if (s.includes("bbc"))     return "bbc";
  if (s.includes("itv"))     return "itv";
  if (s.includes("apple"))   return "apple";
  return "";
}

function normalize(item, forcedType) {
  const type = forcedType || item.type || (item.media_type || "").toLowerCase();
  const title = item.title || item.name || item.original_title || item.original_name || "Untitled";
  const date = item.release_date || item.first_air_date || item.date || "";
  const overview = item.overview || item.description || "";
  const poster = coalescePoster(item.poster || item.poster_path || "");
  const providers = Array.isArray(item.providers) ? item.providers : (Array.isArray(item.uk_providers) ? item.uk_providers : []);
  return { type, title, date, overview, poster, providers };
}

function renderList(gridId, emptyId, list, forcedType) {
  const grid = byId(gridId);
  const empty = byId(emptyId);
  grid.innerHTML = "";
  empty.textContent = "";

  // Filter to upcoming window if dates exist (<= 90 days ahead)
  const now = new Date();
  const ahead = new Date(+now + 90 * 864e5);
  const filtered = list.filter(it => {
    const d = new Date(it.release_date || it.first_air_date || it.date || "");
    // If it has a date, keep next 90 days. If no date, keep it anyway.
    return isNaN(d) ? true : (d >= now && d <= ahead);
  });

  if (!filtered.length) {
    empty.textContent = "Nothing found in this window.";
    return;
  }

  const tpl = document.getElementById("card-tpl");
  filtered.forEach(it => {
    const m = normalize(it, forcedType);
    const node = tpl.content.cloneNode(true);

    const img = node.querySelector("img");
    if (m.poster) {
      img.src = m.poster;
      img.alt = m.title;
    } else {
      img.alt = `${m.title} (no artwork)`;
    }

    node.querySelector(".media-card__title").textContent = m.title;
    node.querySelector(".media-card__badge.type").textContent = kindLabel(m.type);
    node.querySelector(".kind").textContent = kindLabel(m.type);
    node.querySelector(".date").textContent = m.date ? fmtDate(m.date) : "TBA";
    node.querySelector(".media-card__overview").textContent = truncate(m.overview, 260);

    const provWrap = node.querySelector(".media-card__providers");
    if (m.providers && m.providers.length) {
      m.providers.slice(0,5).forEach(p => {
        const a = document.createElement("span");
        a.className = "provider";
        const dot = document.createElement("span");
        dot.className = "dot " + providerDotClass(String(p));
        a.appendChild(dot);
        a.appendChild(document.createTextNode(p));
        provWrap.appendChild(a);
      });
    }

    grid.appendChild(node);
  });
}

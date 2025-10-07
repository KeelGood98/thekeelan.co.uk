/* Media page loader — uses the prebuilt snapshot at /data/media.json */

const DATA_URL = "/data/media.json"; // absolute, so it works from /media.html

const TMDB_IMG = "https://image.tmdb.org/t/p/w342";
const FALLBACK = "data:image/svg+xml;charset=utf-8," +
  encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' width='342' height='513'>
    <rect width='100%' height='100%' fill='#222'/><text x='50%' y='50%' dominant-baseline='middle' text-anchor='middle'
    fill='#999' font-family='system-ui' font-size='18'>No poster</text></svg>`);

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-store" });
  if (!r.ok) throw new Error(url + " -> " + r.status);
  return r.json();
}

function cut(s, n = 220) {
  if (!s) return "";
  return s.length > n ? s.slice(0, n - 1) + "…" : s;
}

function badge(txt) {
  const el = document.createElement("span");
  el.className = "badge";
  el.textContent = txt;
  return el;
}

function card(item, kind) {
  // kind = "movie" or "tv"
  const img = document.createElement("img");
  img.loading = "lazy";
  img.src = item.poster ? (TMDB_IMG + item.poster) : FALLBACK;
  img.alt = (item.title || item.name || "") + " poster";

  const h3 = document.createElement("h3");
  h3.textContent = (kind === "movie" ? item.title : item.name) || "Untitled";

  const meta = document.createElement("div");
  meta.className = "meta";
  const date = item.date ? new Date(item.date) : null;
  meta.textContent = `${kind === "movie" ? "Film" : "TV"} • ` +
    (date ? date.toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" }) : "TBA");

  const badges = document.createElement("div");
  badges.className = "badges";
  if (item.provider) badges.append(badge(item.provider));
  if (item.isNew) badges.append(badge("NEW"));

  const ov = document.createElement("div");
  ov.className = "overview";
  ov.textContent = cut(item.overview, 320);

  const right = document.createElement("div");
  right.style.flex = "1 1 auto";
  right.append(h3, meta, badges, ov);

  const card = document.createElement("div");
  card.className = "card";
  card.append(img, right);
  return card;
}

function drawList(where, list, kind) {
  const host = document.getElementById(where);
  host.innerHTML = "";
  if (!list || !list.length) {
    const d = document.createElement("div");
    d.className = "card";
    d.textContent = "Nothing found in this window.";
    host.append(d);
    return;
  }
  // Sort by date ascending
  list.sort((a,b) => String(a.date).localeCompare(String(b.date)));
  for (const it of list) host.append(card(it, kind));
}

(async function init() {
  try {
    const data = await getJSON(DATA_URL);
    // Expecting { movies:[{title,poster,date,provider,overview,isNew}], tv:[{name,poster,date,provider,overview,isNew}] }
    drawList("movies", data.movies || [], "movie");
    drawList("tv", data.tv || [], "tv");
  } catch (e) {
    console.error("Media load failed:", e);
    for (const id of ["movies","tv"]) {
      const host = document.getElementById(id);
      host.innerHTML = "";
      const d = document.createElement("div");
      d.className = "card";
      d.textContent = "Couldn't load media data.";
      host.append(d);
    }
  }
})();

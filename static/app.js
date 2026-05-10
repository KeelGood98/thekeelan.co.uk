const DATA_PATHS = {
  table: "data/pl_table.json",
  fixtures: "data/mufc_fixtures.json",
  gaming: "data/gaming.json"
};

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  loadDashboard();
});

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".tab-panel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;

      tabs.forEach((item) => item.classList.remove("active"));
      panels.forEach((panel) => panel.classList.remove("active"));

      tab.classList.add("active");
      document.getElementById(target)?.classList.add("active");
    });
  });
}

async function loadDashboard() {
  await Promise.all([
    loadPremierLeagueTable(),
    loadFixtures(),
    loadGaming()
  ]);

  updateLastUpdatedLabel();
}

function updateLastUpdatedLabel() {
  const lastUpdated = document.getElementById("lastUpdated");

  if (!lastUpdated) return;

  lastUpdated.textContent = `Updated ${new Date().toLocaleString("en-GB", {
    dateStyle: "medium",
    timeStyle: "short"
  })}`;
}

async function fetchJson(path) {
  const response = await fetch(`${path}?v=${Date.now()}`);

  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }

  return response.json();
}

async function loadPremierLeagueTable() {
  const body = document.getElementById("plTableBody");

  if (!body) return;

  try {
    const data = await fetchJson(DATA_PATHS.table);

    if (!data.teams || !Array.isArray(data.teams)) {
      throw new Error("teams array missing from JSON");
    }

    body.innerHTML = data.teams.map((team, index) => `
      <tr>
        <td>${team.position || index + 1}</td>
        <td>
          <div class="team-cell">
            ${team.badge ? `<img class="badge" src="${team.badge}" alt="${team.name} badge">` : ""}
            <span>${team.name}</span>
          </div>
        </td>
        <td>${team.played ?? 0}</td>
        <td>${team.won ?? 0}</td>
        <td>${team.drawn ?? 0}</td>
        <td>${team.lost ?? 0}</td>
        <td>${team.goalDifference ?? 0}</td>
        <td><strong>${team.points ?? 0}</strong></td>
      </tr>
    `).join("");
  } catch (error) {
    console.error("Premier League table load error:", error);

    body.innerHTML = `
      <tr>
        <td colspan="8">Could not load Premier League table: ${error.message}</td>
      </tr>
    `;
  }
}

async function loadFixtures() {
  const list = document.getElementById("fixturesList");

  if (!list) return;

  try {
    const data = await fetchJson(DATA_PATHS.fixtures);

    if (!data.fixtures || !Array.isArray(data.fixtures)) {
      throw new Error("fixtures array missing from JSON");
    }

    list.innerHTML = data.fixtures.map((fixture) => {
      const resultClass = fixture.result ? `result ${fixture.result}` : "";
      const scoreOrVs = fixture.score ? fixture.score : "vs";
      const channelText = fixture.channel && fixture.channel !== "TBC"
        ? ` · ${fixture.channel}`
        : "";

      return `
        <article class="fixture">
          <div class="fixture-top">
            <span>${fixture.date || "TBC"}</span>
            <span>${fixture.competition || "Premier League"}</span>
          </div>

          <div class="fixture-main">
            ${fixture.home || "TBC"} ${scoreOrVs} ${fixture.away || "TBC"}
            ${fixture.result ? `<span class="${resultClass}">${fixture.result}</span>` : ""}
          </div>

          <div class="fixture-meta">
            ${fixture.venue || "TBC"}${channelText}
          </div>
        </article>
      `;
    }).join("");
  } catch (error) {
    console.error("Fixture load error:", error);
    list.innerHTML = `Could not load fixtures: ${error.message}`;
  }
}

async function loadGaming() {
  const bestDeals = document.getElementById("gamingBestDeals");
  const watchlist = document.getElementById("gamingWatchlist");
  const gamepass = document.getElementById("gamingGamepass");
  const links = document.getElementById("gamingLinks");

  if (!bestDeals || !watchlist || !gamepass || !links) return;

  try {
    const data = await fetchJson(DATA_PATHS.gaming);

    bestDeals.innerHTML = renderDealGrid(data.bestDeals || []);
    watchlist.innerHTML = renderDealGrid(data.watchlist || []);
    gamepass.innerHTML = renderGamepassCards(data.gamepass || []);
    links.innerHTML = renderGamingLinks(data.links || []);
  } catch (error) {
    console.error("Gaming load error:", error);

    bestDeals.innerHTML = `Could not load gaming data: ${error.message}`;
    watchlist.innerHTML = "";
    gamepass.innerHTML = "";
    links.innerHTML = "";
  }
}

function renderDealGrid(items) {
  if (!items.length) {
    return `<p class="muted">No deals found.</p>`;
  }

  return items.map((item) => {
    const image = item.thumb
      ? `<img class="deal-thumb" src="${item.thumb}" alt="${item.title} cover">`
      : `<div class="deal-thumb deal-thumb-empty">🎮</div>`;

    return `
      <a class="deal-card" href="${item.url}" target="_blank" rel="noopener noreferrer">
        ${image}

        <div class="deal-content">
          <div class="deal-title-row">
            <h3>${item.title || "Untitled"}</h3>
            <span class="deal-saving">${item.saving || "0%"}</span>
          </div>

          <div class="deal-price-row">
            <strong>${item.salePrice || "N/A"}</strong>
            <span>${item.normalPrice || ""}</span>
          </div>

          <div class="deal-meta">
            <span>${item.store || "Unknown store"}</span>
            ${item.steamRating ? `<span>${item.steamRating}</span>` : ""}
          </div>
        </div>
      </a>
    `;
  }).join("");
}

function renderGamepassCards(items) {
  if (!items.length) {
    return `<p class="muted">No Game Pass picks added yet.</p>`;
  }

  return items.map((item) => `
    <article class="mini-card mini-card-icon-layout">
      <div class="mini-card-icon-wrap">
        ${item.icon ? `<img class="mini-card-icon" src="${item.icon}" alt="${item.title} icon">` : `<div class="mini-card-icon mini-card-icon-fallback">🎮</div>`}
      </div>

      <div class="mini-card-body">
        <div class="mini-card-top">
          <h3>${item.title || "Untitled"}</h3>
          <span>${item.genre || ""}</span>
        </div>
        <p>${item.note || ""}</p>
      </div>
    </article>
  `).join("");
}

function renderGamingLinks(items) {
  if (!items.length) {
    return `<p class="muted">No links added yet.</p>`;
  }

  return items.map((item) => `
    <a class="gaming-link gaming-link-with-logo" href="${item.url}" target="_blank" rel="noopener noreferrer">
      ${item.logo ? `<img class="gaming-link-logo" src="${item.logo}" alt="${item.label} logo">` : ""}
      <span>${item.label}</span>
    </a>
  `).join("");
}

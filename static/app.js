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
  const featuredList = document.getElementById("gamingFeatured");
  const gamepassList = document.getElementById("gamingGamepass");
  const dealsList = document.getElementById("gamingDeals");
  const linksList = document.getElementById("gamingLinks");

  if (!featuredList || !gamepassList || !dealsList || !linksList) return;

  try {
    const data = await fetchJson(DATA_PATHS.gaming);

    featuredList.innerHTML = renderGameCards(data.featured || []);
    gamepassList.innerHTML = renderGameCards(data.gamepass || []);
    dealsList.innerHTML = renderDealCards(data.deals || []);
    linksList.innerHTML = renderGamingLinks(data.links || []);
  } catch (error) {
    console.error("Gaming load error:", error);

    featuredList.innerHTML = `Could not load gaming data: ${error.message}`;
    gamepassList.innerHTML = "";
    dealsList.innerHTML = "";
    linksList.innerHTML = "";
  }
}

function renderGameCards(items) {
  if (!items.length) {
    return `<p class="muted">Nothing added yet.</p>`;
  }

  return items.map((item) => `
    <article class="mini-card">
      <div class="mini-card-top">
        <h3>${item.title || "Untitled"}</h3>
        <span>${item.status || item.platform || item.genre || ""}</span>
      </div>
      <p>${item.note || ""}</p>
      ${item.platform ? `<div class="mini-meta">${item.platform}</div>` : ""}
      ${item.genre ? `<div class="mini-meta">${item.genre}</div>` : ""}
    </article>
  `).join("");
}

function renderDealCards(items) {
  if (!items.length) {
    return `<p class="muted">No deals added yet.</p>`;
  }

  return items.map((item) => `
    <article class="mini-card">
      <div class="mini-card-top">
        <h3>${item.title || "Untitled"}</h3>
        <span>${item.price || ""}</span>
      </div>
      <p>${item.note || ""}</p>
    </article>
  `).join("");
}

function renderGamingLinks(items) {
  if (!items.length) {
    return `<p class="muted">No links added yet.</p>`;
  }

  return items.map((item) => `
    <a class="gaming-link" href="${item.url}" target="_blank" rel="noopener noreferrer">
      ${item.label}
    </a>
  `).join("");
}

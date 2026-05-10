const DATA_PATHS = {
  table: "data/pl_table.json",
  fixtures: "data/mufc_fixtures.json",
  gaming: "data/gaming.json",
  weather: "data/weather.json"
};

const APP_STATE = {
  table: null,
  fixtures: null,
  gaming: null,
  weather: null
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
    loadGaming(),
    loadWeather()
  ]);

  loadHome();
  updateLastUpdatedLabel();
}

function updateLastUpdatedLabel() {
  const lastUpdated = document.getElementById("lastUpdated");

  if (!lastUpdated) return;

  const dates = [
    APP_STATE.table?.updated,
    APP_STATE.fixtures?.updated,
    APP_STATE.gaming?.updated,
    APP_STATE.weather?.updated
  ]
    .filter(Boolean)
    .map((value) => new Date(value))
    .filter((date) => !Number.isNaN(date.getTime()));

  if (!dates.length) {
    lastUpdated.textContent = `Updated ${new Date().toLocaleString("en-GB", {
      dateStyle: "medium",
      timeStyle: "short"
    })}`;
    return;
  }

  const newest = new Date(Math.max(...dates.map((date) => date.getTime())));

  lastUpdated.textContent = `Updated ${newest.toLocaleString("en-GB", {
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

  try {
    const data = await fetchJson(DATA_PATHS.table);
    APP_STATE.table = data;

    if (!data.teams || !Array.isArray(data.teams)) {
      throw new Error("teams array missing from JSON");
    }

    if (!body) return;

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

    if (body) {
      body.innerHTML = `
        <tr>
          <td colspan="8">Could not load Premier League table: ${error.message}</td>
        </tr>
      `;
    }
  }
}

async function loadFixtures() {
  const list = document.getElementById("fixturesList");

  try {
    const data = await fetchJson(DATA_PATHS.fixtures);
    APP_STATE.fixtures = data;

    if (!data.fixtures || !Array.isArray(data.fixtures)) {
      throw new Error("fixtures array missing from JSON");
    }

    if (!list) return;

    list.innerHTML = data.fixtures.map((fixture) => renderFixtureCard(fixture)).join("");
  } catch (error) {
    console.error("Fixture load error:", error);

    if (list) {
      list.innerHTML = `Could not load fixtures: ${error.message}`;
    }
  }
}

function renderFixtureCard(fixture) {
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
}

async function loadGaming() {
  const bestDeals = document.getElementById("gamingBestDeals");
  const watchlist = document.getElementById("gamingWatchlist");
  const gamepass = document.getElementById("gamingGamepass");
  const links = document.getElementById("gamingLinks");

  try {
    const data = await fetchJson(DATA_PATHS.gaming);
    APP_STATE.gaming = data;

    if (bestDeals) {
      bestDeals.innerHTML = renderDealGrid(data.bestDeals || []);
    }

    if (watchlist) {
      watchlist.innerHTML = renderDealGrid(data.watchlist || []);
    }

    if (gamepass) {
      gamepass.innerHTML = renderGamepassCards(data.gamepass || []);
    }

    if (links) {
      links.innerHTML = renderGamingLinks(data.links || []);
    }
  } catch (error) {
    console.error("Gaming load error:", error);

    if (bestDeals) {
      bestDeals.innerHTML = `Could not load gaming data: ${error.message}`;
    }

    if (watchlist) watchlist.innerHTML = "";
    if (gamepass) gamepass.innerHTML = "";
    if (links) links.innerHTML = "";
  }
}

async function loadWeather() {
  const extrasWeather = document.getElementById("extrasWeather");

  try {
    const data = await fetchJson(DATA_PATHS.weather);
    APP_STATE.weather = data;

    if (extrasWeather) {
      extrasWeather.innerHTML = renderFullWeather(data);
    }
  } catch (error) {
    console.error("Weather load error:", error);

    if (extrasWeather) {
      extrasWeather.innerHTML = `Could not load weather data: ${error.message}`;
    }
  }
}

function loadHome() {
  loadHomeWeatherHero();
  loadHomeNextFixture();
  loadHomeTopDeal();
  loadHomeTopThree();
  loadHomeQuickLinks();
}

function loadHomeWeatherHero() {
  const main = document.getElementById("homeWeatherHeroMain");
  const stats = document.getElementById("homeWeatherHeroStats");

  const weather = APP_STATE.weather;
  const current = weather?.current;

  if (!current) {
    if (main) {
      main.innerHTML = `
        <div class="weather-icon weather-icon-large">🌡️</div>
        <div>
          <h2>Weather unavailable</h2>
          <p>No weather data found.</p>
        </div>
      `;
    }

    if (stats) {
      stats.innerHTML = `
        <span>Wind —</span>
        <span>Humidity —</span>
        <span>Rain —</span>
      `;
    }

    return;
  }

  if (main) {
    main.innerHTML = `
      <div class="weather-icon weather-icon-large">${current.icon || "🌡️"}</div>

      <div>
        <h2>${current.temperature ?? "N/A"}°C in ${weather.location || "Leeds"}</h2>
        <p>${current.description || "Unknown"} · Feels like ${current.feelsLike ?? "N/A"}°C</p>
      </div>
    `;
  }

  if (stats) {
    stats.innerHTML = `
      <span>Wind ${current.windSpeed ?? "N/A"} mph</span>
      <span>Humidity ${current.humidity ?? "N/A"}%</span>
      <span>Rain ${current.precipitation ?? "N/A"} mm</span>
    `;
  }
}

function loadHomeNextFixture() {
  const target = document.getElementById("homeNextFixture");
  if (!target) return;

  const fixtures = APP_STATE.fixtures?.fixtures || [];

  const nextFixture =
    fixtures.find((fixture) => !fixture.score && fixture.status !== "FINISHED") ||
    fixtures.find((fixture) => !fixture.score) ||
    fixtures[0];

  if (!nextFixture) {
    target.innerHTML = `<p class="muted">No fixture data found.</p>`;
    return;
  }

  target.innerHTML = `
    <div class="home-feature-main">
      <span class="home-icon">⚽</span>
      <div>
        <h3>${nextFixture.home || "TBC"} ${nextFixture.score ? nextFixture.score : "vs"} ${nextFixture.away || "TBC"}</h3>
        <p>${nextFixture.date || "TBC"} · ${nextFixture.competition || "Premier League"}</p>
      </div>
    </div>

    <button class="home-jump-button" data-jump-tab="football">Open Football</button>
  `;

  setupJumpButtons();
}

function loadHomeTopDeal() {
  const target = document.getElementById("homeTopDeal");
  if (!target) return;

  const deals = APP_STATE.gaming?.bestDeals || [];
  const topDeal = deals[0];

  if (!topDeal) {
    target.innerHTML = `<p class="muted">No deal data found.</p>`;
    return;
  }

  const image = topDeal.thumb
    ? `<img class="home-deal-thumb" src="${topDeal.thumb}" alt="${topDeal.title} cover">`
    : `<div class="home-deal-thumb home-deal-thumb-empty">🎮</div>`;

  target.innerHTML = `
    <a class="home-feature-link" href="${topDeal.url}" target="_blank" rel="noopener noreferrer">
      <div class="home-feature-main">
        ${image}
        <div>
          <h3>${topDeal.title || "Untitled"}</h3>
          <p>${topDeal.salePrice || "N/A"} <span>${topDeal.normalPrice || ""}</span></p>
        </div>
      </div>

      <strong class="home-saving">${topDeal.saving || "0%"}</strong>
    </a>
  `;
}

function loadHomeTopThree() {
  const target = document.getElementById("homeTopThree");
  if (!target) return;

  const teams = APP_STATE.table?.teams || [];

  if (!teams.length) {
    target.innerHTML = `<p class="muted">No table data found.</p>`;
    return;
  }

  target.innerHTML = teams.slice(0, 3).map((team, index) => `
    <div class="home-list-row">
      <div class="team-cell">
        <strong>${team.position || index + 1}</strong>
        ${team.badge ? `<img class="badge" src="${team.badge}" alt="${team.name} badge">` : ""}
        <span>${team.name}</span>
      </div>
      <strong>${team.points ?? 0} pts</strong>
    </div>
  `).join("");
}

function loadHomeQuickLinks() {
  const target = document.getElementById("homeQuickLinks");
  if (!target) return;

  const links = APP_STATE.gaming?.links || [];

  if (!links.length) {
    target.innerHTML = `<p class="muted">No quick links found.</p>`;
    return;
  }

  target.innerHTML = renderGamingLinks(links.slice(0, 6));
}

function setupJumpButtons() {
  const buttons = document.querySelectorAll("[data-jump-tab]");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const tabName = button.dataset.jumpTab;
      const tab = document.querySelector(`.tab[data-tab="${tabName}"]`);

      if (tab) {
        tab.click();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
  });
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

function renderFullWeather(data) {
  const current = data.current || {};
  const forecast = data.forecast || [];

  return `
    <div class="weather-panel">
      <div class="weather-current weather-current-large">
        <div class="weather-icon weather-icon-large">${current.icon || "🌡️"}</div>

        <div>
          <h3>${current.temperature ?? "N/A"}°C</h3>
          <p>${current.description || "Unknown"} · Feels like ${current.feelsLike ?? "N/A"}°C</p>
        </div>
      </div>

      <div class="weather-stats weather-stats-grid">
        <span>Wind ${current.windSpeed ?? "N/A"} mph</span>
        <span>Gusts ${current.windGusts ?? "N/A"} mph</span>
        <span>Humidity ${current.humidity ?? "N/A"}%</span>
        <span>Rain ${current.precipitation ?? "N/A"} mm</span>
      </div>

      <div class="forecast-grid">
        ${forecast.map((day, index) => `
          <article class="forecast-card">
            <div class="forecast-icon">${day.icon || "🌡️"}</div>
            <div>
              <h3>${index === 0 ? "Today" : index === 1 ? "Tomorrow" : day.date}</h3>
              <p>${day.description || "Unknown"}</p>
              <strong>${day.maxTemp ?? "N/A"}° / ${day.minTemp ?? "N/A"}°C</strong>
              <span>Rain chance ${day.rainChance ?? "N/A"}%</span>
            </div>
          </article>
        `).join("")}
      </div>
    </div>
  `;
}

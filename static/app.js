const DATA_PATHS = {
  table: "data/pl_table.json",
  fixtures: "data/mufc_fixtures.json",
  stats: "data/pl_stats.json",
  gaming: "data/gaming.json",
  weather: "data/weather.json",
  media: "data/media.json"
};

const APP_STATE = {
  table: null,
  fixtures: null,
  stats: null,
  gaming: null,
  weather: null,
  media: null
};

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupMemeButton();
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

function setupMemeButton() {
  const button = document.getElementById("randomMemeButton");

  if (!button) return;

  button.addEventListener("click", () => {
    loadRandomMeme();
  });
}

async function loadDashboard() {
  await Promise.all([
    loadPremierLeagueTable(),
    loadFixtures(),
    loadPremierLeagueStats(),
    loadGaming(),
    loadWeather(),
    loadMedia()
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
    APP_STATE.stats?.updated,
    APP_STATE.gaming?.updated,
    APP_STATE.weather?.updated,
    APP_STATE.media?.updated
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
      <tr class="${team.name === "Manchester United" ? "highlight-row" : ""}">
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
        <td>${team.goalsFor ?? 0}</td>
        <td>${team.goalsAgainst ?? 0}</td>
        <td>${team.goalDifference ?? 0}</td>
        <td><strong>${team.points ?? 0}</strong></td>
      </tr>
    `).join("");
  } catch (error) {
    console.error("Premier League table load error:", error);

    if (body) {
      body.innerHTML = `
        <tr>
          <td colspan="10">Could not load Premier League table: ${error.message}</td>
        </tr>
      `;
    }
  }
}

async function loadFixtures() {
  const nextMatch = document.getElementById("mufcNextMatch");
  const recentResults = document.getElementById("mufcRecentResults");
  const upcomingFixtures = document.getElementById("mufcUpcomingFixtures");

  try {
    const data = await fetchJson(DATA_PATHS.fixtures);
    APP_STATE.fixtures = data;

    if (!data.fixtures || !Array.isArray(data.fixtures)) {
      throw new Error("fixtures array missing from JSON");
    }

    if (nextMatch) {
      nextMatch.innerHTML = renderFeatureMatch(data.nextMatch);
    }

    if (recentResults) {
      recentResults.innerHTML = renderMatchList(data.recentResults || [], "No recent results found.");
    }

    if (upcomingFixtures) {
      upcomingFixtures.innerHTML = renderMatchList(data.upcomingFixtures || [], "No upcoming fixtures found.");
    }
  } catch (error) {
    console.error("Fixture load error:", error);

    if (nextMatch) nextMatch.innerHTML = `Could not load fixtures: ${error.message}`;
    if (recentResults) recentResults.innerHTML = "";
    if (upcomingFixtures) upcomingFixtures.innerHTML = "";
  }
}

async function loadPremierLeagueStats() {
  const topScorers = document.getElementById("plTopScorers");
  const bestAttacks = document.getElementById("plBestAttacks");
  const bestDefences = document.getElementById("plBestDefences");
  const mufcSummary = document.getElementById("mufcSummary");

  try {
    const data = await fetchJson(DATA_PATHS.stats);
    APP_STATE.stats = data;

    if (topScorers) {
      topScorers.innerHTML = renderTopScorers(data.topScorers || []);
    }

    if (bestAttacks) {
      bestAttacks.innerHTML = renderTeamStatList(data.bestAttacks || [], "goalsFor", "goals");
    }

    if (bestDefences) {
      bestDefences.innerHTML = renderTeamStatList(data.bestDefences || [], "goalsAgainst", "conceded");
    }

    if (mufcSummary) {
      mufcSummary.innerHTML = renderMufcSummary(data.manUnitedSummary);
    }
  } catch (error) {
    console.error("Premier League stats load error:", error);

    if (topScorers) topScorers.innerHTML = `Could not load stats: ${error.message}`;
    if (bestAttacks) bestAttacks.innerHTML = "";
    if (bestDefences) bestDefences.innerHTML = "";
    if (mufcSummary) mufcSummary.innerHTML = "";
  }
}

function renderFeatureMatch(match) {
  if (!match) {
    return `<p class="muted">No next match found.</p>`;
  }

  const statusLabel = formatStatus(match.status);
  const matchday = match.matchday ? `Matchday ${match.matchday}` : "Premier League";
  const scoreText = match.score ? match.score : "vs";

  return `
    <article class="feature-match-card">
      <div class="feature-match-top">
        <span>${matchday}</span>
        <strong>${statusLabel}</strong>
      </div>

      <div class="feature-match-main">
        <h3>${match.home || "TBC"} ${scoreText} ${match.away || "TBC"}</h3>
        <p>${match.date || "TBC"} · ${match.competition || "Premier League"}</p>
      </div>

      <div class="feature-match-meta">
        <span>${match.venue || "Venue TBC"}</span>
        ${match.channel && match.channel !== "TBC" ? `<span>${match.channel}</span>` : ""}
      </div>
    </article>
  `;
}

function renderMatchList(matches, emptyMessage) {
  if (!matches.length) {
    return `<p class="muted">${emptyMessage}</p>`;
  }

  return matches.map((match) => renderDetailedFixtureCard(match)).join("");
}

function renderDetailedFixtureCard(match) {
  const scoreOrVs = match.score ? match.score : "vs";
  const resultClass = match.result ? `result ${match.result}` : "";
  const statusLabel = formatStatus(match.status);
  const halfTime = match.halfTimeScore ? `HT ${match.halfTimeScore}` : "";
  const winner = match.winner ? `Winner: ${match.winner}` : "";
  const matchday = match.matchday ? `MD ${match.matchday}` : "";

  return `
    <article class="fixture detailed-fixture">
      <div class="fixture-top">
        <span>${match.date || "TBC"}</span>
        <span>${statusLabel}</span>
      </div>

      <div class="fixture-main">
        ${match.home || "TBC"} ${scoreOrVs} ${match.away || "TBC"}
        ${match.result ? `<span class="${resultClass}">${match.result}</span>` : ""}
      </div>

      <div class="fixture-detail-row">
        ${matchday ? `<span>${matchday}</span>` : ""}
        ${halfTime ? `<span>${halfTime}</span>` : ""}
        ${winner ? `<span>${winner}</span>` : ""}
      </div>

      <div class="fixture-meta">
        ${match.competition || "Premier League"}
        ${match.channel && match.channel !== "TBC" ? ` · ${match.channel}` : ""}
      </div>
    </article>
  `;
}

function formatStatus(status) {
  const labels = {
    FINISHED: "Finished",
    TIMED: "Scheduled",
    SCHEDULED: "Scheduled",
    IN_PLAY: "Live",
    PAUSED: "Half-time",
    POSTPONED: "Postponed",
    SUSPENDED: "Suspended",
    CANCELLED: "Cancelled"
  };

  return labels[status] || status || "TBC";
}

function renderTopScorers(items) {
  if (!items.length) {
    return `<p class="muted">No scorers found.</p>`;
  }

  return items.map((player, index) => `
    <div class="stats-row">
      <div class="stats-left">
        <strong>${index + 1}</strong>
        ${player.teamBadge ? `<img class="badge" src="${player.teamBadge}" alt="${player.team} badge">` : ""}
        <div>
          <span>${player.name || "Unknown"}</span>
          <p>${player.team || "Unknown team"}</p>
        </div>
      </div>

      <div class="stats-number">
        <strong>${player.goals ?? 0}</strong>
        <span>goals</span>
      </div>
    </div>
  `).join("");
}

function renderTeamStatList(items, valueKey, label) {
  if (!items.length) {
    return `<p class="muted">No team stats found.</p>`;
  }

  return items.map((team, index) => `
    <div class="stats-row">
      <div class="stats-left">
        <strong>${index + 1}</strong>
        ${team.badge ? `<img class="badge" src="${team.badge}" alt="${team.name} badge">` : ""}
        <div>
          <span>${team.name || "Unknown"}</span>
          <p>${team.played ?? 0} played</p>
        </div>
      </div>

      <div class="stats-number">
        <strong>${team[valueKey] ?? 0}</strong>
        <span>${label}</span>
      </div>
    </div>
  `).join("");
}

function renderMufcSummary(team) {
  if (!team) {
    return `<p class="muted">No United summary found.</p>`;
  }

  return `
    <div class="mufc-summary-card">
      <div class="team-cell">
        ${team.badge ? `<img class="badge large-badge" src="${team.badge}" alt="${team.name} badge">` : ""}
        <div>
          <h3>${team.name || "Manchester United"}</h3>
          <p>${ordinal(team.position)} · ${team.points ?? 0} pts</p>
        </div>
      </div>

      <div class="summary-grid">
        <span><strong>${team.played ?? 0}</strong>P</span>
        <span><strong>${team.won ?? 0}</strong>W</span>
        <span><strong>${team.drawn ?? 0}</strong>D</span>
        <span><strong>${team.lost ?? 0}</strong>L</span>
        <span><strong>${team.goalsFor ?? 0}</strong>GF</span>
        <span><strong>${team.goalsAgainst ?? 0}</strong>GA</span>
      </div>
    </div>
  `;
}

function ordinal(value) {
  const number = Number(value);

  if (!number) return "Position TBC";

  const suffixes = ["th", "st", "nd", "rd"];
  const mod100 = number % 100;
  const suffix = suffixes[(mod100 - 20) % 10] || suffixes[mod100] || suffixes[0];

  return `${number}${suffix}`;
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
      links.innerHTML = renderGenericLinks(data.links || []);
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

async function loadMedia() {
  const trendingMovies = document.getElementById("mediaTrendingMovies");
  const trendingTv = document.getElementById("mediaTrendingTv");
  const upcomingMovies = document.getElementById("mediaUpcomingMovies");
  const nowPlaying = document.getElementById("mediaNowPlaying");
  const mediaLinks = document.getElementById("mediaLinks");
  const mediaAttribution = document.getElementById("mediaAttribution");

  try {
    const data = await fetchJson(DATA_PATHS.media);
    APP_STATE.media = data;

    if (trendingMovies) {
      trendingMovies.innerHTML = renderMediaGrid(data.trendingMovies || []);
    }

    if (trendingTv) {
      trendingTv.innerHTML = renderMediaGrid(data.trendingTv || []);
    }

    if (upcomingMovies) {
      upcomingMovies.innerHTML = renderMediaGrid(data.upcomingMovies || []);
    }

    if (nowPlaying) {
      nowPlaying.innerHTML = renderMediaGrid(data.nowPlayingMovies || []);
    }

    if (mediaLinks) {
      mediaLinks.innerHTML = renderGenericLinks(data.links || []);
    }

    if (mediaAttribution) {
      mediaAttribution.textContent = data.attribution || "";
    }
  } catch (error) {
    console.error("Media load error:", error);

    if (trendingMovies) {
      trendingMovies.innerHTML = `Could not load media data: ${error.message}`;
    }

    if (trendingTv) trendingTv.innerHTML = "";
    if (upcomingMovies) upcomingMovies.innerHTML = "";
    if (nowPlaying) nowPlaying.innerHTML = "";
    if (mediaLinks) mediaLinks.innerHTML = "";
  }
}

function loadHome() {
  loadHomeWeatherHero();
  loadHomeNextFixture();
  loadHomeTopDeal();
  loadHomeTopThree();
  loadHomeMediaPick();
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

  const nextFixture = APP_STATE.fixtures?.nextMatch ||
    APP_STATE.fixtures?.upcomingFixtures?.[0] ||
    APP_STATE.fixtures?.fixtures?.find((fixture) => !fixture.score && fixture.status !== "FINISHED") ||
    APP_STATE.fixtures?.fixtures?.[0];

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

function loadHomeMediaPick() {
  const target = document.getElementById("homeMediaPick");
  if (!target) return;

  const items = [
    ...(APP_STATE.media?.trendingMovies || []),
    ...(APP_STATE.media?.trendingTv || [])
  ];

  const pick = items[0];

  if (!pick) {
    target.innerHTML = `<p class="muted">No media data found.</p>`;
    return;
  }

  const poster = pick.poster
    ? `<img class="home-deal-thumb" src="${pick.poster}" alt="${pick.title} poster">`
    : `<div class="home-deal-thumb home-deal-thumb-empty">🎬</div>`;

  target.innerHTML = `
    <a class="home-feature-link" href="${pick.url}" target="_blank" rel="noopener noreferrer">
      <div class="home-feature-main">
        ${poster}
        <div>
          <h3>${pick.title || "Untitled"}</h3>
          <p>${pick.mediaType === "tv" ? "TV" : "Movie"} · ⭐ ${pick.rating || "N/A"}</p>
        </div>
      </div>

      <strong class="home-saving">Trending</strong>
    </a>
  `;
}

function loadHomeQuickLinks() {
  const target = document.getElementById("homeQuickLinks");
  if (!target) return;

  const links = [
    ...(APP_STATE.gaming?.links || []).slice(0, 3),
    ...(APP_STATE.media?.links || []).slice(0, 3)
  ];

  if (!links.length) {
    target.innerHTML = `<p class="muted">No quick links found.</p>`;
    return;
  }

  target.innerHTML = renderGenericLinks(links);
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

async function loadRandomMeme() {
  const button = document.getElementById("randomMemeButton");
  const status = document.getElementById("memeStatus");
  const result = document.getElementById("memeResult");

  if (!button || !status || !result) return;

  button.disabled = true;
  status.textContent = "Summoning nonsense...";
  result.innerHTML = `
    <div class="meme-placeholder">
      <span>⏳</span>
      <p>Loading meme...</p>
    </div>
  `;

  try {
    const meme = await fetchSafeMeme();

    result.innerHTML = `
      <article class="meme-card">
        <img class="meme-image" src="${meme.url}" alt="${meme.title || "Random meme"}">

        <div class="meme-info">
          <h3>${meme.title || "Random meme"}</h3>
          <p>r/${meme.subreddit || "memes"} · by ${meme.author || "unknown"}</p>

          <a href="${meme.postLink || meme.url}" target="_blank" rel="noopener noreferrer">
            Open source
          </a>
        </div>
      </article>
    `;

    status.textContent = "Fresh nonsense loaded.";
  } catch (error) {
    console.error("Meme load error:", error);

    result.innerHTML = `
      <div class="meme-placeholder">
        <span>💀</span>
        <p>Could not load a meme. The internet has failed us.</p>
      </div>
    `;

    status.textContent = "Meme machine had a wobble.";
  } finally {
    button.disabled = false;
  }
}

async function fetchSafeMeme() {
  const endpoints = [
    "https://meme-api.com/gimme/memes",
    "https://meme-api.com/gimme/wholesomememes",
    "https://meme-api.com/gimme/me_irl"
  ];

  for (let attempt = 0; attempt < 5; attempt++) {
    const endpoint = endpoints[attempt % endpoints.length];
    const response = await fetch(`${endpoint}?v=${Date.now()}`);

    if (!response.ok) {
      throw new Error(`Meme API returned ${response.status}`);
    }

    const data = await response.json();

    if (!data.nsfw && !data.spoiler && data.url) {
      return data;
    }
  }

  throw new Error("No safe meme returned");
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

function renderMediaGrid(items) {
  if (!items.length) {
    return `<p class="muted">No media items found.</p>`;
  }

  return items.map((item) => {
    const poster = item.poster
      ? `<img class="media-poster" src="${item.poster}" alt="${item.title} poster">`
      : `<div class="media-poster media-poster-empty">🎬</div>`;

    const typeLabel = item.mediaType === "tv" ? "TV" : "Movie";

    return `
      <a class="media-card" href="${item.url}" target="_blank" rel="noopener noreferrer">
        ${poster}

        <div class="media-content">
          <div class="media-title-row">
            <h3>${item.title || "Untitled"}</h3>
            <span>${typeLabel}</span>
          </div>

          <p>${item.overview || "No overview available."}</p>

          <div class="media-meta">
            <span>${item.releaseDate || "TBC"}</span>
            <span>⭐ ${item.rating || "N/A"}</span>
          </div>
        </div>
      </a>
    `;
  }).join("");
}

function renderGenericLinks(items) {
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

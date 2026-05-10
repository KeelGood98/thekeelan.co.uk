const DATA_PATHS = {
  table: "data/pl_table.json",
  fixtures: "data/mufc_fixtures.json"
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
    loadFixtures()
  ]);

  const lastUpdated = document.getElementById("lastUpdated");
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

  try {
    const data = await fetchJson(DATA_PATHS.table);

    body.innerHTML = data.teams.map((team, index) => `
      <tr>
        <td>${index + 1}</td>
        <td>
          <div class="team-cell">
            ${team.badge ? `<img class="badge" src="${team.badge}" alt="${team.name} badge">` : ""}
            <span>${team.name}</span>
          </div>
        </td>
        <td>${team.played}</td>
        <td>${team.won}</td>
        <td>${team.drawn}</td>
        <td>${team.lost}</td>
        <td>${team.goalDifference}</td>
        <td><strong>${team.points}</strong></td>
      </tr>
    `).join("");
  } catch (error) {
    console.error(error);
    body.innerHTML = `
      <tr>
        <td colspan="8">Could not load Premier League table.</td>
      </tr>
    `;
  }
}

async function loadFixtures() {
  const list = document.getElementById("fixturesList");

  try {
    const data = await fetchJson(DATA_PATHS.fixtures);

    list.innerHTML = data.fixtures.map((fixture) => {
      const resultClass = fixture.result ? `result ${fixture.result}` : "";

      return `
        <article class="fixture">
          <div class="fixture-top">
            <span>${fixture.date}</span>
            <span>${fixture.competition}</span>
          </div>
          <div class="fixture-main">
            ${fixture.home} ${fixture.score ? fixture.score : "vs"} ${fixture.away}
            ${fixture.result ? `<span class="${resultClass}">${fixture.result}</span>` : ""}
          </div>
          <div class="fixture-meta">
            ${fixture.venue || ""}
            ${fixture.channel ? ` · ${fixture.channel}` : ""}
          </div>
        </article>
      `;
    }).join("");
  } catch (error) {
    console.error(error);
    list.innerHTML = "Could not load fixtures.";
  }
}

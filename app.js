const elements = {
  totalMatches: document.querySelector("#total-matches"),
  totalSeasons: document.querySelector("#total-seasons"),
  latestMatch: document.querySelector("#latest-match"),
  generatedAt: document.querySelector("#generated-at"),
  seasonFilter: document.querySelector("#season-filter"),
  teamFilter: document.querySelector("#team-filter"),
  searchInput: document.querySelector("#search-input"),
  resultsCount: document.querySelector("#results-count"),
  matchesGrid: document.querySelector("#matches-grid"),
  matchCardTemplate: document.querySelector("#match-card-template"),
};

let archive = null;

function formatDate(dateText) {
  if (!dateText) return "Unknown date";
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(dateText));
}

function formatGeneratedAt(timestamp) {
  if (!timestamp) return "Archive metadata unavailable.";
  const date = new Date(timestamp);
  return `Generated from downloaded archive on ${date.toLocaleString("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  })}.`;
}

function populateSelect(select, values, allLabel) {
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  });
  select.firstElementChild.textContent = allLabel;
}

function updateSummary(payload) {
  elements.totalMatches.textContent = payload.matchCount.toLocaleString("en-IN");
  elements.totalSeasons.textContent = payload.seasons.length.toString();
  elements.latestMatch.textContent = formatDate(payload.latestMatchDate);
  elements.generatedAt.textContent = formatGeneratedAt(payload.generatedAt);
}

function createInningsRow(innings) {
  const row = document.createElement("div");
  row.className = "innings-row";

  const team = document.createElement("div");
  team.className = "innings-team";
  team.innerHTML = `<strong>${innings.shortName}</strong><span>${innings.team}</span>`;

  const score = document.createElement("div");
  score.className = "innings-score";
  score.textContent = `${innings.runs}/${innings.wickets} (${innings.overs})`;

  row.append(team, score);
  return row;
}

function createMatchCard(match) {
  const fragment = elements.matchCardTemplate.content.cloneNode(true);

  fragment.querySelector(".match-season").textContent = `Season ${match.season}`;
  fragment.querySelector(".match-title").textContent = match.teams
    .map((team) => team.shortName)
    .join(" vs ");
  fragment.querySelector(".match-date").textContent = formatDate(match.date);
  fragment.querySelector(".match-result").textContent = match.resultText;
  fragment.querySelector(".match-venue").textContent = [
    match.venue,
    match.city,
  ]
    .filter(Boolean)
    .join(", ");

  const playerText =
    match.playerOfMatch && match.playerOfMatch.length
      ? `Player of the match: ${match.playerOfMatch.join(", ")}`
      : "Player of the match unavailable";
  fragment.querySelector(".match-player").textContent = playerText;

  const scoreboard = fragment.querySelector(".scoreboard");
  match.innings.forEach((innings) => scoreboard.append(createInningsRow(innings)));

  return fragment;
}

function getFilteredMatches() {
  const season = elements.seasonFilter.value;
  const team = elements.teamFilter.value;
  const query = elements.searchInput.value.trim().toLowerCase();

  return archive.matches.filter((match) => {
    const seasonMatches = season === "all" || match.season === season;
    const teamMatches =
      team === "all" || match.teams.some((entry) => entry.name === team);
    const haystack = [
      match.venue,
      match.city,
      match.resultText,
      ...match.teams.map((entry) => entry.name),
      ...match.teams.map((entry) => entry.shortName),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const queryMatches = !query || haystack.includes(query);

    return seasonMatches && teamMatches && queryMatches;
  });
}

function renderMatches() {
  const matches = getFilteredMatches();
  elements.matchesGrid.innerHTML = "";
  elements.resultsCount.textContent = `${matches.length.toLocaleString("en-IN")} matches shown`;

  if (!matches.length) {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";
    emptyState.textContent = "No matches match the current filters.";
    elements.matchesGrid.append(emptyState);
    return;
  }

  const fragment = document.createDocumentFragment();
  matches.forEach((match) => fragment.append(createMatchCard(match)));
  elements.matchesGrid.append(fragment);
}

async function loadArchive() {
  try {
    const response = await fetch("./data/matches.json");
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }

    archive = await response.json();
    updateSummary(archive);
    populateSelect(elements.seasonFilter, archive.seasons, "All seasons");
    populateSelect(elements.teamFilter, archive.teams, "All teams");
    renderMatches();
  } catch (error) {
    elements.resultsCount.textContent = "Could not load IPL archive data.";
    elements.matchesGrid.innerHTML = `<div class="empty-state">${error.message}</div>`;
  }
}

[elements.seasonFilter, elements.teamFilter].forEach((select) => {
  select.addEventListener("change", renderMatches);
});

elements.searchInput.addEventListener("input", renderMatches);

loadArchive();

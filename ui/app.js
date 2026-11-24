// the two service addresses come from config.js, so the same page works locally and on Azure
const LIBRARY_URL = window.APP_CONFIG.libraryUrl;
const GROUP_URL = window.APP_CONFIG.groupUrl;
// a sleeping Azure service can take about 30 seconds to answer, so a request is given up after 40
const REQUEST_TIMEOUT_MS = 40000;
const STARTING_UP_MESSAGE = "A service could not be reached. If the app has been idle it is starting up, so please try again in a moment.";

function showMessage(text, isError) {
  const message = document.getElementById("message");
  message.textContent = text;
  if (isError) {
    message.className = "message error";
  } else {
    message.className = "message";
  }
  message.hidden = false;
}

async function callService(baseUrl, path, method, body) {
  const options = { method: method, signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS) };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(baseUrl + path, options);
  } catch (error) {
    // a service that is down, still waking up, or too slow all end up here, including Azure's cold-start 503
    console.error(error);
    throw new Error(STARTING_UP_MESSAGE);
  }

  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  if (response.ok) {
    return data;
  }
  if (data !== null && data.error) {
    throw new Error(data.error);
  }
  if (response.status === 503) {
    throw new Error(STARTING_UP_MESSAGE);
  }
  throw new Error("Something went wrong (status " + response.status + ").");
}

async function loadGames() {
  const games = await callService(LIBRARY_URL, "/games", "GET");
  const gameList = document.getElementById("game-list");
  const gameSelect = document.getElementById("rating-game");
  gameList.innerHTML = "";
  gameSelect.innerHTML = "";

  for (const game of games) {
    // textContent shows the text exactly as typed, so a title can never inject HTML into the page
    const item = document.createElement("li");
    item.textContent = game.title + " (" + game.min_players + "-" + game.max_players + " players, " + game.playtime_minutes + " min, owned by " + game.owner + ")";
    gameList.appendChild(item);

    const option = document.createElement("option");
    option.value = game.id;
    option.textContent = game.title;
    gameSelect.appendChild(option);
  }
}

async function loadMembers() {
  const members = await callService(GROUP_URL, "/members", "GET");
  const memberList = document.getElementById("member-list");
  const attendeeChoices = document.getElementById("attendee-choices");
  const memberSelect = document.getElementById("rating-member");
  memberList.innerHTML = "";
  memberSelect.innerHTML = "";
  for (const oldChoice of attendeeChoices.querySelectorAll("label")) {
    oldChoice.remove();
  }

  for (const member of members) {
    const item = document.createElement("li");
    if (member.is_active === 1) {
      item.textContent = member.name;
    } else {
      item.textContent = member.name + " (archived)";
    }
    memberList.appendChild(item);

    // only active members can come to a night or rate a game
    if (member.is_active === 1) {
      const choice = document.createElement("label");
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.name = "attendee_ids";
      checkbox.value = member.id;
      choice.appendChild(checkbox);
      choice.append(" " + member.name);
      attendeeChoices.appendChild(choice);

      const option = document.createElement("option");
      option.value = member.id;
      option.textContent = member.name;
      memberSelect.appendChild(option);
    }
  }
}

async function addGame(event) {
  event.preventDefault();
  const fields = event.target.elements;
  const game = {
    title: fields.title.value,
    owner: fields.owner.value,
    min_players: Number(fields.min_players.value),
    max_players: Number(fields.max_players.value),
    playtime_minutes: Number(fields.playtime_minutes.value)
  };
  try {
    await callService(LIBRARY_URL, "/games", "POST", game);
    event.target.reset();
    showMessage("Added " + game.title + ".", false);
    await loadGames();
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function addMember(event) {
  event.preventDefault();
  const fields = event.target.elements;
  try {
    const member = await callService(GROUP_URL, "/members", "POST", { name: fields.name.value });
    event.target.reset();
    showMessage("Added " + member.name + ".", false);
    await loadMembers();
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function planNight(event) {
  event.preventDefault();
  const form = event.target;
  const attendeeIds = [];
  for (const checkbox of form.querySelectorAll("input[name='attendee_ids']:checked")) {
    attendeeIds.push(Number(checkbox.value));
  }
  const guestNames = [];
  for (const guestName of form.elements.guest_names.value.split(",")) {
    if (guestName.trim() !== "") {
      guestNames.push(guestName.trim());
    }
  }
  const night = {
    night_date: form.elements.night_date.value,
    available_minutes: Number(form.elements.available_minutes.value),
    attendee_ids: attendeeIds,
    guest_names: guestNames
  };

  try {
    const savedNight = await callService(GROUP_URL, "/nights", "POST", night);
    // this call crosses the seam: group asks library which games fit before it scores them
    const plan = await callService(GROUP_URL, "/nights/" + savedNight.id + "/plan", "GET");
    showPlan(plan);
  } catch (error) {
    showMessage(error.message, true);
  }
}

function showPlan(plan) {
  const planList = document.getElementById("plan-list");
  planList.innerHTML = "";
  for (const game of plan.games) {
    const item = document.createElement("li");
    item.textContent = game.title + " (" + game.playtime_minutes + " min, score " + Math.round(game.score * 10) / 10 + ")";
    planList.appendChild(item);
  }
  if (plan.games.length === 0) {
    showMessage("No game in the library fits " + plan.player_count + " players in " + plan.available_minutes + " minutes.", false);
  } else {
    showMessage("Plan for " + plan.player_count + " players on " + plan.night_date + ", with " + plan.minutes_left + " minutes to spare.", false);
  }
}

async function saveRating(event) {
  event.preventDefault();
  const fields = event.target.elements;
  const rating = {
    member_id: Number(fields.member_id.value),
    game_id: Number(fields.game_id.value),
    score: Number(fields.score.value)
  };
  try {
    await callService(GROUP_URL, "/ratings", "PUT", rating);
    event.target.reset();
    showMessage("Rating saved.", false);
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function loadPage() {
  // each service is loaded on its own, so one being down never hides the other one's data
  try {
    await loadGames();
  } catch (error) {
    showMessage(error.message, true);
  }
  try {
    await loadMembers();
  } catch (error) {
    showMessage(error.message, true);
  }
}

document.getElementById("game-form").addEventListener("submit", addGame);
document.getElementById("member-form").addEventListener("submit", addMember);
document.getElementById("night-form").addEventListener("submit", planNight);
document.getElementById("rating-form").addEventListener("submit", saveRating);
loadPage();

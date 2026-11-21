"use strict";

// Dates in the source are local to Tyumen (UTC+5).
function refreshRetakes(now = new Date()) {
  const local = new Date(now.getTime() + 5 * 3600000).toISOString();
  const today = local.slice(0, 10);
  const clock = local.slice(11, 16);
  const confirmed = [];
  const future = document.querySelector("#commissions");
  const past = document.querySelector("#past-commissions");
  const weekly = document.querySelector("#weekly");

  function stillAvailable(date, time) {
    return date > today || (date === today && clock <= time.split("–").pop());
  }
  if (future && past) {
    for (const row of document.querySelectorAll("#retakes li[data-date]")) {
      const {date, time, place} = row.dataset;
      const group = date < today ? past : future;
      const list = group.querySelector("ul");
      if (row.parentElement !== list) list.append(row);
      if (stillAvailable(date, time)) confirmed.push({date, time, place});
    }
    for (const group of [future, past]) group.hidden = !group.querySelector("li");
  }

  let hasWeekly = false;
  for (const row of document.querySelectorAll("#weekly li")) {
    const {from, until, weekday, parity, time, place} = row.dataset;
    row.hidden = until < today;
    if (row.hidden) continue;
    hasWeekly = true;
    // The source gives no calendar anchor for even/odd academic weeks.
    if (parity) continue;
    const first = new Date((from > today ? from : today) + "T00:00:00Z");
    first.setUTCDate(first.getUTCDate() + (Number(weekday) - first.getUTCDay() + 7) % 7);
    let date = first.toISOString().slice(0, 10);
    if (!stillAvailable(date, time)) {
      first.setUTCDate(first.getUTCDate() + 7);
      date = first.toISOString().slice(0, 10);
    }
    if (date <= until) confirmed.push({date, time, place});
  }
  if (weekly) weekly.hidden = !hasWeekly;
  const consult = document.querySelector("#weekly-consultations");
  if (consult && !hasWeekly) consult.textContent = "График консультаций в карточке не указан.";
  document.querySelector("#no-retakes").hidden = hasWeekly || Boolean(future && !future.hidden);
  confirmed.sort((a, b) => a.date.localeCompare(b.date) || a.time.localeCompare(b.time));
  const next = confirmed[0];
  let message = "Ближайшая пересдача не указана.";
  if (next) {
    message = "Ближайшая пересдача по графику · " + next.date.split("-").reverse().join(".") +
      " · " + next.time + " · " + next.place + ".";
  } else if (hasWeekly) {
    message = "Уточните дату по графику приёма кафедры.";
  }
  document.querySelector("#next-retake").textContent = message;
}

refreshRetakes();
window.setInterval(refreshRetakes, 60000);
window.addEventListener("pageshow", () => refreshRetakes());

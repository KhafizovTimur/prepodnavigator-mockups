"use strict";

function tyumenClock(now = new Date()) {
  const iso = new Date(now.getTime() + 5 * 3600000).toISOString();
  return {today: iso.slice(0, 10), clock: iso.slice(11, 16)};
}

function shiftDay(day, offset) {
  const date = new Date(day + "T00:00:00Z");
  date.setUTCDate(date.getUTCDate() + offset);
  return date.toISOString().slice(0, 10);
}

// The weekly timetable supplies weekdays 1–7, but no calendar anchor for parity.
function nextSession(row, {today, clock}) {
  const available = date => date > today || (date === today && clock <= row.time.split("–").pop());
  if (row.date) return available(row.date) ? row.date : null;
  if (row.parity || row.until < today) return null;
  const start = row.from > today ? row.from : today;
  const weekday = new Date(start + "T00:00:00Z").getUTCDay();
  let date = shiftDay(start, (Number(row.weekday) - weekday + 7) % 7);
  if (!available(date)) date = shiftDay(date, 7);
  return date <= row.until ? date : null;
}

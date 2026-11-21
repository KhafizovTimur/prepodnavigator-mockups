"use strict";

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

const home = document.querySelector(".brand").href;
function navigationUrl(path, pageNumber, query, retakes) {
  const url = new URL(path, home);
  if (query) url.searchParams.set("q", query);
  if (pageNumber > 1) url.searchParams.set("page", pageNumber);
  if (retakes) url.searchParams.set("view", "retakes");
  return url;
}

function teacherRow(teacher, info, caption, url, lead = "") {
  const item = element("li");
  const link = element("a", "teacher-row");
  link.href = url;
  if (!lead) {
    const letters = teacher.name.split(/\s+/).slice(0, 2).map(word => word[0]).join("");
    const initials = element("span", "initials", letters);
    initials.setAttribute("aria-hidden", "true");
    link.append(initials);
  }
  const body = element("span", "teacher-info");
  if (lead) body.append(element("span", "event-time", lead));
  body.append(element("strong", "", teacher.name), element("span", "subject", info));
  if (caption) body.append(element("span", "muted", caption));
  const arrow = element("span", "row-arrow", "›");
  arrow.setAttribute("aria-hidden", "true");
  link.append(body, arrow);
  item.append(link);
  return item;
}

function message(title, text) {
  const box = element("div", "empty-state");
  box.append(element("h3", "", title), element("p", "", text));
  return box;
}

const fullDate = new Intl.DateTimeFormat("ru-RU", {day:"numeric", month:"long", year:"numeric", timeZone:"UTC"});
const weekdays = ["", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"];

async function initCatalog(results) {
  const input = document.querySelector("#query");
  const title = document.querySelector("#results-title");
  const total = document.querySelector("#results-total");
  const extra = document.querySelector("#parity-sessions");
  const entry = document.querySelector(".retakes-entry");
  const params = new URLSearchParams(location.search);
  let retakes = params.get("view") === "retakes";
  let page = Math.max(1, Math.trunc(Number(params.get("page"))) || 1);
  let teachers, pageSize;
  input.value = (params.get("q") || "").slice(0,120);
  const key = value => value.trim().toLowerCase().replaceAll("ё", "е");
  const cardUrl = teacher => navigationUrl("teacher/" + teacher.id + "/", page, input.value.trim(), retakes);

  function paginate(rows, draw, emptyBox) {
    const last = Math.max(1, Math.ceil(rows.length / pageSize));
    page = Math.min(page, last);
    total.textContent = "Всего: " + rows.length;
    if (!rows.length) {
      results.replaceChildren(emptyBox);
      return;
    }
    const list = element("ul", "teacher-list");
    for (const row of rows.slice((page - 1) * pageSize, page * pageSize)) list.append(draw(row));
    results.replaceChildren(list);
    if (last <= 1) return;
    const nav = element("nav", "pagination");
    nav.setAttribute("aria-label", "Страницы результатов");
    function addLink(label, number) {
      const link = element("a", "btn", label);
      const url = navigationUrl(home, number, input.value.trim(), retakes);
      url.hash = "results-title";
      link.href = url;
      nav.append(link);
    }
    if (page > 1) addLink("← Назад", page - 1);
    nav.append(element("span", "", "Страница " + page + " из " + last));
    if (page < last) addLink("Дальше →", page + 1);
    results.append(nav);
  }

  let previousEvents;
  function showSessions() {
    const moment = tyumenClock();
    const dated = [], uncertain = [];
    for (const teacher of teachers) {
      for (const row of teacher.sessions || []) {
        const date = nextSession(row, moment);
        if (date) dated.push({teacher, row, date});
        else if (row.parity && row.until >= moment.today) uncertain.push({teacher, row});
      }
    }
    dated.sort((a,b) => a.date.localeCompare(b.date) || a.row.time.localeCompare(b.row.time) ||
      a.teacher.name.localeCompare(b.teacher.name,"ru"));
    const signature = moment.today + "|" + dated.map(event =>
      [event.teacher.id, event.date, event.row.time, event.row.place].join("/")
    ).join("|");
    if (signature === previousEvents) return;
    previousEvents = signature;
    function eventRow({teacher, row, date}) {
      const url = cardUrl(teacher);
      url.hash = "retakes";
      const when = date ? fullDate.format(new Date(date + "T00:00:00Z")) :
        weekdays[row.weekday] + " · " + (row.parity === "odd" ? "нечётная" : "чётная") + " неделя";
      const label = row.date ? "Комиссия" : "Приём";
      const note = [label, row.subject, row.note].filter(Boolean).join(" · ");
      return teacherRow(teacher, row.place, note, url, when + " · " + row.time);
    }
    paginate(dated, eventRow, message("Ближайших дат нет", "Уточните время приёма на кафедре."));
    extra.replaceChildren();
    if (uncertain.length) {
      const details = element("details", "parity-list");
      details.append(element("summary", "", "Приём по чётности недели (" + uncertain.length + ")"),
        element("p", "muted", "В графике указана чётность недели. Конкретную дату уточните на кафедре."));
      const list = element("ul","teacher-list");
      for (const event of uncertain) list.append(eventRow(event));
      details.append(list);
      extra.append(details);
    }
  }

  function render() {
    entry.textContent = retakes ? "← К каталогу преподавателей" : "Ближайшие пересдачи ›";
    entry.href = retakes ? home : new URL("?view=retakes#results-title", home);
    title.textContent = retakes ? "Ближайшие пересдачи" : input.value.trim() ? "Результаты поиска" : "Каталог преподавателей";
    if (!teachers) return;
    if (retakes) { showSessions(); return; }
    previousEvents = undefined;
    extra.replaceChildren();
    const words = key(input.value).split(/\s+/).filter(Boolean);
    const matches = value => words.every(word => key(value).includes(word));
    const found = [];
    for (const teacher of teachers) {
      const subjects = words.length ? teacher.subjects.filter(matches) : [];
      if (matches(teacher.name) || subjects.length) found.push({teacher, subjects: subjects.length ? subjects : teacher.subjects});
    }
    paginate(found, ({teacher, subjects}) => {
      const more = subjects.length > 2 ? " и ещё " + (subjects.length - 2) : "";
      return teacherRow(teacher, subjects.slice(0,2).join(", ") + more, teacher.affiliation, cardUrl(teacher));
    }, message("Ничего не найдено", "Попробуйте часть фамилии или названия предмета."));
  }

  function search() {
    retakes = false;
    page = 1;
    history.replaceState(null, "", navigationUrl(home, page, input.value.trim(), false));
    render();
  }
  input.addEventListener("input", search);
  input.form.addEventListener("submit", event => {
    event.preventDefault();
    search();
    title.focus();
  });
  render();
  try {
    const response = await fetch(new URL("catalog.json",home));
    if (!response.ok) throw Error("catalog");
    ({teachers, pageSize} = await response.json());
    render();
    if (retakes) {
      window.setInterval(() => { if (retakes && !document.hidden) showSessions(); }, 60000);
      window.addEventListener("pageshow", () => { if (retakes) showSessions(); });
    }
  } catch {
    results.replaceChildren(message("Каталог пока недоступен", "Обновите страницу, чтобы попробовать ещё раз."));
  }
}

function initWeekPicker(select) {
  const params = new URLSearchParams(location.search);
  const back = document.querySelector(".back-link");
  const backToRetakes = params.get("view") === "retakes";
  const backUrl = navigationUrl(home, Number(params.get("page")), params.get("q"), backToRetakes);
  if (backToRetakes) { backUrl.hash = "results-title"; back.textContent = "← К ближайшим пересдачам"; }
  back.href = backUrl;
  const picker = document.querySelector(".week-picker");
  const schedule = document.querySelector("#week-schedule");
  const today = tyumenClock().today;
  const monday = shiftDay(today, -(new Date(today + "T00:00:00Z").getUTCDay() + 6) % 7);
  const parityKeys = ["odd","even"].filter(key => [...select.options].some(option => option.value === key));
  const shortDate = new Intl.DateTimeFormat("ru-RU", {day:"numeric", month:"short", timeZone:"UTC"});
  const labelFor = key => shortDate.format(new Date(key + "T00:00:00Z")) + " – " +
    shortDate.format(new Date(shiftDay(key,6) + "T00:00:00Z"));
  const original = select.value;
  if (![...select.options].some(option => option.value === monday)) select.add(new Option(labelFor(monday),monday));
  const weeks = [...select.options].map(option => option.value).filter(key => /^\d{4}-/.test(key)).sort();
  const requested = params.get("period");
  const valid = [...select.options].some(option => option.value === requested);
  let current = valid ? requested : original || monday;
  const templates = new Map([...document.querySelectorAll("template[data-period]")].map(t => [t.dataset.period,t]));
  const empty = document.querySelector("#empty-schedule");
  const prev = picker.querySelector("[data-prev]"), next = picker.querySelector("[data-next]");
  const parity = picker.querySelector("[data-parity]");
  function sequence() { return parityKeys.includes(current) ? parityKeys : weeks; }

  function display(key, changeUrl) {
    if (!key) return;
    const address = new URL(location.href);
    address.searchParams.set("period", key);
    if (!empty && changeUrl) { address.hash = "schedule-title"; location.assign(address); return; }
    if (changeUrl) history.replaceState(null, "", address);
    current = select.value = key;
    const isParity = parityKeys.includes(key);
    const keys = sequence();
    const index = keys.indexOf(key);
    prev.disabled = index <= 0;
    next.disabled = index >= keys.length - 1;
    parity.hidden = !parityKeys.length || isParity;
    picker.querySelector("[data-week-label]").textContent = isParity ? select.selectedOptions[0].textContent : labelFor(key);
    if (empty) {
      if (changeUrl) schedule.classList.add("is-updated");
      schedule.replaceChildren((templates.get(key) || empty).content.cloneNode(true));
    }
    const recurringHint = parityKeys.length ? " Расписание по чётности доступно отдельно." : "";
    document.querySelector("#period-note").textContent = isParity ? "ТИУ указал чётность недели без конкретных дат." :
      (key === monday ? "Текущая неделя по Тюмени." : "Занятия с датами по расписанию ТИУ.") + recurringHint;
    const day = schedule.querySelector('[data-date="' + today + '"] h3');
    if (day && !day.querySelector("small")) day.append(element("small", "today-label", "Сегодня"));
  }
  prev.onclick = () => display(sequence()[sequence().indexOf(current)-1],true);
  next.onclick = () => display(sequence()[sequence().indexOf(current)+1],true);
  picker.querySelector("[data-today]").onclick = () => display(monday,true);
  parity.onclick = () => display(parityKeys[0],true);
  display(current,false);
  select.form.hidden = true;
  picker.hidden = false;
}

const results = document.querySelector("#results");
if (results) initCatalog(results);
const period = document.querySelector("#period");
if (period) initWeekPicker(period);

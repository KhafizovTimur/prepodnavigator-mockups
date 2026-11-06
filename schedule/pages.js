"use strict";

const params = new URLSearchParams(location.search);
const query = (params.get("q") || "").slice(0, 120).trim();
const mode = params.get("by") === "subject" ? "subject" : "name";
const requestedPage = Number(params.get("page"));
const page = Number.isSafeInteger(requestedPage) ? Math.max(1, requestedPage) : 1;

function searchUrl(path, pageNumber = page) {
  const url = new URL(path, location.href);
  if (query) url.searchParams.set("q", query);
  if (mode === "subject") url.searchParams.set("by", mode);
  if (pageNumber > 1) url.searchParams.set("page", pageNumber);
  return url;
}

function element(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value) node.textContent = value;
  return node;
}

function teacherLink(teacher, subjects, pageNumber) {
  const item = element("li");
  const link = element("a", "teacher-row");
  link.href = searchUrl(`./teacher/${teacher.id}/`, pageNumber);
  const initials = element("span", "initials", teacher.name.split(/\s+/).slice(0, 2).map(word => word[0]).join("").toUpperCase());
  initials.setAttribute("aria-hidden", "true");
  const arrow = element("span", "row-arrow", "→");
  arrow.setAttribute("aria-hidden", "true");
  const info = element("span", "teacher-info");
  let subjectLine = subjects.slice(0, 2).join(", ");
  if (subjects.length > 2) subjectLine += ` и ещё ${subjects.length - 2}`;
  info.append(
    element("strong", "", teacher.name),
    element("span", "muted", teacher.affiliation || "Кафедра не указана"),
    element("span", "subject", subjectLine),
  );
  link.append(initials, info, arrow);
  item.append(link);
  return item;
}

function pagination(current, last) {
  const nav = element("nav", "pagination");
  nav.setAttribute("aria-label", "Страницы результатов");
  if (current > 1) {
    const previous = element("a", "btn", "← Назад");
    previous.href = searchUrl("./", current - 1);
    nav.append(previous);
  }
  nav.append(element("span", "", `Страница ${current} из ${last}`));
  if (current < last) {
    const next = element("a", "btn", "Дальше →");
    next.href = searchUrl("./", current + 1);
    nav.append(next);
  }
  return nav;
}

function message(results, title, body) {
  const panel = element("div", "empty-state");
  panel.append(element("h3", "", title), element("p", "", body));
  results.replaceChildren(panel);
}

async function showResults(results) {
  document.querySelector("#query").value = query;
  document.querySelector(`input[name="by"][value="${mode}"]`).checked = true;
  if (query) document.querySelector("#results-title").textContent = "Результаты поиска";
  const words = query.toLowerCase().replaceAll("ё", "е").split(/\s+/).filter(Boolean);
  const matches = value => {
    const key = value.toLowerCase().replaceAll("ё", "е");
    return words.every(word => key.includes(word));
  };
  try {
    const response = await fetch("./catalog.json");
    if (!response.ok) throw new Error("Каталог недоступен");
    const { teachers, pageSize } = await response.json();
    const found = [];
    for (const teacher of teachers) {
      if (mode === "subject") {
        const subjects = teacher.subjects.filter(matches);
        if (subjects.length) found.push([teacher, subjects]);
      } else if (matches(teacher.name)) {
        found.push([teacher, teacher.subjects]);
      }
    }
    document.querySelector("#results-total").textContent = `Всего: ${found.length}`;
    if (!found.length) {
      message(results, "Ничего не найдено", "Проверьте написание или попробуйте часть фамилии или названия предмета.");
      return;
    }
    const last = Math.ceil(found.length / pageSize);
    const current = Math.min(page, last);
    const list = element("ul", "teacher-list");
    for (const [teacher, subjects] of found.slice((current - 1) * pageSize, current * pageSize)) {
      list.append(teacherLink(teacher, subjects, current));
    }
    results.replaceChildren(list);
    if (last > 1) results.append(pagination(current, last));
  } catch (error) {
    message(results, "Каталог пока недоступен", "Обновите страницу, чтобы попробовать ещё раз.");
  }
}

function showTeacher(period) {
  const schedule = document.querySelector("#week-schedule");
  const note = document.querySelector("#period-note");
  const templates = new Map(
    Array.from(document.querySelectorAll("template[data-period]"), template => [template.dataset.period, template]),
  );
  document.querySelector(".back-link").href = searchUrl("../../");

  function selectWeek(value) {
    const template = templates.get(value) || document.querySelector("#empty-schedule");
    schedule.replaceChildren(template.content.cloneNode(true));
    note.textContent = value === "odd" || value === "even"
      ? "ТИУ указал чётность недели без конкретных дат."
      : "Здесь показаны занятия, для которых ТИУ указал даты.";
  }

  const requested = params.get("period");
  if (Array.from(period.options).some(option => option.value === requested)) {
    period.value = requested;
    selectWeek(requested);
  }
  period.form.addEventListener("submit", event => {
    event.preventDefault();
    selectWeek(period.value);
    const url = new URL(location.href);
    url.searchParams.set("period", period.value);
    history.replaceState(null, "", url);
  });
}

const results = document.querySelector("#results");
if (results) showResults(results);
const period = document.querySelector("#period");
if (period) showTeacher(period);

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from html import escape
from string import Template
from urllib.parse import urlencode

from .database import search_key
from .source import ROOT, SOURCE

LAYOUT = Template((ROOT / "web" / "index.html").read_text(encoding="utf-8"))
WEEKDAYS = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")
PARITIES = {"odd": "Нечётная неделя", "even": "Чётная неделя"}
FORMS = {"full_time": "Очная форма", "part_time": "Заочная форма"}
TYUMEN = timezone(timedelta(hours=5))
DETAILS = json.loads((ROOT / "data" / "teacher-details.json").read_text(encoding="utf-8"))
RETAKES = json.loads((ROOT / "data" / "retakes.json").read_text(encoding="utf-8"))
RETAKE_COURSE = "https://educon2.tyuiu.ru/course/view.php?id=28774"
DEPARTMENTS = {
    (search_key(row["name"]), row["institute"]): row for row in DETAILS["departments"]
}


def url(path="/", **params):
    query = urlencode({key: value for key, value in params.items() if value})
    return escape(f"{path}?{query}" if query else path)


def layout(title, content, root="/"):
    script = f'<script src="{root}assets/session-dates.js" defer></script><script src="{root}pages.js" defer></script>'
    script += f'<script src="{root}assets/teacher-tools.js" defer></script>'
    return LAYOUT.substitute(title=escape(title), source=SOURCE, content=content, root=root, script=script)


def initials(name):
    return escape("".join(part[0].upper() for part in name.split()[:2]))


def empty(title, message):
    return f'<div class="empty-state"><h3>{escape(title)}</h3><p>{escape(message)}</p></div>'


def affiliation(teacher):
    return " · ".join(filter(None, (teacher["department"], teacher["institute"])))


def teacher_row(teacher, subjects, query, mode, page):
    href = url(f"/teacher/{teacher['id']}", q=query, by=mode, page=page if page > 1 else None)
    subject_line = ", ".join(subjects[:2])
    if len(subjects) > 2:
        subject_line += f" и ещё {len(subjects) - 2}"
    return f'''<li><a class="teacher-row" href="{href}">
      <span class="initials" aria-hidden="true">{initials(teacher['name'])}</span>
      <span class="teacher-info"><strong>{escape(teacher['name'])}</strong>
      <span class="muted">{escape(affiliation(teacher) or 'Кафедра не указана')}</span>
      <span class="subject">{escape(subject_line)}</span></span>
      <span class="row-arrow" aria-hidden="true">→</span>
    </a></li>'''


def pagination(query, mode, page, pages):
    if pages == 1:
        return ""
    previous = f'<a class="btn" rel="prev" href="{url(q=query, by=mode, page=page - 1)}">← Назад</a>' if page > 1 else ""
    following = f'<a class="btn" rel="next" href="{url(q=query, by=mode, page=page + 1)}">Дальше →</a>' if page < pages else ""
    return f'<nav class="pagination" aria-label="Страницы результатов">{previous}<span>Страница {page} из {pages}</span>{following}</nav>'


def search_view(query, mode, teachers, subjects, total, page, pages, *, static=False, retake_index=False):
    root = "./" if static else "/"
    if retake_index:
        results = '<p>Загружаем графики приёма…</p><noscript>Включите JavaScript, чтобы посмотреть ближайшие пересдачи.</noscript>'
    elif static:
        results = '''<p>Загружаем каталог преподавателей…</p>
          <noscript><p>Включите JavaScript в браузере, чтобы искать преподавателей.</p></noscript>'''
    elif teachers:
        rows = "".join(teacher_row(teacher, subjects[teacher["id"]], query, mode, page) for teacher in teachers)
        results = f'<ul class="teacher-list">{rows}</ul>{pagination(query, mode, page, pages)}'
    else:
        results = empty("Ничего не найдено", "Проверьте написание или попробуйте часть фамилии или названия предмета.")
    return layout("Поиск преподавателя", f'''
      <section class="search-hero"><div class="container hero-inner">
        <h1>Найти преподавателя</h1>
        <p class="lead">Посмотрите, когда и в каком кабинете проходят занятия.</p>
        <form class="search-form" action="{root}" method="get" role="search">
          <div class="search-box"><div class="search-input-wrap"><span class="search-icon" aria-hidden="true"></span>
            <label for="query" class="visually-hidden">Фамилия или название предмета</label>
            <input type="search" id="query" name="q" value="{escape(query)}" maxlength="120" autocomplete="off" aria-describedby="search-hint" placeholder="Фамилия или предмет">
          </div><button class="btn btn-primary" type="submit">Найти <span aria-hidden="true">→</span></button></div>
          <p id="search-hint" class="muted">Например, <a href="{url(root, q='Конев')}">Конев</a> или <a href="{url(root, q='Математика')}">Математика</a>.</p>
        </form>
        <a class="retakes-entry" href="?view=retakes#results-title">Ближайшие пересдачи <span aria-hidden="true">›</span></a>
        <section class="favorites" aria-labelledby="favorites-title" data-favorites data-card-pattern="{root}teacher/ID{'/' if static else ''}" hidden>
          <h2 id="favorites-title">Избранные преподаватели</h2>
          <ul></ul>
          <span class="muted" role="status"></span>
        </section>
      </div></section>
      <section class="container search-results" aria-labelledby="results-title">
        <div class="results-heading"><h2 id="results-title" tabindex="-1">{'Результаты поиска' if query else 'Каталог преподавателей'}</h2><span id="results-total" role="status">{'' if static else f'Всего: {total}'}</span></div>
        <div id="parity-sessions"></div>
        <div id="results">{results}</div>
      </section>''', root)


def week_label(value):
    if value in PARITIES:
        return PARITIES[value]
    first = date.fromisoformat(value)
    last = first + timedelta(days=6)
    return f"{first:%d.%m}–{last:%d.%m.%Y}"


def default_period(available):
    today = datetime.now(TYUMEN).date()
    monday = (today - timedelta(days=today.weekday())).isoformat()
    if monday in available:
        return monday
    for parity in PARITIES:
        if parity in available:
            return parity
    dated = sorted(available)
    return next((period for period in dated if period >= monday), dated[-1] if dated else monday)


def lesson_view(lesson):
    groups = ", ".join(f"{group} (подгр. {subgroup})" if subgroup else group for group, subgroup in json.loads(lesson["groups"]))
    details = " · ".join(filter(None, (lesson["kind"], groups)))
    room = lesson["room"]
    if room and lesson["building"]:
        room = f"Каб. {room}"
    location = " · ".join(filter(None, (lesson["building"], lesson["address"])))
    return f'''<li><details class="lesson"><summary>
      <span class="time">{lesson['starts']}–{lesson['ends']}</span>
      <span class="lesson-room">{escape(room or "Кабинет не указан")}</span>
      <span class="lesson-subject">{escape(lesson["subject"])}</span>
      <span class="lesson-place">{escape(location)}</span>
      <span class="lesson-arrow" aria-hidden="true">›</span></summary>
      <p>{escape(details or "Вид занятия и группа не указаны.")}</p></details></li>'''


def day_view(lessons):
    first = lessons[0]
    heading = WEEKDAYS[first["day"] - 1]
    if first["date"]:
        day = date.fromisoformat(first["date"])
        heading += f", {day.day} {MONTHS[day.month - 1]}"
    rows = "".join(lesson_view(lesson) for lesson in lessons)
    return f'<section class="schedule-day" data-date="{first["date"]}"><h3>{heading}</h3><ul>{rows}</ul></section>'


def schedule_view(lessons):
    days = defaultdict(list)
    for lesson in lessons:
        days[lesson["day"]].append(lesson)
    schedule = "".join(day_view(day) for day in days.values())
    return schedule or empty("Нет занятий в этом разделе", "Выберите другую неделю или проверьте расписание на сайте ТИУ.")


def teacher_details(teacher):
    record = DETAILS["teachers"].get(str(teacher["id"]), {})
    if record.get("name") != teacher["name"]:
        return {}
    return record


def source_link(source, label):
    return f'<a href="{escape(DETAILS["sources"][source])}">{escape(label)} ↗</a>'


def contact_view(teacher):
    department = DEPARTMENTS.get((search_key(teacher["department"]), teacher["institute"]))
    if department is None:
        return f'''<section class="side-panel"><h2>Контакты кафедры</h2>
          <p class="muted">Адрес, кабинет, этаж и контакты кафедры в карточке не указаны.</p>
          <p>{source_link("departments", "Справочник ТИУ")}</p></section>'''
    address = escape(department.get("address", "Адрес и кабинет не указаны"))
    email = escape(department["email"])
    phone = escape(department.get("phone", ""))
    phone_line = f"<br>{phone}" if phone else ""
    checked = date.fromisoformat(department.get("checked", DETAILS["checked"])).strftime("%d.%m.%Y")
    return f'''<section class="side-panel"><h2>Контакты кафедры</h2>
      <p>{address}<br><span class="muted">Этаж не указан</span></p>
      <p><a href="mailto:{email}">{email}</a>{phone_line}</p>
      <p class="side-note">Сверено {checked}. {source_link("departments", "Справочник ТИУ")}</p></section>'''


def format_date(value):
    return date.fromisoformat(value).strftime("%d.%m.%Y")


def retake_sources(row):
    references = (
        f'{escape(RETAKES["sources"][ref["document"]])}, стр. {ref["page"]}'
        for ref in row["sources"]
    )
    return f'<small class="muted">Источник · {" · ".join(references)}</small>'


def commission_list(rows):
    entries = []
    for row in rows:
        role = "Председатель комиссии" if row["chair"] else "Член комиссии"
        note = f'<br><small>{escape(row["note"])}</small>' if "note" in row else ""
        entries.append(f'''<li data-date="{row['date']}" data-time="{escape(row['time'])}" data-place="{escape(row['place'])}"><strong>{format_date(row["date"])} · {escape(row["time"])}</strong><br>
          {escape(row["subject"])}<br>{escape(row["groups"])}<br>
          {escape(row["place"])} · {role}{note}<br>{retake_sources(row)}</li>''')
    return f'<ul class="retake-list">{"".join(entries)}</ul>'


def retake_view(weekly, commissions, archive):
    today = datetime.now(TYUMEN).date().isoformat()
    active_weekly = [row for row in weekly if row["until"] >= today]
    upcoming = [row for row in commissions if row["date"] >= today]
    past = [row for row in commissions if row["date"] < today]
    parts = []
    if active_weekly:
        windows = []
        for row in active_weekly:
            day = WEEKDAYS[row["weekday"] - 1]
            parity = f' · {PARITIES[row["parity"]].lower()}' if row["parity"] else ""
            windows.append(f'''<li data-weekday="{row['weekday']}" data-from="{row['from']}" data-until="{row['until']}" data-parity="{row['parity']}" data-time="{escape(row['time'])}" data-place="{escape(row['place'])}"><strong>{day}{parity} · {escape(row["time"])}</strong><br>
              {escape(row["place"])}<br>
              <small class="muted">С {format_date(row["from"])} по {format_date(row["until"])}</small><br>
              {retake_sources(row)}</li>''')
        parts.append(f'<div id="weekly"><h3>Еженедельный приём</h3><ul class="retake-list">{"".join(windows)}</ul></div>')
    if commissions:
        hidden_upcoming = "" if upcoming else " hidden"
        hidden_past = "" if past else " hidden"
        parts.append(f'<div id="commissions"{hidden_upcoming}><h3>Комиссии по датам</h3>{commission_list(upcoming)}</div>')
        parts.append(f'<details id="past-commissions"{hidden_past}><summary>Прошедшие комиссии</summary>{commission_list(past)}</details>')
    hidden_empty = " hidden" if active_weekly or upcoming else ""
    parts.append(f'<p id="no-retakes" class="muted"{hidden_empty}>Актуальный график пересдач в карточке не указан.</p>')
    if archive:
        entries = "".join(
            f'<li><strong>{format_date(row["date"])} · {escape(row["time"])}</strong><br>{escape(row["place"])}</li>'
            for row in archive
        )
        parts.append(f'''<details><summary>Архив пересдач · июнь 2026</summary>
          <ul>{entries}</ul><p>{source_link("retake-surgut", "Архивный график ТИУ")}</p></details>''')
    if weekly or commissions:
        parts.append(f'<p><a href="{RETAKE_COURSE}">Распоряжения ИМЦТ в Educon2 ↗</a></p>')
    else:
        parts.append('<p>Уточните дату на кафедре или в <a href="https://educon2.tyuiu.ru/">Educon2</a>.</p>')
    return "".join(parts)


def appointments_view(teacher):
    record = teacher_details(teacher)
    retakes = RETAKES["teachers"].get(str(teacher["id"]), {})
    if retakes.get("name") != teacher["name"]:
        retakes = {}
    weekly = retakes.get("weekly", [])
    commissions = retakes.get("commissions", [])
    consultation = record.get("consultation")
    if consultation:
        consultations = f'''<p>Для аспирантов 2–5 курсов, осенний семестр 2026/27.</p>
          <p><strong>{escape(consultation["day"])} · {escape(consultation["time"])}</strong><br>
          {escape(consultation["subject"])} · {escape(consultation["place"])}</p>
          <p>{source_link(consultation["source"], "График консультаций ТИУ")}</p>'''
    elif any(row["consultations"] and row["until"] >= datetime.now(TYUMEN).date().isoformat() for row in weekly):
        consultations = '<p id="weekly-consultations">В ИМЦТ консультации проходят по <a href="#retakes">общему графику приёма</a>.</p>'
    else:
        consultations = '<p class="muted">График консультаций в карточке не указан.</p>'

    return f'''<div class="appointment-panels">
      <section class="side-panel"><h2>Консультации</h2>{consultations}</section>
      <section class="side-panel" id="retakes"><h2>Пересдачи</h2>
        {retake_view(weekly, commissions, record.get("retake_archive", []))}
      </section></div>'''


def teacher_view(teacher, lessons, weeks, period, query, mode, page, updated, *, static_schedules=None, available=None):
    static = static_schedules is not None
    root = "../../" if static else "/"
    back = url(root, q=query, by=mode, page=page if page > 1 else None)
    action = "./" if static else f"/teacher/{teacher['id']}"
    templates = ""
    if static:
        templates = "".join(f'<template data-period="{key}">{schedule_view(rows)}</template>' for key, rows in static_schedules.items())
        templates += f'<template id="empty-schedule">{schedule_view([])}</template>'
    available = set(static_schedules) if static else set(available or ())
    periods = {key: label for key, label in PARITIES.items() if key in available or key == period}
    periods.update({week: week_label(week) for week in weeks})
    options = "".join(f'<option value="{key}"{" selected" if key == period else ""}>{value}</option>' for key, value in periods.items())
    sources = json.loads(teacher["sources"])
    links = "".join(f'<li><a href="{escape(source["url"])}">{escape(FORMS.get(source["form"], "Расписание ТИУ"))} ↗</a></li>' for source in sources)
    stamp = datetime.fromisoformat(updated).astimezone(TYUMEN).strftime("%d.%m.%Y, %H:%M")
    note = "ТИУ указал чётность недели без конкретных дат." if period in PARITIES else "Здесь показаны занятия, для которых ТИУ указал даты."
    return layout(teacher["name"], f'''
      <div class="container teacher-page" data-teacher-id="{teacher['id']}">
        <a class="back-link" href="{back}">← К поиску преподавателя</a>
        <div class="teacher-heading"><span class="initials" aria-hidden="true">{initials(teacher['name'])}</span>
          <div><h1>{escape(teacher['name'])}</h1><p class="lead">{escape(affiliation(teacher))}</p></div>
        </div>
        <div class="teacher-actions" hidden>
          <button class="btn" type="button" data-favorite-toggle aria-pressed="false">В избранное</button>
          <button class="btn" type="button" data-share>Поделиться карточкой</button>
          <span class="muted" role="status"></span>
          <label hidden>Ссылка на карточку <input type="url" readonly></label>
        </div>
        <div class="teacher-layout">
          <div>
          <section aria-labelledby="schedule-title">
            <p class="week-panel"><strong id="next-retake"></strong> <a href="#retakes">К графику пересдач ↓</a></p>
            <div class="week-panel"><h2 id="schedule-title">Расписание занятий</h2>
              <form class="week-form" action="{action}" method="get">
                <input type="hidden" name="q" value="{escape(query)}"><input type="hidden" name="by" value="{mode}">
                <input type="hidden" name="page" value="{page}">
                <label for="period" class="visually-hidden">Неделя расписания</label>
                <select id="period" name="period" aria-describedby="period-note">{options}</select>
                <button type="submit" class="btn">Показать</button>
              </form>
              <div class="week-picker" hidden>
                <div class="week-track"><button class="btn" type="button" data-prev aria-label="Предыдущая неделя">‹</button>
                  <strong data-week-label aria-live="polite"></strong>
                  <button class="btn" type="button" data-next aria-label="Следующая неделя">›</button></div>
                <button class="btn" type="button" data-today>Сегодня</button>
                <button class="week-parity" type="button" data-parity hidden>По чётности</button>
              </div>
              <p id="period-note" class="muted">{note}</p>
            </div>
            <div id="week-schedule" aria-live="polite">{schedule_view(lessons)}</div>
            {templates}
          </section>
          {appointments_view(teacher)}
          </div>
          <aside class="teacher-sidebar"><section class="side-panel"><h2>Источник расписания</h2>
            <p>Расписание взято с <a href="{SOURCE}">сайта ТИУ ↗</a></p>
            <ul>{links}</ul><p class="side-note">Загружено {stamp} по Тюмени.</p>
          </section>{contact_view(teacher)}</aside>
          <script src="{root}assets/retakes.js" defer></script>
        </div>
      </div>''', root)


def message_view(title, text):
    return layout(title, f'<div class="container message"><h1>{escape(title)}</h1><p>{escape(text)}</p><a href="/" class="btn">К поиску</a></div>')

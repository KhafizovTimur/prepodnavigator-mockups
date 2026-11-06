(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const shell = $('#app-shell');
  const content = $('#app-content');
  const statePicker = $('#demo-state');
  const teacher = {name:'Иванов Алексей Сергеевич',department:'Кафедра прикладной информатики',subject:'Математика · Информационные системы'};
  // Form actions switch the demo state in this tab.
  const state = {route:'search',view:'normal',date:'2026-10-26',from:'14:00',to:'15:00',room:'214',building:'Корпус 1',comment:'Консультация по математике'};
  const options = {
    search:[['normal','Результат поиска'],['empty','Пустой поиск']],
    teacher:[['normal','Обычная карточка'],['stale','Устаревшие сведения']],
    status:[['normal','Форма статуса'],['confirmation','Вид подтверждения']],
    subscribe:[['normal','Форма подписки'],['connected','Подписка подключена'],['cancelled','Подписка отменена']]
  };
  const escape = (v) => String(v).replace(/[&<>"']/g,(c)=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const dateLabel = () => '26 октября';
  const btn = (text,route,cls='') => `<a class="btn ${cls}" href="#${route}">${text}</a>`;
  const crumb = (name) => `<div class="breadcrumb"><a href="#search">Кафедра Онлайн</a><span> / </span><span>${name}</span></div>`;
  const teacherMini = () => `<div class="selected-teacher"><span class="initials">ИА</span><div><h3>${teacher.name}</h3><p>${teacher.department}</p></div></div>`;
  function renderSearch() {
    const empty = state.view === 'empty';
    return `<section class="search-hero"><div class="content-width">${crumb('Поиск преподавателя')}<h1>Найти преподавателя</h1><p class="lead">Кабинет, консультации и пересдачи — в одной карточке.</p><div class="search-form"><div class="search-types"><button type="button" disabled aria-pressed="true">По ФИО</button><button type="button" disabled aria-pressed="false">По предмету</button></div><div class="search-box"><div class="search-input-wrap"><span class="search-icon" aria-hidden="true"></span><input aria-label="Пример поискового запроса" value="${empty ? 'Нет совпадений' : 'Иванов'}" readonly></div><button class="btn btn-primary" type="button" disabled>Найти →</button></div></div></div></section><div class="content-width search-results"><div class="results-heading"><h2>${empty ? 'Результаты поиска' : 'Результаты: 1'}</h2></div>${empty ? '<div class="empty-state"><h3>Ничего не найдено</h3><p>Проверьте написание ФИО или попробуйте ввести часть фамилии.</p></div>' : `<a class="teacher-row" href="#teacher"><span class="initials">ИА</span><div class="teacher-info"><h3>${teacher.name}</h3><p>${teacher.department}</p><span class="subject">${teacher.subject}</span></div><div class="row-status"><span class="pill pill-blue">Консультация 26 октября</span><strong>14:00–15:00 · кабинет 214</strong></div><span class="row-arrow" aria-hidden="true">→</span></a>`}</div>`;
  }
  function renderTeacher() {
    const stale = state.view === 'stale';
    return `<div class="content-width"><a href="#search" class="back-link">← К результатам поиска</a><div class="teacher-heading"><div class="name-block"><span class="initials">ИА</span><div><h1>${teacher.name}</h1><p class="lead">${teacher.department}<br>${teacher.subject}</p></div></div></div><div class="teacher-layout"><div><section class="status-banner ${stale ? 'warning' : ''}"><div class="status-title-row"><h2>Статус на ${dateLabel(state.date)}</h2><span class="pill ${stale ? 'pill-amber' : 'pill-blue'}">${stale ? 'Нужно уточнить' : 'Опубликовано кафедрой'}</span></div>${stale ? '<div class="status-main"><span>На выбранную дату статус не опубликован</span></div><p class="status-description">Последний статус был на 23 октября. Не используйте его как актуальный — уточните время на кафедре.</p><p class="status-meta">Последнее обновление: 23.10.2026, 09:15 · Контакты кафедры указаны ниже</p>' : `<div class="status-main"><strong>${state.from}–${state.to}</strong><span>${escape(state.building)} · кабинет ${escape(state.room)}</span></div><p class="status-description">${escape(state.comment)}</p><p class="status-meta">Обновлено 26.10.2026, 09:15 · Сотрудник кафедры<br>Официально опубликованный план приёма, не отслеживание местоположения</p>`}</section><section><div class="section-heading"><h2>Расписание занятий</h2><span class="small muted">26 октября, понедельник</span></div><div class="schedule-row"><span class="time">10:00–11:30</span><div>${teacher.subject.split(" · ")[0]}<p>Лекция · пример расписания</p></div><span class="where">Корпус 1 · каб. 306</span></div><div class="schedule-row"><span class="time">12:00–13:30</span><div>${teacher.subject.split(" · ")[1]}<p>Практическое занятие</p></div><span class="where">Корпус 1 · каб. 214</span></div></section><hr class="rule"><section><h2>Консультации и пересдачи</h2><div class="schedule-row"><span class="time">26 октября<br>14:00–15:00</span><div>Консультация<p>${teacher.subject.split(" · ")[0]}</p></div><span class="where">Корпус 1 · каб. 214</span></div><div class="schedule-row"><span class="time">30 октября<br>16:00–17:00</span><div>Пересдача<p>${teacher.subject.split(" · ")[0]} · по предварительной записи</p></div><span class="where">Корпус 1 · каб. 214</span></div></section></div><aside class="side-panel"><h2>Кафедра и контакты</h2><dl class="details-list"><div class="wide-detail"><dt>Кафедра</dt><dd>${teacher.department.replace("Кафедра ", "")}</dd></div><div><dt>Где находится</dt><dd>${escape(state.building)}, этаж 2<br>Кабинет ${escape(state.room)}</dd></div><div><dt>Почта кафедры</dt><dd><a href="mailto:kafedra@example.com">kafedra@example.com</a></dd></div><div class="wide-detail"><dt>Источник сведений</dt><dd>Расписание и публикация кафедры<br><span class="muted">Учебный пример</span></dd></div></dl><div class="subscription-shortcut">${btn('Подписаться на изменения','subscribe','btn-primary btn-block')}</div><p class="side-note">Сведения о занятиях обновлены 26.10.2026 в 09:00. При изменениях ориентируйтесь на свежий статус кафедры.</p></aside></div></div>`;
  }


  function renderStatus() {
    return `<div class="content-width form-page">${crumb('Форма статуса')}<div class="form-page-head"><h1>Опубликовать статус</h1><p class="lead">Форма для преподавателя или сотрудника кафедры.</p></div><section class="form-panel mock-form"><div class="form-grid"><label class="field full">Преподаватель<select disabled><option>${teacher.name}</option></select></label><label class="field full">Дата статуса<input type="date" value="2026-10-26" readonly></label><label class="field">С какого времени<input type="time" value="14:00" readonly></label><label class="field">До какого времени<input type="time" value="15:00" readonly></label><label class="field">Корпус<select disabled><option>Корпус 1</option></select></label><label class="field">Кабинет<input value="214" readonly></label><label class="field full">Комментарий<input value="Консультация по математике" readonly></label></div><div class="form-actions"><span class="small">Статус на выбранную дату</span><button type="button" class="btn btn-primary" data-demo-action="confirmation">Сохранить</button></div>${state.view === 'confirmation' ? '<div class="mock-confirmation" role="status" tabindex="-1">✓ Статус сохранён</div><p><a class="back-link" href="#teacher">Посмотреть карточку →</a></p>' : ''}</section></div>`;
  }
  function renderSubscribe() {
    const connected = state.view === 'connected';
    return `<div class="content-width form-page">${crumb('Подписка')}<a class="back-link" href="#teacher">← К карточке преподавателя</a><div class="form-page-head"><h1>Подписка на изменения</h1><p class="lead">Уведомления о консультациях, пересдачах и статусе преподавателя.</p></div><section class="form-panel mock-form">${teacherMini()}<label class="field">Электронная почта<input type="text" value="student@example.com" readonly></label><p class="group-label">О чём сообщать</p><div class="check-group"><label class="check-line"><input type="checkbox" checked disabled><span>Изменения консультаций</span></label><label class="check-line"><input type="checkbox" checked disabled><span>Изменения графика пересдач</span></label><label class="check-line"><input type="checkbox" checked disabled><span>Статус на день</span></label></div><div class="subscription-save">${connected ? '<p class="small" role="status" tabindex="-1">✓ Подписка подключена</p><button type="button" class="btn" data-demo-action="cancelled">Отменить подписку</button>' : '<button type="button" class="btn btn-primary" data-demo-action="connected">Подписаться</button>'}${state.view === 'cancelled' ? '<p class="mock-confirmation" role="status" tabindex="-1">Подписка отменена</p>' : ''}</div></section></div>`;
  }
  function render() {
    statePicker.innerHTML = options[state.route].map(([value,label])=>`<option value="${value}" ${state.view === value ? 'selected' : ''}>${label}</option>`).join('');
    content.innerHTML = ({search:renderSearch,teacher:renderTeacher,status:renderStatus,subscribe:renderSubscribe})[state.route]();
    shell.dataset.screen = state.route;
    document.querySelectorAll('[data-demo-route],[data-route]').forEach((a)=>a.setAttribute('aria-current',(a.dataset.demoRoute || a.dataset.route) === state.route ? 'page' : 'false'));
    document.title = `${{search:'Поиск',teacher:'Карточка',status:'Статус',subscribe:'Подписка'}[state.route]} · Кафедра Онлайн`;
  }
  function onHash() {
    const next = location.hash.slice(1);
    state.route = Object.hasOwn(options,next) ? next : 'search';
    state.view = 'normal';
    render();
    window.scrollTo({top:0,behavior:'instant'});
  }
  content.addEventListener('click', (event) => {
    const action = event.target.closest('[data-demo-action]');
    if (!action) return;
    state.view = action.dataset.demoAction;
    render();
    content.querySelector('[role="status"]')?.focus();
  });
  statePicker.addEventListener('change',(event)=>{state.view = event.target.value;render();});
  document.querySelectorAll('button[data-device]').forEach((button)=>button.addEventListener('click',()=>{
    shell.dataset.device = button.dataset.device;
    document.querySelectorAll('button[data-device]').forEach((b)=>b.setAttribute('aria-pressed',b === button ? 'true' : 'false'));
  }));
  const params = new URLSearchParams(location.search);
  if(params.has('presentation')) document.body.classList.add('presentation');
  window.addEventListener('hashchange',onHash);
  onHash();
  const initialView = params.get('state');
  if(options[state.route].some(([v])=>v === initialView)){state.view=initialView;render();}
})();

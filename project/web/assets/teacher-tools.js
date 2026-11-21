(() => {
  const card = document.querySelector("[data-teacher-id]");
  const favorites = document.querySelector("[data-favorites]");
  if (!card && !favorites) return;

  const storageKey = "kafedra-online.favorite-teachers.v1";
  const controls = card?.querySelector(".teacher-actions");
  const toggle = controls?.querySelector("[data-favorite-toggle]");
  const status = controls?.querySelector('[role="status"]');
  const teacherName = card?.querySelector("h1").textContent.trim();

  function savedTeachers() {
    try {
      const rows = JSON.parse(localStorage.getItem(storageKey) || "[]");
      return Array.isArray(rows) ? rows.filter(row =>
        row && /^\d+$/.test(row.id) && typeof row.name === "string") : [];
    } catch {
      return [];
    }
  }

  function render() {
    const rows = savedTeachers();
    if (card) {
      const saved = rows.some(row => row.id === card.dataset.teacherId);
      toggle.textContent = saved ? "В избранном" : "В избранное";
      toggle.setAttribute("aria-pressed", String(saved));
      controls.hidden = false;
    }
    if (favorites) {
      const list = favorites.querySelector("ul");
      list.replaceChildren();
      for (const row of rows) {
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = favorites.dataset.cardPattern.replace("ID", row.id);
        link.textContent = row.name;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.textContent = "Убрать";
        remove.setAttribute("aria-label", "Убрать из избранного: " + row.name);
        remove.addEventListener("click", () => {
          try {
            localStorage.setItem(storageKey, JSON.stringify(savedTeachers().filter(item => item.id !== row.id)));
            render();
            (favorites.querySelector("li a") || document.querySelector("#query")).focus();
          } catch {
            favorites.querySelector('[role="status"]').textContent = "Браузер запретил изменить избранное.";
          }
        });
        item.append(link, remove);
        list.append(item);
      }
      favorites.hidden = rows.length === 0;
    }
  }

  toggle?.addEventListener("click", () => {
    const id = card.dataset.teacherId;
    const rows = savedTeachers();
    const saved = rows.some(row => row.id === id);
    const updated = saved ? rows.filter(row => row.id !== id) : [...rows, {id, name: teacherName}];
    try {
      localStorage.setItem(storageKey, JSON.stringify(updated));
      render();
      status.textContent = saved ? "Удалено из избранного." : "Сохранено в этом браузере.";
    } catch {
      status.textContent = "Браузер запретил сохранить избранное.";
    }
  });

  controls?.querySelector("[data-share]").addEventListener("click", async () => {
    const manual = controls.querySelector("label");
    manual.hidden = true;
    status.textContent = "";
    const url = new URL(location.pathname, location.origin);
    const period = new URLSearchParams(location.search).get("period");
    if (period && Array.from(document.querySelector("#period").options).some(option => option.value === period)) {
      url.searchParams.set("period", period);
    }
    if (location.hash === "#retakes") url.hash = "retakes";
    if (navigator.share) {
      try {
        await navigator.share({title: teacherName + " · Кафедра Онлайн", url: url.href});
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }
    try {
      await navigator.clipboard.writeText(url.href);
      status.textContent = "Ссылка скопирована.";
    } catch {
      const input = manual.querySelector("input");
      input.value = url.href;
      manual.hidden = false;
      input.focus();
      input.select();
      status.textContent = "Скопируйте выделенную ссылку.";
    }
  });

  window.addEventListener("storage", event => {
    if (event.key === storageKey || event.key === null) render();
  });
  window.addEventListener("pageshow", render);
  render();
})();


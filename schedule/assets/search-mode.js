"use strict";

const searchField = document.querySelector("#query");
const searchModes = searchField.form.elements.by;
const initialQuery = searchField.value.trim();

function updateSearchHint() {
  searchField.placeholder = searchModes.value === "subject" ? "Название предмета" : "Фамилия преподавателя";
}

updateSearchHint();

for (const option of searchModes) {
  option.addEventListener("click", event => {
    updateSearchHint();
    if (searchField.value.trim() || initialQuery) {
      searchField.form.requestSubmit();
    } else if (event.detail > 0) {
      searchField.focus();
    }
  });
}

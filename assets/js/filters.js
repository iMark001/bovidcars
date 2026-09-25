/* Фильтры каталога: марка, двигатель, статус. Пустые секции марок скрываются. */
(function () {
  "use strict";

  var active = { brand: "all", engine: "all", status: "all" };
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var tiles = Array.prototype.slice.call(document.querySelectorAll(".brand-tile"));
  var emptyState = document.querySelector(".empty-state");

  function matches(card) {
    return Object.keys(active).every(function (key) {
      return active[key] === "all" || card.dataset[key] === active[key];
    });
  }

  function apply() {
    var visibleTotal = 0;
    cards.forEach(function (card) {
      var show = matches(card);
      card.hidden = !show;
      if (show) visibleTotal += 1;
    });
    tiles.forEach(function (tile) {
      tile.hidden = !tile.querySelector(".card:not([hidden])");
    });
    if (emptyState) emptyState.hidden = visibleTotal > 0;
  }

  document.addEventListener("click", function (event) {
    var chip = event.target.closest(".chip[data-filter]");
    if (!chip) return;
    var group = chip.dataset.filter;
    active[group] = chip.dataset.value;
    document.querySelectorAll('.chip[data-filter="' + group + '"]').forEach(function (el) {
      var on = el === chip;
      el.classList.toggle("is-active", on);
      el.setAttribute("aria-pressed", String(on));
    });
    apply();
  });

  apply();
})();

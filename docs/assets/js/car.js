/* Страница авто: листание галереи и кнопка «Поделиться». */
(function () {
  "use strict";

  var COPIED_MESSAGE = "Ссылка скопирована";
  var COPY_FAILED_MESSAGE = "Не получилось скопировать — выделите адрес в строке браузера";
  var page = document.querySelector(".car");
  if (!page) return;

  /* ---------- галерея ---------- */
  var track = document.querySelector(".gallery__track");
  document.addEventListener("click", function (event) {
    var btn = event.target.closest("[data-gallery]");
    if (!btn || !track) return;
    var item = track.querySelector(".gallery__item");
    var step = item ? item.getBoundingClientRect().width + 16 : track.clientWidth;
    track.scrollBy({ left: btn.dataset.gallery === "next" ? step : -step, behavior: "smooth" });
  });

  /* ---------- поделиться ---------- */
  var title = page.dataset.shareTitle;
  var url = page.dataset.shareUrl;
  var menu = document.querySelector(".share-menu");
  var done = document.querySelector(".share-menu__done");
  var text = encodeURIComponent(title + " — " + url);

  if (menu) {
    menu.querySelector('[data-share-target="whatsapp"]').href = "https://wa.me/?text=" + text;
    menu.querySelector('[data-share-target="telegram"]').href =
      "https://t.me/share/url?url=" + encodeURIComponent(url) + "&text=" + encodeURIComponent(title);
  }

  function copyLink() {
    var show = function (message) { if (done) done.textContent = message; };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(function () { show(COPIED_MESSAGE); }, function () { show(COPY_FAILED_MESSAGE); });
    } else {
      show(COPY_FAILED_MESSAGE);
    }
  }

  document.addEventListener("click", function (event) {
    if (event.target.closest('[data-share-target="copy"]')) {
      copyLink();
      return;
    }
    if (!event.target.closest("[data-share]")) return;
    if (navigator.share) {
      navigator.share({ title: title, url: url }).catch(function () { /* пользователь закрыл окно */ });
      return;
    }
    if (menu) menu.hidden = !menu.hidden;
  });
})();

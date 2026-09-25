/* Цены: всегда сначала евро, затем доллары. Исходная валюта точная, вторая пересчитывается
   по свежему курсу ЕЦБ (frankfurter.dev); при сбое остаётся курс, с которым собран сайт. */
(function () {
  "use strict";

  var TIMEOUT_MS = 6000;
  var SIGNS = { EUR: "€", USD: "$" };
  var body = document.body;
  var rate = parseFloat(body.dataset.rate) || 1;

  function convert(amount, from, to) {
    if (from === to) return amount;
    return Math.round(from === "EUR" ? amount * rate : amount / rate);
  }

  function format(amount, currency) {
    return new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 0 }).format(amount) + " " + SIGNS[currency];
  }

  function render() {
    document.querySelectorAll(".price-value").forEach(function (el) {
      var amount = parseFloat(el.dataset.amount);
      var base = el.dataset.currency;
      el.querySelector(".price-value__main").textContent = format(convert(amount, base, "EUR"), "EUR");
      el.querySelector(".price-value__alt").textContent = format(convert(amount, base, "USD"), "USD");
    });
  }

  function formatDate(iso) {
    var parts = iso.split("-");
    var date = new Date(Date.UTC(+parts[0], +parts[1] - 1, +parts[2]));
    return new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" })
      .format(date).replace(/\s?г\.$/, "");
  }

  function applyRate(newRate, isoDate) {
    rate = newRate;
    document.querySelectorAll("[data-rate-text]").forEach(function (el) { el.textContent = newRate.toFixed(4); });
    document.querySelectorAll("[data-rate-date-text]").forEach(function (el) { el.textContent = formatDate(isoDate); });
    render();
  }

  function fetchRate() {
    var api = body.dataset.rateApi;
    if (!api || !window.fetch) return;
    var controller = window.AbortController ? new AbortController() : null;
    var timer = setTimeout(function () { if (controller) controller.abort(); }, TIMEOUT_MS);
    fetch(api, controller ? { signal: controller.signal } : {})
      .then(function (resp) {
        if (!resp.ok) throw new Error("HTTP " + resp.status);
        return resp.json();
      })
      .then(function (data) {
        var fresh = data && data.rates && parseFloat(data.rates.USD);
        if (fresh > 0 && data.date) applyRate(fresh, data.date);
      })
      .catch(function () { /* остаётся курс из сборки — он уже показан */ })
      .then(function () { clearTimeout(timer); });
  }

  fetchRate();
})();

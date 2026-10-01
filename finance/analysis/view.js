/** 分析列表。新文章在 entries.js 数组最前。 */
(function (global) {
  "use strict";

  var DATE_LINE = /^(\d{1,2}\/\d{1,2}(?:[–\-]\d{1,2}(?:\/\d{1,2})?)?)\s*(.*)$/;

  function pad2(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function parseMd(md) {
    var parts = String(md).split("/");
    return { m: Number(parts[0]), d: Number(parts[1]) };
  }

  function eventSortKey(dateLabel, year) {
    var first = String(dateLabel).split(/[–\-]/)[0].trim();
    var md = parseMd(first);
    return year * 10000 + md.m * 100 + md.d;
  }

  function renderTimeline(a) {
    var year = Number(String(a.date || "").slice(0, 4)) || new Date().getFullYear();
    var now = new Date();
    var todayKey = now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
    var todayLabel = pad2(now.getMonth() + 1) + "/" + pad2(now.getDate());
    var events = [];
    var hold = "";

    (a.paragraphs || []).forEach(function (p) {
      if (/^一直留/.test(p)) {
        hold = p;
        return;
      }
      var m = DATE_LINE.exec(p);
      if (!m) return;
      events.push({
        dateLabel: m[1],
        text: m[2],
        key: eventSortKey(m[1], year)
      });
    });

    var nowInserted = false;
    var rows = [];

    function pushNow() {
      rows.push(
        '<li class="tl-item tl-now">' +
          '<span class="tl-rail" aria-hidden="true"><span class="tl-star">★</span></span>' +
          '<div class="tl-body">' +
          '<div class="tl-date">' +
          todayLabel +
          "</div>" +
          '<div class="tl-text">现在</div>' +
          "</div>" +
          "</li>"
      );
      nowInserted = true;
    }

    events.forEach(function (ev) {
      if (!nowInserted && todayKey < ev.key) pushNow();
      rows.push(
        '<li class="tl-item">' +
          '<span class="tl-rail" aria-hidden="true"><span class="tl-dot"></span></span>' +
          '<div class="tl-body">' +
          '<div class="tl-date">' +
          ev.dateLabel +
          "</div>" +
          '<div class="tl-text">' +
          ev.text +
          "</div>" +
          "</div>" +
          "</li>"
      );
    });

    if (!nowInserted) pushNow();

    return (
      '<ol class="tl">' +
      rows.join("") +
      "</ol>" +
      (hold ? '<p class="tl-hold">' + hold + "</p>" : "")
    );
  }

  function init() {
    var list = document.getElementById("analysis-list");
    var items = global.ANALYSES || [];
    if (!list) return;
    if (!items.length) {
      list.innerHTML = '<p class="snap-note">还没有分析。在 analysis/entries.js 最前面加一篇。</p>';
      return;
    }
    list.innerHTML = items
      .map(function (a) {
        var body =
          a.id === "2026-10-01-timeline"
            ? renderTimeline(a)
            : (a.paragraphs || [])
                .map(function (p) {
                  return "<p>" + p + "</p>";
                })
                .join("");
        return (
          '<article class="analysis-entry" id="' +
          a.id +
          '">' +
          '<div class="analysis-date">' +
          a.date +
          "</div>" +
          "<h2>" +
          a.title +
          "</h2>" +
          body +
          "</article>"
        );
      })
      .join("");
  }

  global.AnalysisPage = { init: init };
})(window);

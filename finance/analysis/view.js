/** 待办。数据在 entries.js 的 TODOS。 */
(function (global) {
  "use strict";

  function pad2(n) {
    return n < 10 ? "0" + n : String(n);
  }

  function parseMd(md) {
    var parts = String(md).split("/");
    return { m: Number(parts[0]), d: Number(parts[1]) };
  }

  function eventSortKey(dateLabel, year) {
    var label = String(dateLabel).trim();
    var full = label.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
    if (full) return Number(full[1]) * 10000 + Number(full[2]) * 100 + Number(full[3]);
    var first = label.split(/[–\-]/)[0].trim();
    var md = parseMd(first);
    return year * 10000 + md.m * 100 + md.d;
  }

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inline(s) {
    return esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function renderTimeline(events, year) {
    if (!events || !events.length) return "";
    var now = new Date();
    var todayKey = now.getFullYear() * 10000 + (now.getMonth() + 1) * 100 + now.getDate();
    var todayLabel = pad2(now.getMonth() + 1) + "/" + pad2(now.getDate());
    var nowInserted = false;
    var rows = [];

    function pushNow() {
      rows.push(
        '<li class="tl-item tl-now">' +
          '<span class="tl-rail" aria-hidden="true"><span class="tl-star">★</span></span>' +
          '<div class="tl-body"><div class="tl-date">' +
          todayLabel +
          '</div><div class="tl-text">现在</div></div></li>'
      );
      nowInserted = true;
    }

    events.forEach(function (ev) {
      var key = eventSortKey(ev.date, year);
      if (!nowInserted && todayKey < key) pushNow();
      rows.push(
        '<li class="tl-item">' +
          '<span class="tl-rail" aria-hidden="true"><span class="tl-dot"></span></span>' +
          '<div class="tl-body"><div class="tl-date">' +
          esc(ev.date) +
          '</div><div class="tl-text">' +
          inline(ev.text) +
          "</div></div></li>"
      );
    });
    if (!nowInserted) pushNow();
    return '<ol class="tl">' + rows.join("") + "</ol>";
  }

  function renderItem(it) {
    var st = it.status || "todo";
    var mark = st === "done" ? "✓" : st === "wait" ? "○" : "";
    return (
      '<li class="todo-item is-' +
      st +
      '">' +
      '<span class="todo-check" aria-hidden="true">' +
      mark +
      "</span>" +
      '<div class="todo-body">' +
      (it.date ? '<div class="todo-date">' + esc(it.date) + "</div>" : "") +
      '<div class="todo-text">' +
      inline(it.text) +
      "</div></div></li>"
    );
  }

  function renderGroup(g) {
    var open = g.collapsed ? "" : " open";
    return (
      '<details class="todo-group"' +
      open +
      "><summary>" +
      esc(g.title) +
      "</summary><ul class=\"todo-list\">" +
      (g.items || [])
        .map(renderItem)
        .join("") +
      "</ul></details>"
    );
  }

  function init() {
    var list = document.getElementById("analysis-list");
    var data = global.TODOS;
    if (!list) return;
    if (!data || !((data.groups && data.groups.length) || data.next || (data.timeline && data.timeline.length))) {
      list.innerHTML = '<p class="snap-note">还没有待办。</p>';
      return;
    }
    var year = Number(String(data.year || "2026").slice(0, 4)) || 2026;
    var html = "";
    if (data.next) {
      html += '<p class="an-callout">' + inline(data.next) + "</p>";
    }
    if (data.order) {
      html +=
        '<p class="todo-order">卖出顺序：' + inline(data.order) + "</p>";
    }
    (data.groups || []).forEach(function (g) {
      html += renderGroup(g);
    });
    if (data.never && data.never.length) {
      html +=
        '<section class="todo-never"><h3>不要做</h3><ul class="an-list">' +
        data.never
          .map(function (t) {
            return "<li>" + inline(t) + "</li>";
          })
          .join("") +
        "</ul></section>";
    }
    if (data.timeline && data.timeline.length) {
      html +=
        '<section class="todo-cal"><h3>日历</h3>' +
        renderTimeline(data.timeline, year) +
        "</section>";
    }
    list.innerHTML = '<div class="analysis-entry is-lead todo-page">' + html + "</div>";
  }

  global.AnalysisPage = { init: init };
})(window);

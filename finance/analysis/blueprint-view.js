/** 人生公司蓝图。 */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function metrics(list) {
    return (
      '<div class="bp-metrics">' +
      list
        .map(function (m) {
          return (
            '<div class="bp-metric"><b>' +
            esc(m.value) +
            "</b><i>" +
            esc(m.label) +
            "</i><small>" +
            esc(m.note) +
            "</small></div>"
          );
        })
        .join("") +
      "</div>"
    );
  }

  function trio(items) {
    return (
      '<div class="bp-trio">' +
      items
        .map(function (it) {
          return "<article><h3>" + esc(it.h) + "</h3><p>" + esc(it.p) + "</p></article>";
        })
        .join("") +
      "</div>"
    );
  }

  function cell(c) {
    return (
      '<article class="bp-cell"><span class="bp-chip">' +
      esc(c.chip) +
      "</span><h3>" +
      esc(c.name) +
      "</h3><p>" +
      esc(c.text) +
      "</p></article>"
    );
  }

  function org(o) {
    return (
      '<div class="bp-org">' +
      '<article class="bp-org-head"><span class="bp-chip">' +
      esc(o.head.chip) +
      "</span><h3>" +
      esc(o.head.name) +
      "</h3><p>" +
      esc(o.head.text) +
      "</p></article>" +
      '<div class="bp-row">' +
      o.row.map(cell).join("") +
      "</div>" +
      '<div class="bp-row two">' +
      o.base.map(cell).join("") +
      "</div></div>" +
      '<div class="bp-order">' +
      o.order
        .map(function (name, i) {
          return (i ? '<i>→</i>' : "") + "<span>" + esc(name) + "</span>";
        })
        .join("") +
      "</div>"
    );
  }

  function rail(phases) {
    return (
      '<ol class="bp-rail">' +
      phases
        .map(function (p) {
          return (
            '<li class="' +
            (p.now ? "is-now" : "") +
            '"><div class="bp-when">' +
            esc(p.when) +
            "</div><div><h3>" +
            esc(p.name) +
            "</h3><p>" +
            esc(p.text) +
            "</p></div></li>"
          );
        })
        .join("") +
      "</ol>"
    );
  }

  function board(b) {
    function col(title, items) {
      return (
        "<section><h3>" +
        esc(title) +
        "</h3><ul>" +
        items
          .map(function (t) {
            return "<li>" + esc(t) + "</li>";
          })
          .join("") +
        "</ul></section>"
      );
    }
    return '<div class="bp-board">' + col("默认否决", b.no) + col("可以做", b.yes) + "</div>";
  }

  function questions(list) {
    return (
      '<div class="bp-questions">' +
      list
        .map(function (q) {
          return "<article><b>" + esc(q.n) + "</b><p>" + esc(q.q) + "</p></article>";
        })
        .join("") +
      "</div>"
    );
  }

  function plate(no, title, inner) {
    return (
      '<section class="bp-plate"><header class="bp-plate-h"><span class="bp-no">' +
      esc(no) +
      "</span><h2>" +
      esc(title) +
      "</h2></header>" +
      inner +
      "</section>"
    );
  }

  function init() {
    var root = document.getElementById("blueprint");
    var d = global.BLUEPRINT;
    if (!root || !d) return;

    var road =
      '<p class="bp-lead">' +
      esc(d.road.lead) +
      "</p>" +
      rail(d.road.phases) +
      '<div class="bp-lock"><h3>' +
      esc(d.road.lockedTitle) +
      "</h3><ul>" +
      d.road.locked
        .map(function (t) {
          return "<li>" + esc(t) + "</li>";
        })
        .join("") +
      '</ul><p class="bp-rule">' +
      esc(d.road.unlock) +
      "</p></div>";

    root.innerHTML =
      '<article class="bp-sheet">' +
      '<p class="bp-kicker"><span>' +
      esc(d.kicker) +
      "</span><span>" +
      esc(d.date) +
      "</span></p>" +
      "<h1 class=\"bp-title\">" +
      esc(d.title) +
      "</h1>" +
      '<p class="bp-thesis">' +
      esc(d.thesis) +
      "</p>" +
      metrics(d.metrics) +
      plate(
        "01",
        "定位",
        '<p class="bp-lead">' + esc(d.place.lead) + "</p>" + trio(d.place.items)
      ) +
      plate("02", "结构", '<p class="bp-lead">' + esc(d.org.lead) + "</p>" + org(d.org)) +
      plate("03", "路线", road) +
      plate("04", "纪律", board(d.board) + questions(d.questions)) +
      '<footer class="bp-close"><p>' +
      esc(d.close) +
      '</p><a href="index.html">卖单在待办</a></footer></article>';
  }

  global.BlueprintPage = { init: init };
})(window);

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

  function classify(line) {
    var t = String(line || "").trim();
    if (!t) return { kind: "empty" };
    if (/^##\s+/.test(t)) return { kind: "h", text: t.replace(/^##\s+/, "") };
    if (/^>\s+/.test(t)) return { kind: "callout", text: t.replace(/^>\s+/, "") };
    if (/^[-•]\s+/.test(t)) return { kind: "li", text: t.replace(/^[-•]\s+/, "") };
    if (/^\d+\.\s+/.test(t)) return { kind: "oli", text: t.replace(/^\d+\.\s+/, "") };
    if (t.charAt(0) === "|" && t.indexOf("|", 1) !== -1) {
      var cells = t.split("|").slice(1);
      if (cells.length && cells[cells.length - 1].trim() === "") cells.pop();
      return {
        kind: "tr",
        cells: cells.map(function (c) {
          return c.trim();
        })
      };
    }
    return { kind: "p", text: t };
  }

  function renderTable(rows) {
    if (!rows.length) return "";
    var head = rows[0];
    var body = rows.slice(1);
    var thead =
      "<thead><tr>" +
      head.cells
        .map(function (c) {
          return "<th>" + inline(c) + "</th>";
        })
        .join("") +
      "</tr></thead>";
    var tbody =
      "<tbody>" +
      body
        .map(function (r) {
          return (
            "<tr>" +
            r.cells
              .map(function (c) {
                return "<td>" + inline(c) + "</td>";
              })
              .join("") +
            "</tr>"
          );
        })
        .join("") +
      "</tbody>";
    return '<div class="an-table-wrap"><table class="an-table">' + thead + tbody + "</table></div>";
  }

  function renderList(items, tag) {
    return (
      "<" +
      tag +
      ' class="an-list">' +
      items
        .map(function (it) {
          return "<li>" + inline(it.text) + "</li>";
        })
        .join("") +
      "</" +
      tag +
      ">"
    );
  }

  function renderBlocks(lines) {
    var html = [];
    var i = 0;
    while (i < lines.length) {
      var cur = classify(lines[i]);
      if (cur.kind === "empty") {
        i += 1;
        continue;
      }
      if (cur.kind === "h") {
        html.push("<h3>" + inline(cur.text) + "</h3>");
        i += 1;
        continue;
      }
      if (cur.kind === "callout") {
        html.push('<p class="an-callout">' + inline(cur.text) + "</p>");
        i += 1;
        continue;
      }
      if (cur.kind === "p") {
        html.push("<p>" + inline(cur.text) + "</p>");
        i += 1;
        continue;
      }
      if (cur.kind === "li" || cur.kind === "oli") {
        var kind = cur.kind;
        var group = [];
        while (i < lines.length && classify(lines[i]).kind === kind) {
          group.push(classify(lines[i]));
          i += 1;
        }
        html.push(renderList(group, kind === "oli" ? "ol" : "ul"));
        continue;
      }
      if (cur.kind === "tr") {
        var rows = [];
        while (i < lines.length && classify(lines[i]).kind === "tr") {
          rows.push(classify(lines[i]));
          i += 1;
        }
        html.push(renderTable(rows));
        continue;
      }
      i += 1;
    }
    return html.join("");
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
          inline(ev.text) +
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
      (hold ? '<p class="tl-hold">' + inline(hold) + "</p>" : "")
    );
  }

  function renderToc(items) {
    return (
      '<details class="analysis-toc-wrap">' +
      "<summary>共 " +
      items.length +
      " 篇，点开跳转</summary>" +
      '<nav class="analysis-toc" aria-label="篇目">' +
      items
        .map(function (a) {
          return (
            '<a class="analysis-toc-link" href="#' +
            esc(a.id) +
            '"><span class="analysis-toc-date">' +
            esc(a.date) +
            "</span>" +
            esc(a.title) +
            "</a>"
          );
        })
        .join("") +
      "</nav></details>"
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
    list.innerHTML =
      renderToc(items) +
      items
        .map(function (a, idx) {
          var body =
            a.id === "2026-10-01-timeline"
              ? renderTimeline(a)
              : renderBlocks(a.paragraphs || []);
          return (
            '<article class="analysis-entry' +
            (idx === 0 ? " is-lead" : "") +
            '" id="' +
            esc(a.id) +
            '">' +
            '<div class="analysis-date">' +
            esc(a.date) +
            "</div>" +
            "<h2>" +
            esc(a.title) +
            "</h2>" +
            body +
            "</article>"
          );
        })
        .join("");
  }

  global.AnalysisPage = { init: init };
})(window);

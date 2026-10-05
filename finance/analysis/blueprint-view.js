/** 人生公司蓝图。数据在 blueprint-data.js。 */
(function (global) {
  "use strict";

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

  function paras(list) {
    return (list || [])
      .map(function (p) {
        return "<p>" + inline(p) + "</p>";
      })
      .join("");
  }

  function table(t) {
    if (!t || !t.rows) return "";
    var cap = t.caption ? '<p class="bp-caption">' + inline(t.caption) + "</p>" : "";
    return (
      cap +
      '<div class="an-table-wrap"><table class="an-table"><thead><tr>' +
      (t.head || [])
        .map(function (h) {
          return "<th>" + inline(h) + "</th>";
        })
        .join("") +
      "</tr></thead><tbody>" +
      t.rows
        .map(function (r) {
          return (
            "<tr>" +
            r
              .map(function (c) {
                return "<td>" + inline(c) + "</td>";
              })
              .join("") +
            "</tr>"
          );
        })
        .join("") +
      "</tbody></table></div>"
    );
  }

  function ul(items) {
    if (!items || !items.length) return "";
    return (
      '<ul class="an-list">' +
      items
        .map(function (t) {
          return "<li>" + inline(t) + "</li>";
        })
        .join("") +
      "</ul>"
    );
  }

  function dept(d) {
    return (
      '<article class="bp-dept">' +
      "<h3>" +
      esc(d.name) +
      "</h3>" +
      '<span class="bp-label">职责</span><p>' +
      inline(d.duty) +
      "</p>" +
      '<span class="bp-label">当前</span><p>' +
      inline(d.now) +
      "</p>" +
      '<span class="bp-label">禁止</span>' +
      ul(d.bans) +
      '<span class="bp-label">近端</span><p>' +
      inline(d.kpi) +
      "</p></article>"
    );
  }

  function phase(p) {
    return (
      '<article class="bp-phase' +
      (p.now ? " is-now" : "") +
      '"><h3>' +
      esc(p.name) +
      '</h3><p class="bp-when">' +
      esc(p.when) +
      "</p>" +
      ul(p.lines) +
      "</article>"
    );
  }

  function subsection(s) {
    var html = "<h3>" + esc(s.title) + "</h3>";
    html += paras(s.paragraphs);
    html += table(s.table);
    if (s.list && s.list.length) {
      if (s.listTitle) html += '<p class="bp-caption">' + inline(s.listTitle) + "</p>";
      html += ul(s.list);
    }
    html += paras(s.paragraphsAfter);
    if (s.note) html += '<p class="snap-note">' + inline(s.note) + "</p>";
    return html;
  }

  function section(s) {
    var html = '<section class="bp-section"><h2>' + esc(s.title) + "</h2>";
    html += paras(s.paragraphs);
    html += table(s.table);
    (s.tables || []).forEach(function (t) {
      html += table(t);
    });
    html += paras(s.paragraphsAfter);
    if (s.depts && s.depts.length) {
      html += '<div class="bp-dept-grid">' + s.depts.map(dept).join("") + "</div>";
    }
    if (s.phases && s.phases.length) {
      html += '<div class="bp-phases">' + s.phases.map(phase).join("") + "</div>";
    }
    (s.subsections || []).forEach(function (sub) {
      html += subsection(sub);
    });
    (s.groups || []).forEach(function (g) {
      html += '<p class="bp-caption">' + inline(g.title) + "</p>" + ul(g.items);
    });
    if (s.ol && s.ol.length) {
      if (s.olTitle) html += '<p class="bp-caption">' + inline(s.olTitle) + "</p>";
      html +=
        '<ol class="an-list">' +
        s.ol
          .map(function (t) {
            return "<li>" + inline(t) + "</li>";
          })
          .join("") +
        "</ol>";
    }
    html += "</section>";
    return html;
  }

  function init() {
    var root = document.getElementById("blueprint");
    var data = global.BLUEPRINT;
    if (!root || !data) return;
    var html =
      '<p class="bp-meta">' +
      esc(data.date) +
      " · " +
      esc(data.status) +
      "</p>" +
      '<p class="an-callout">' +
      inline(data.lead) +
      "</p>" +
      '<p class="an-callout">' +
      inline(data.diagnosis) +
      "</p>";
    (data.sections || []).forEach(function (s) {
      html += section(s);
    });
    html += '<p class="an-callout">' + inline(data.close) + "</p>";
    root.innerHTML = '<div class="analysis-entry is-lead bp-page">' + html + "</div>";
  }

  global.BlueprintPage = { init: init };
})(window);

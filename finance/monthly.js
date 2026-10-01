(function (global) {
  "use strict";
  function money(n) {
    return Math.abs(n).toLocaleString("zh-CN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }
  function cells(items, tag) {
    return "<tr>" + items.map(function (c) {
      return "<" + tag + (c.cls ? ' class="' + c.cls + '"' : "") + ">" + c.text + "</" + tag + ">";
    }).join("") + "</tr>";
  }
  function metric(label, value) {
    return '<div class="snap-metric"><div class="snap-metric-label">' + label +
      '</div><div class="snap-metric-value">' + value + "</div></div>";
  }
  function init() {
    var rows = global.MONTHLY || [];
    var latest = rows[0];
    if (!latest) return;
    var metrics = document.getElementById("month-metrics");
    if (metrics) {
      metrics.innerHTML =
        metric("工资到手", money(latest.incomeNet)) +
        metric("给家人", money(latest.toFamily)) +
        metric("自己留存", money(latest.selfSave)) +
        metric("自己生活费", latest.living);
    }
    var table = document.getElementById("month-table");
    if (table) {
      var head = cells(["月份", "到手", "给家人", "自己留存", "生活费"].map(function (t) { return { text: t }; }), "th");
      var body = rows.map(function (m) {
        return cells([
          { text: m.month },
          { text: money(m.incomeNet), cls: "num" },
          { text: money(m.toFamily), cls: "num" },
          { text: money(m.selfSave), cls: "num" },
          { text: m.living, cls: "num" }
        ], "td");
      }).join("");
      table.innerHTML = "<thead>" + head + "</thead><tbody>" + body + "</tbody>";
    }
    var note = document.getElementById("month-note");
    if (note) note.textContent = latest.note || "";
  }
  global.MonthlyPage = { init: init };
})(window);

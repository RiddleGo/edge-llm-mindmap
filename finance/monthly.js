/** 每月财务页：工资分配 + 负债。不渲染证券。 */
(function (global) {
  "use strict";

  function money(n) {
    var sign = n < 0 ? "-" : "";
    return sign + Math.abs(n).toLocaleString("zh-CN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  function cells(items, tag) {
    return (
      "<tr>" +
      items
        .map(function (c) {
          return "<" + tag + (c.cls ? ' class="' + c.cls + '"' : "") + ">" + c.text + "</" + tag + ">";
        })
        .join("") +
      "</tr>"
    );
  }

  function metric(label, value, note) {
    return (
      '<div class="snap-metric"><div class="snap-metric-label">' +
      label +
      '</div><div class="snap-metric-value">' +
      value +
      "</div>" +
      (note ? '<div class="snap-metric-note">' + note + "</div>" : "") +
      "</div>"
    );
  }

  function init() {
    var rows = global.MONTHLY || [];
    var metrics = document.getElementById("month-metrics");
    var table = document.getElementById("month-table");
    var detail = document.getElementById("month-detail");
    if (!rows.length) return;

    var latest = rows[0];
    if (metrics) {
      metrics.innerHTML =
        metric("工资到手", money(latest.incomeNet), "每月") +
        metric("给家人", money(latest.toFamily), "从到手里划出") +
        metric("自己留存", money(latest.selfSave), "从到手里划出") +
        metric("自己生活费", "加班费", latest.overtimeNote || "") +
        metric("负债本金", money(latest.debt), latest.month);
    }

    if (table) {
      var head = cells(
        ["月份", "到手", "给家人", "自己留存", "生活费", "负债本金"].map(function (t) {
          return { text: t };
        }),
        "th"
      );
      var body = rows
        .map(function (m) {
          return cells(
            [
              { text: m.month },
              { text: money(m.incomeNet), cls: "num" },
              { text: money(m.toFamily), cls: "num" },
              { text: money(m.selfSave), cls: "num" },
              { text: m.livingFromOvertime ? "加班费" : "—", cls: "num" },
              { text: money(m.debt), cls: "num" }
            ],
            "td"
          );
        })
        .join("");
      table.innerHTML = "<thead>" + head + "</thead><tbody>" + body + "</tbody>";
    }

    if (detail) {
      var notes = rows
        .map(function (m) {
          return "<p class=\"snap-note\"><strong>" + m.month + "</strong>　" + m.note + "</p>";
        })
        .join("");
      var debtRows = (latest.debts || [])
        .map(function (d) {
          return cells([{ text: d.item }, { text: money(d.principal), cls: "num" }, { text: d.term }], "td");
        })
        .join("");
      var sum = (latest.debts || []).reduce(function (s, d) {
        return s + d.principal;
      }, 0);
      debtRows += cells([{ text: "合计" }, { text: money(sum), cls: "num" }, { text: latest.month }], "td");
      detail.innerHTML =
        notes +
        "<h3 class=\"snap-sub\">" +
        latest.month +
        " 负债明细</h3>" +
        '<div class="snap-table-wrap"><table class="snap-table"><thead>' +
        cells([{ text: "项目" }, { text: "本金" }, { text: "期限" }], "th") +
        "</thead><tbody>" +
        debtRows +
        "</tbody></table></div>";
    }
  }

  global.MonthlyPage = { init: init };
})(window);

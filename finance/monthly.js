/** 每月财务页 */
(function (global) {
  "use strict";

  function money(n) {
    var sign = n < 0 ? "-" : "";
    return sign + Math.abs(n).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function blank(n) {
    return n == null ? "未记" : money(n);
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

  function init() {
    var rows = global.MONTHLY || [];
    var box = document.getElementById("month-table");
    var detail = document.getElementById("month-detail");
    if (!box) return;

    var head = cells(
      ["月份", "证券账户", "基金", "负债", "净资产", "工资收入", "生活开支", "还款"].map(function (t) {
        return { text: t };
      }),
      "th"
    );
    var body = rows
      .map(function (m) {
        var net = m.securities + m.funds - m.debt;
        return cells(
          [
            { text: m.month },
            { text: money(m.securities), cls: "num" },
            { text: money(m.funds), cls: "num" },
            { text: money(m.debt), cls: "num" },
            { text: money(net), cls: "num" },
            { text: blank(m.income), cls: "num" },
            { text: blank(m.living), cls: "num" },
            { text: blank(m.repayment), cls: "num" }
          ],
          "td"
        );
      })
      .join("");
    box.innerHTML = "<thead>" + head + "</thead><tbody>" + body + "</tbody>";

    var notes = rows
      .map(function (m) {
        return "<p class=\"snap-note\"><strong>" + m.month + "</strong>　" + m.note + "</p>";
      })
      .join("");

    var latest = rows[0];
    var debtRows = "";
    if (latest && latest.debts) {
      debtRows = latest.debts
        .map(function (d) {
          return cells([{ text: d.item }, { text: money(d.principal), cls: "num" }, { text: d.term }], "td");
        })
        .join("");
      var sum = latest.debts.reduce(function (s, d) {
        return s + d.principal;
      }, 0);
      debtRows += cells([{ text: "合计" }, { text: money(sum), cls: "num" }, { text: latest.month }], "td");
    }

    if (detail) {
      detail.innerHTML =
        notes +
        "<h3 class=\"snap-sub\">" +
        (latest ? latest.month : "") +
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

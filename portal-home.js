/** 持仓页 */
(function (global) {
  "use strict";

  function money(n) {
    var sign = n < 0 ? "-" : "";
    return sign + Math.abs(n).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function pct(n) {
    return (n > 0 ? "+" : "") + n.toFixed(1) + "%";
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

  function metric(label, value) {
    return (
      '<div class="snap-metric"><div class="snap-metric-label">' +
      label +
      '</div><div class="snap-metric-value">' +
      value +
      "</div></div>"
    );
  }

  function init() {
    var data = global.SITE_SNAPSHOT;
    var box = document.getElementById("snap-holdings");
    if (!data || !box) return;
    var stamp = document.getElementById("snap-asof");
    if (stamp) stamp.textContent = "数据日期 " + data.asOf;

    var head = cells(
      ["账户", "名称", "持仓 / 可用", "成本价 / 现价", "市值", "持仓盈亏", "占证券"].map(function (t) {
        return { text: t };
      }),
      "th"
    );
    var body = data.holdings
      .map(function (h) {
        return cells(
          [
            { text: h.account },
            { text: h.name },
            { text: h.shares },
            { text: h.price },
            { text: money(h.marketValue), cls: "num" },
            { text: money(h.pnl) + "（" + pct(h.pnlPct) + "）", cls: "num" },
            { text: h.weight.toFixed(1) + "%", cls: "num" }
          ],
          "td"
        );
      })
      .join("");

    box.innerHTML =
      '<div class="snap-metrics">' +
      metric("证券合计", money(data.securitiesTotal)) +
      metric("现金", money(data.cash)) +
      metric("仓位", data.positionPct.toFixed(1) + "%") +
      metric("基金", money(data.funds)) +
      metric("当前持仓盈亏", money(data.unrealizedPnl)) +
      metric("历史全部盈亏", money(data.lifetimePnl)) +
      "</div>" +
      '<p class="snap-note">历史收益率：华宝 ' +
      data.lifetimeReturn.hb.toFixed(2) +
      "%，国投 " +
      data.lifetimeReturn.gt.toFixed(2) +
      "%。智谱价格为港元，市值已是人民币。</p>" +
      '<div class="snap-table-wrap"><table class="snap-table"><thead>' +
      head +
      "</thead><tbody>" +
      body +
      "</tbody></table></div>";
  }

  global.PortalHome = { init: init };
})(window);

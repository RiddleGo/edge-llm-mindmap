/** 分析列表。新文章在 entries.js 数组最前。 */
(function (global) {
  "use strict";

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
        var body = (a.paragraphs || [])
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

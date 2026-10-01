(function (global) {
  "use strict";

  function initSidebar() {
    var btn = document.querySelector(".kb-hamburger");
    var sidebar = document.getElementById("kb-sidebar");
    if (btn && sidebar) {
      btn.addEventListener("click", function () {
        sidebar.classList.toggle("open");
      });
    }
  }

  function prefixHref(href, base) {
    if (/^https?:\/\//.test(href) || href.indexOf("/") === 0) return href;
    if (href.indexOf("../") === 0 || href.indexOf("./") === 0) return href;
    return (base || "") + href;
  }

  function renderPortalSidebar(activeId) {
    var nav = global.SITE_NAV;
    if (!nav) return;
    var sidebar = document.getElementById("kb-sidebar");
    if (!sidebar) return;

    var header = sidebar.querySelector(".kb-sidebar-header");
    if (header) {
      header.innerHTML =
        '<a href="index.html" class="kb-logo">' +
        '<img src="' + nav.brand.logo + '" class="kb-logo-icon" alt="">' +
        "<span>" + nav.brand.title + " · " + nav.brand.subtitle + "</span></a>";
    }

    var navEl = sidebar.querySelector(".kb-sidebar-nav");
    if (!navEl) return;
    var html = "";
    nav.groups.forEach(function (group) {
      html += '<div class="kb-nav-group"><div class="kb-nav-group-title">' + group.title + "</div>";
      group.links.forEach(function (link) {
        var cls = link.id === activeId ? " kb-nav-link active" : " kb-nav-link";
        var lock = link.lock ? ' <span class="kb-nav-badge">🔒</span>' : "";
        html += '<a href="' + link.href + '" class="' + cls.trim() + '">' + link.label + lock + "</a>";
      });
      html += "</div>";
    });
    navEl.innerHTML = html;
  }

  global.KBShell = {
    initSidebar: initSidebar,
    renderPortalSidebar: renderPortalSidebar,
    prefixHref: prefixHref,
  };
})(window);

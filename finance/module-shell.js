(function (global) {
  "use strict";

  function resolveBase() {
    var depth = (location.pathname.match(/\//g) || []).length;
    var root = location.pathname.includes("/lcai-portfolio/") ? "/lcai-portfolio/" : "/";
    if (document.querySelector('script[src*="module-shell.js"]')) {
      var src = document.querySelector('script[src*="module-shell.js"]').getAttribute("src") || "";
      if (src.indexOf("../") === 0) return "../";
      if (src.indexOf("../../") === 0) return "../../";
    }
    return depth > 2 ? "../" : "";
  }

  function prefixHref(href, base) {
    if (/^https?:\/\//.test(href) || href.indexOf("/") === 0) return href;
    if (href.indexOf("../") === 0 || href.indexOf("./") === 0) return href;
    return base + href;
  }

  function renderSidebar(activeId, base) {
    base = base || resolveBase();
    var nav = global.SITE_NAV;
    if (!nav) return;
    var sidebar = document.getElementById("kb-sidebar");
    if (!sidebar) return;

    var header = sidebar.querySelector(".kb-sidebar-header");
    if (header) {
      header.innerHTML =
        '<a href="' + prefixHref(nav.brand.home, base) + '" class="kb-logo">' +
        '<img src="' + prefixHref(nav.brand.logo, base) + '" class="kb-logo-icon" alt="">' +
        "<span>" + nav.brand.title + " · " + nav.brand.subtitle + "</span></a>";
    }

    var navEl = sidebar.querySelector(".kb-sidebar-nav") || sidebar.querySelector("#kb-sidebar-nav");
    if (!navEl) return;
    var html = "";
    nav.groups.forEach(function (group) {
      html += '<div class="kb-nav-group"><div class="kb-nav-group-title">' + group.title + "</div>";
      group.links.forEach(function (link) {
        var cls = link.id === activeId ? " kb-nav-link active" : " kb-nav-link";
        var lock = link.lock ? ' <span class="kb-nav-badge">🔒</span>' : "";
        html += '<a href="' + prefixHref(link.href, base) + '" class="' + cls.trim() + '">' + link.label + lock + "</a>";
      });
      html += "</div>";
    });
    navEl.innerHTML = html;
  }

  function initModulePage(opts) {
    opts = opts || {};
    var base = opts.base || resolveBase();
    renderSidebar(opts.activeId, base);
    if (global.KBShell && global.KBShell.initSidebar) global.KBShell.initSidebar();
    if (opts.gateModule && global.SiteAdminGate) {
      global.SiteAdminGate.initModule(opts.gateModule, opts.onUnlock, opts.gateOptions);
    }
  }

  global.ModuleShell = {
    resolveBase: resolveBase,
    prefixHref: prefixHref,
    renderSidebar: renderSidebar,
    initModulePage: initModulePage,
  };
})(window);

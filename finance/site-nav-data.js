/** 全站两栏：每月财务、分析。不展示证券持仓。 */
window.SITE_NAV = {
  brand: {
    title: "Russshare",
    subtitle: "财务",
    home: "index.html",
    logo: "assets/lcai-kb-logo.svg",
  },
  groups: [
    {
      id: "main",
      title: "内容",
      links: [
        { href: "index.html", label: "每月财务", id: "monthly" },
        { href: "analysis/index.html", label: "分析", id: "analysis" },
      ],
    },
  ],
};

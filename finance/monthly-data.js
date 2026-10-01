/**
 * 每月财务。新的一个月加在数组最前面。
 * income / living / repayment 没有账单就写 null，页面显示「未记」。
 */
window.MONTHLY = [
  {
    month: "2026-10",
    securities: 720645.83,
    funds: 50000,
    debt: 1050000,
    income: null,
    living: null,
    repayment: null,
    note: "证券为华宝+国投截图总资产。基金 5 万为当月口述。负债为本金，不含利息。",
    debts: [
      { item: "京东", principal: 500000, term: "近一年滚动" },
      { item: "支付宝", principal: 100000, term: "近一年滚动" },
      { item: "滴滴", principal: 100000, term: "近一年滚动" },
      { item: "云闪付", principal: 150000, term: "约一年后到期" },
      { item: "朋友", principal: 200000, term: "约一年后到期" }
    ]
  },
  {
    month: "2026-06",
    securities: 742203,
    funds: 63352,
    debt: 559607,
    income: null,
    living: null,
    repayment: null,
    note: "仓库 6 月 19 日快照。证券约 73.5 万股票市值 + 现金 7,203。基金为当时未赎回的 63,352。负债为京东 20.9 万、支付宝 15.0 万、朋友 20 万。",
    debts: [
      { item: "京东", principal: 209353, term: "平台" },
      { item: "支付宝", principal: 150254, term: "平台" },
      { item: "朋友", principal: 200000, term: "约定" }
    ]
  }
];

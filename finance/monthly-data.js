/**
 * 每月财务。新的一个月加在数组最前面。
 *
 * 工资口径：到手 25000；给家人 15000；自己留存 10000。
 * 自己生活费由加班费承担，不从上述 25000 里扣。
 */
window.MONTHLY = [
  {
    month: "2026-10",
    incomeNet: 25000,
    toFamily: 15000,
    selfSave: 10000,
    livingFromOvertime: true,
    overtimeNote: "自己生活费用加班费，不占用到手 2.5 万。",
    debt: 1050000,
    note: "负债为本金合计。工资按到手 2.5 万口径；家人 1.5 万、留存 1 万。证券持仓不在本页展示。",
    debts: [
      { item: "京东", principal: 500000, term: "近一年滚动" },
      { item: "支付宝", principal: 100000, term: "近一年滚动" },
      { item: "滴滴", principal: 100000, term: "近一年滚动" },
      { item: "云闪付", principal: 150000, term: "约一年后到期" },
      { item: "朋友", principal: 200000, term: "约一年后到期" }
    ]
  }
];

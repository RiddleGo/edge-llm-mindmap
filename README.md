# Russshare · 财务

**在线访问：** https://riddlego.github.io/lcai-portfolio/

导航只有三栏：

| 栏目 | 路径 | 数据 |
|------|------|------|
| 持仓 | [`index.html`](index.html) | [`snapshot-data.js`](snapshot-data.js) |
| 每月财务 | [`monthly.html`](monthly.html) | [`monthly-data.js`](monthly-data.js)，新月份加在数组最前 |
| 分析 | [`analysis/index.html`](analysis/index.html) | [`analysis/entries.js`](analysis/entries.js)，新文章加在数组最前 |

工资、生活开支、每月还款没有账单时记为「未记」，页面不估算。

健康、OKR、阅读等旧页面还在原路径，主导航不再链入。

| 模块 | 路径 | 说明 |
|------|------|------|
| 财务计划 | [`finance/index.html`](finance/index.html) | 还债 · 执行 · 持仓 · 一页纸规划（门控） |
| LCAI 投资 | [`invest/workbench.html`](invest/workbench.html) | 选股研判 · 规则 · ETF · 书籍 |
| 目标 OKR | [`goals/index.html`](goals/index.html) | 年度目标 · 季度 KR |
| 阅读笔记 | [`learning/index.html`](learning/index.html) | 书库筛选 · 跳转 LCAI 书籍 Tab |
| 职业成长 | [`career/index.html`](career/index.html) | 技能矩阵 · 项目 |
| 健康习惯 | [`health/index.html`](health/index.html) | 本机打卡 · streak |
| 决策日记 | [`journal/index.html`](journal/index.html) | 重大决策记录（门控） |
| 产业研究 | [`docs/research/index.html`](docs/research/index.html) | AI 五层研究 |

[`资产总览.html`](资产总览.html) 与 [`选股研判.html`](选股研判.html) 已重定向至投资/财务子模块。

## 本地使用

```bash
# 生成财务配置（从 资产总览 迁移后维护 finance-config.json）
python scripts/build_finance_module.py

# 选股 CLI（不变）
python 投资系统/engine/screen_stock.py 600519
```

## 隐私说明

- 财务敏感配置：编辑 `finance/finance-config.json`（已 gitignore），运行 `scripts/build_finance_module.py` 生成 `finance-config-data.js`
- 健康打卡：仅 `localStorage`
- 决策日记：公开仓库建议只放框架；正文本地或私有分支

## LCAI 投资（子系统）

买卖裁决唯一来源：[`投资系统/criteria.json`](投资系统/criteria.json) + [`screen-engine.js`](screen-engine.js)

维护手册：[`invest/workbench.html#handbook`](invest/workbench.html#handbook) 或 [`投资系统/08-日常维护手册.md`](投资系统/08-日常维护手册.md)

Agent 指令见 [`AGENTS.md`](AGENTS.md)

## 部署

GitHub Pages 托管于 `main` 分支根目录。有改动推送后约 1–2 分钟生效。

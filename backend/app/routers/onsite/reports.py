import csv
from datetime import datetime, timezone
from io import StringIO

from fastapi import Depends
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import CrawlSession, OnsiteIssue, PageSpeedAudit, SeoPerformanceRow, SitePage, User
from app.schemas import SeoReportOut, SeoReportTableOut

from . import router
from .common import (
    _active_issue,
    _category_label,
    _crawl_label,
    _issue_action,
    _issue_group_rows,
    _issue_impact,
    _issue_owner,
    _issue_retest,
    _issue_sort_key,
    _page_label,
    _page_type,
    _severity_label,
    _sitemap_label,
    _status_name,
    _tenant,
    _url_depth,
)
from .constants import PAGE_TYPE_LABELS
from .diagnosis import (
    _diagnosis_targets,
    _issue_target_keyword,
    _issue_target_market,
    _page_performance,
    _performance_summary,
    _score_text,
    _serp_summary,
)


@router.get("/report", response_model=SeoReportOut)
def seo_report(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeoReportOut:
    tenant = _tenant(db, user)
    targets = _diagnosis_targets(db, user)
    performance = _performance_summary(db, user)
    serp = performance.serp
    target_markets = targets["markets"]
    target_keywords = targets["keywords"]
    market_by_id = targets["market_by_id"]
    seo_by_id = {p.id: p for p in targets["seo_pages"]}
    pages = db.query(SitePage).filter(SitePage.tenant_id == user.tenant_id).order_by(SitePage.path).all()
    issues = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id)
        .order_by(OnsiteIssue.severity, OnsiteIssue.status, OnsiteIssue.created_at)
        .all()
    )
    sessions = (
        db.query(CrawlSession)
        .filter(CrawlSession.tenant_id == user.tenant_id)
        .order_by(CrawlSession.started_at.desc())
        .limit(1)
        .all()
    )
    generated = datetime.now(timezone.utc)
    active = [i for i in issues if _active_issue(i)]
    critical = [i for i in active if i.severity == "critical"]
    high = [i for i in active if i.severity == "high"]
    low = [i for i in active if i.severity == "low"]
    product_pages = [p for p in pages if _page_type(p) in {"product", "solution"}]
    sitemap_pages = [p for p in pages if p.is_in_sitemap == "yes"]
    orphan_issues = [i for i in issues if i.title.startswith("孤岛页面") and i.status not in {"verified", "wont_fix"}]
    inaccessible = [p for p in pages if (p.crawl_status or "").startswith("http_") or p.crawl_status in {"fetch_error", "robots_blocked"}]
    needs_js = [p for p in pages if p.crawl_status == "needs_js" or p.needs_js]
    priority = sorted(active, key=_issue_sort_key)
    groups = _issue_group_rows(active)
    gsc_needed = [i for i in active if i.category == "index"]
    b2b_issues = [i for i in active if i.category == "b2b"]
    lines = [
        f"# SEO 诊断报告 - {tenant.name}",
        "",
        "## 一句话结论",
        "",
        f"本次诊断共检查 {len(pages)} 个页面，发现 {len(active)} 个待处理问题，其中紧急 {len(critical)} 个、重要 {len(high)} 个、一般 {len(low)} 个。"
        "建议先处理影响抓取、收录确认、规范 URL、结构化数据和 B2B 转化信息的问题，再进入内容优化。",
        "",
        "## 本次诊断范围",
        "",
        f"- 客户站点：{tenant.site_origin or '未设置'}",
        f"- 报告时间：{generated.strftime('%Y-%m-%d %H:%M')}",
        f"- 已发现页面：{len(pages)} 个",
        f"- sitemap 覆盖：{len(sitemap_pages)} 个页面",
        f"- 产品/方案类页面：{len(product_pages)} 个",
        f"- GSC 状态：{performance.gsc_status}。Bing 状态：{performance.bing_status}。",
        f"- SERP 市场表现：{serp.status if serp else '未配置'}，已查询 {serp.total_runs if serp else 0} 轮。",
        f"- 测速状态：PageSpeed Insights {performance.pagespeed_status}。",
        "",
        "## 诊断目标",
        "",
        "### 目标国家 / 市场",
        "",
    ]
    if target_markets:
        for market in target_markets:
            lines.append(f"- {market.name}（{market.country_code} / {market.primary_locale}）：{market.status}，机会分 {market.opportunity_score}")
    else:
        lines.append("- 未设置目标国家。建议先在洞察模块登记目标市场，再进行 SEO 诊断。")
    lines += [
        "",
        "### 目标关键词 / 选题",
        "",
    ]
    if target_keywords:
        for keyword, locale, market_name, status in target_keywords[:12]:
            lines.append(f"- {keyword}（{locale} / {market_name} / {status}）")
        if len(target_keywords) > 12:
            lines.append(f"- 另有 {len(target_keywords) - 12} 个关键词/需求信号未在摘要中展开。")
    else:
        lines.append("- 未设置目标关键词。建议先登记核心产品词、行业词、采购意图词，再跑诊断。")
    lines += [
        "",
        "### 诊断口径",
        "",
        "- 技术 SEO 问题会优先服务目标国家和目标关键词对应页面。",
        "- 未绑定目标关键词的页面仍会诊断，但在整改优先级上应低于核心产品/方案页。",
        "- 速度体验使用 PageSpeed Insights；搜索表现优先使用 GSC/Bing CSV 或后续授权 API。",
        "",
    ]
    lines += [
        "## SEO 表现",
        "",
    ]
    if performance.total_impressions:
        lines += [
            f"- 总曝光：{performance.total_impressions}，总点击：{performance.total_clicks}，平均 CTR：{performance.avg_ctr if performance.avg_ctr is not None else '未测'}%，平均排名：{performance.avg_position if performance.avg_position is not None else '未测'}。",
            "- 重点国家：" + "；".join(f"{item.key} 曝光 {item.impressions} / 点击 {item.clicks}" for item in performance.by_country[:5]),
            "- 重点关键词：" + "；".join(f"{item.key} 曝光 {item.impressions} / 点击 {item.clicks} / 排名 {item.position or '未测'}" for item in performance.by_query[:5]),
            "",
        ]
    else:
        lines += [
            "- 暂未导入 GSC/Bing 搜索表现数据，无法判断真实曝光、点击、CTR 和平均排名。",
            "- 当前收录相关结论仍按“需授权核验”处理，不能直接判定已收录或未收录。",
            "",
        ]
    lines += ["### SERP 竞争表现", ""]
    if serp and serp.latest_runs:
        lines += [
            f"- Bright Data SERP 状态：{serp.status}。已记录 {serp.total_runs} 轮关键词查询。",
            f"- 我方可见：{serp.own_visible_runs} 轮；竞品可见：{serp.competitor_visible_runs} 轮；我方平均最佳排名：{serp.avg_own_position if serp.avg_own_position is not None else '未出现'}。",
            "",
        ]
        for run in serp.latest_runs[:8]:
            own = run.own_best_position if run.own_best_position is not None else "未出现"
            comp = run.competitor_best_position if run.competitor_best_position is not None else "未出现"
            lines.append(f"- {run.keyword}（{run.country}/{run.device}）：我方 {own}，竞品 {comp}，前 {run.result_count} 条第三方 {run.third_party_count} 个。")
        if serp.top_third_party_domains:
            lines.append("- 高频第三方域名：" + "；".join(f"{item['domain']}({item['count']})" for item in serp.top_third_party_domains[:6]))
        lines.append("")
    else:
        lines += [
            "- 暂未运行 SERP 查询。建议用目标国家和核心关键词查询 Google 前 10/20，判断我方、竞品和第三方平台占位。",
            "- SERP 查询结果是市场可见度证据，不等同 GSC 点击/曝光，也不等同真实外链权重。",
            "",
        ]
    if performance.speed_latest:
        lines += ["### 速度体验", ""]
        for audit in performance.speed_latest[:6]:
            lines.append(
                f"- {audit.strategy} · {audit.url}：性能 {_score_text(audit.performance_score)}，SEO {_score_text(audit.seo_score)}，LCP {audit.lcp_ms or '未测'}ms，状态 {audit.status}。"
            )
        lines.append("")
    else:
        lines += [
            "### 速度体验",
            "",
            "- 暂未运行 PageSpeed Insights 测速。建议先测首页、核心产品页、核心方案页的移动端和桌面端。",
            "",
        ]
    if sessions:
        s = sessions[0]
        lines += [
            "## 抓取概况",
            "",
            f"- 本次最多抓取 {s.max_urls} 个 URL，最大深度 {s.max_depth}。",
            f"- 实际发现 {s.discovered} 个 URL，成功读取 {s.fetched} 个，失败 {s.failed} 个。",
            f"- robots 阻止 {s.robots_blocked} 个，疑似需要浏览器渲染 {s.needs_js} 个。",
            f"- 备注：{s.note or '无'}",
            "",
        ]
    lines += [
        "## 主要风险",
        "",
        f"1. 抓取与访问风险：{len(inaccessible)} 个页面存在访问失败、404、服务器错误或 robots 阻止。",
        f"2. 收录确认风险：{len(gsc_needed)} 个页面需要接入 GSC 后确认真实索引状态。",
        f"3. 结构与规范风险：{sum(1 for i in active if i.category in {'canonical', 'schema', 'heading'})} 个问题影响搜索引擎和 AI 对页面的理解。",
        f"4. B2B 获客风险：{len(b2b_issues)} 个问题影响海外买家判断供应商能力和发起询盘。",
        f"5. JS 渲染风险：{len(needs_js)} 个页面疑似需要浏览器渲染，普通 HTML 抓取可能读不到完整内容。",
        f"6. SERP 可见度风险：{(serp.total_runs - serp.own_visible_runs) if serp else '未测'} 个关键词查询轮次未观察到我方自然结果。",
        "",
        "## 问题汇总",
        "",
    ]
    if groups:
        for (severity, category, title), count in groups[:12]:
            lines.append(f"- {_severity_label(severity)} · {_category_label(category)} · {title}：涉及 {count} 个页面")
    else:
        lines.append("- 当前没有待处理问题。")
    lines += [
        "",
        "## 优先整改清单",
        "",
    ]
    for idx, issue in enumerate(priority[:20], start=1):
        page = issue.page
        lines += [
            f"### {idx}. {_severity_label(issue.severity)} · {issue.title}",
            "",
            f"- 页面：{_page_label(page)}",
            f"- 目标国家：{_issue_target_market(issue, page, market_by_id)}",
            f"- 关联关键词：{_issue_target_keyword(issue, page, seo_by_id)}",
            f"- 问题类型：{_category_label(issue.category)}",
            f"- 当前状态：{_status_name(issue.status)}",
            f"- 为什么重要：{_issue_impact(issue)}",
            f"- 诊断依据：{issue.detail or '暂无详细证据'}",
            f"- 建议动作：{_issue_action(issue)}",
            f"- 建议负责人：{_issue_owner(issue)}",
            f"- 复测方式：{_issue_retest(issue)}",
            "",
        ]
    if not priority:
        lines.append("当前没有诊断问题。")
    lines += [
        "",
        "## 需要客户配合",
        "",
        "1. 提供 Google Search Console / Bing Webmaster Tools 授权，用于确认真实收录、曝光和点击。",
        "2. 确认产品参数、认证、应用行业、MOQ、交期、质保、案例等 B2B 事实，避免 AI 或执行人员误写。",
        "3. 指定客户网站技术联系人，处理 404、canonical、schema、sitemap、robots、页面模板等技术项。",
        "4. 每轮修改上线后，回到系统执行复测，形成“发现问题 - 整改 - 复测”的闭环。",
        "",
        "## 下一步建议",
        "",
        "1. 第一优先级：处理无法访问、noindex、canonical、schema、重复 URL 等基础问题。",
        "2. 第二优先级：补齐产品/方案页的 B2B 转化信息，包括参数、应用场景、认证、案例和询盘入口。",
        "3. 第三优先级：优化文章、图片 alt、内链和页面深度，提升搜索引擎与 AI 系统的可理解性。",
        "4. 报告中的 AI 建议均为草案，客户业务事实必须人工确认后再上线。",
        "",
    ]
    return SeoReportOut(title=f"SEO 诊断报告 - {tenant.name}", markdown="\n".join(lines), generated_at=generated)


@router.get("/report-table", response_model=SeoReportTableOut)
def seo_report_table(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> SeoReportTableOut:
    targets = _diagnosis_targets(db, user)
    market_by_id = targets["market_by_id"]
    seo_by_id = {p.id: p for p in targets["seo_pages"]}
    performance_rows = db.query(SeoPerformanceRow).filter(SeoPerformanceRow.tenant_id == user.tenant_id).all()
    serp = _serp_summary(db, user)
    issues = (
        db.query(OnsiteIssue)
        .options(selectinload(OnsiteIssue.page))
        .filter(OnsiteIssue.tenant_id == user.tenant_id)
        .order_by(OnsiteIssue.severity, OnsiteIssue.status, OnsiteIssue.created_at)
        .all()
    )
    generated = datetime.now(timezone.utc)
    active = sorted([i for i in issues if _active_issue(i)], key=_issue_sort_key)
    has_speed = db.query(PageSpeedAudit.id).filter(PageSpeedAudit.tenant_id == user.tenant_id).first() is not None
    out = StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "优先级",
        "严重程度",
        "问题类型",
        "目标国家/地区",
        "关联关键词",
        "页面",
        "页面URL",
        "当前状态",
        "客户能理解的问题",
        "为什么影响获客",
        "建议整改动作",
        "建议负责人",
        "复测方式",
        "抓取状态",
        "HTTP状态",
        "sitemap状态",
        "页面类型",
        "URL深度",
        "正文规模",
        "图片Alt缺失",
        "测速状态",
        "页面抓取方式",
        "JS渲染状态",
        "SERP我方可见轮次",
        "SERP竞品可见轮次",
        "SERP第三方高频域名",
        "曝光",
        "点击",
        "CTR",
        "平均排名",
        "技术证据",
    ])
    for index, issue in enumerate(active, start=1):
        page = issue.page
        page_perf = _page_performance(performance_rows, page)
        page_type = _page_type(page) if page else "other"
        word_count = page.word_count if page else 0
        missing_alt = page.images_missing_alt if page else 0
        image_count = page.image_count if page else 0
        evidence_bits = []
        if page:
            evidence_bits.append(f"抓取={_crawl_label(page.crawl_status)}")
            if page.http_status:
                evidence_bits.append(f"HTTP={page.http_status}")
            if page.content_type:
                evidence_bits.append(f"Content-Type={page.content_type}")
            if page.ttfb_ms is not None:
                evidence_bits.append(f"TTFB={page.ttfb_ms}ms")
            if page.redirect_count:
                evidence_bits.append(f"跳转={page.redirect_count}次")
            if page.body_hash:
                evidence_bits.append(f"内容指纹={page.body_hash[:12]}")
            if page.fetch_mode:
                evidence_bits.append(f"抓取方式={page.fetch_mode}")
            if page.render_status and page.render_status != "not_needed":
                evidence_bits.append(f"渲染={page.render_status}")
            evidence_bits.append(f"sitemap={_sitemap_label(page.is_in_sitemap)}")
            evidence_bits.append(f"URL深度={_url_depth(page.path)}")
            if word_count:
                evidence_bits.append(f"正文约{word_count}词")
            if image_count:
                evidence_bits.append(f"图片缺alt {missing_alt}/{image_count}")
        if issue.evidence:
            evidence_bits.append(issue.evidence.replace("\n", " / ")[:500])
        writer.writerow([
            f"P{index}",
            _severity_label(issue.severity),
            _category_label(issue.category),
            _issue_target_market(issue, page, market_by_id),
            _issue_target_keyword(issue, page, seo_by_id),
            page.title or page.meta_title or page.path if page else "",
            page.path if page else "",
            _status_name(issue.status),
            issue.title,
            _issue_impact(issue),
            _issue_action(issue),
            _issue_owner(issue),
            _issue_retest(issue),
            _crawl_label(page.crawl_status if page else None),
            page.http_status if page and page.http_status else "未测",
            _sitemap_label(page.is_in_sitemap if page else None),
            PAGE_TYPE_LABELS.get(page_type, page_type),
            _url_depth(page.path) if page else "",
            f"约 {word_count or 0} 词",
            f"{missing_alt or 0}/{image_count or 0}",
            "见 PageSpeed 汇总" if has_speed else "未测速",
            page.fetch_mode if page else "",
            page.render_status if page else "",
            serp.own_visible_runs if serp else "未测",
            serp.competitor_visible_runs if serp else "未测",
            "；".join(f"{item['domain']}({item['count']})" for item in (serp.top_third_party_domains if serp else [])[:5]) or "未测",
            page_perf.impressions if page_perf else "未导入",
            page_perf.clicks if page_perf else "未导入",
            f"{page_perf.ctr}%" if page_perf and page_perf.ctr is not None else "未导入",
            page_perf.position if page_perf and page_perf.position is not None else "未导入",
            "；".join(evidence_bits) or issue.detail,
        ])
    return SeoReportTableOut(filename=f"seo整改执行表-{generated.date().isoformat()}.csv", csv=out.getvalue(), generated_at=generated)

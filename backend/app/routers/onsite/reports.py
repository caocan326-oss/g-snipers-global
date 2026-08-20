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
        f"# 网站检查说明 - {tenant.name}",
        "",
        "## 一句话结论",
        "",
        f"本次共查看 {len(pages)} 个页面，发现 {len(active)} 个待处理问题，其中紧急 {len(critical)} 个、优先 {len(high)} 个、常规 {len(low)} 个。"
        "建议先处理打不开、搜索是否收录、标准网址、页面说明和询盘信息，再优化正文。",
        "",
        "## 本次检查范围",
        "",
        f"- 客户网站：{tenant.site_origin or '未设置'}",
        f"- 说明时间：{generated.strftime('%Y-%m-%d %H:%M')}",
        f"- 已发现页面：{len(pages)} 个",
        f"- 网站地图覆盖：{len(sitemap_pages)} 个页面",
        f"- 产品/方案类页面：{len(product_pages)} 个",
        f"- Google 搜索数据：{performance.gsc_status}。Bing 数据：{performance.bing_status}。",
        f"- 关键词位置检查：{serp.status if serp else '未配置'}，已查询 {serp.total_runs if serp else 0} 轮。",
        f"- 测速状态：网页速度 {performance.pagespeed_status}。",
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
        lines.append("- 未设置目标国家。建议先登记目标市场，再做网站检查。")
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
        lines.append("- 未设置目标关键词。建议先登记核心产品词、行业词和采购意图词，再做检查。")
    lines += [
        "",
        "### 检查口径",
        "",
        "- 技术问题优先对应目标国家和目标关键词页面。",
        "- 未绑定关键词的页面仍会检查，但优先级低于核心产品/方案页。",
        "- 速度用网页测速；搜索表现优先用 Google / Bing 表格或授权同步。",
        "",
    ]
    lines += [
        "## 搜索表现",
        "",
    ]
    if performance.total_impressions:
        lines += [
            f"- 总展示：{performance.total_impressions}，总点击：{performance.total_clicks}，平均点开率：{performance.avg_ctr if performance.avg_ctr is not None else '尚未检查'}%，平均位置：{performance.avg_position if performance.avg_position is not None else '尚未检查'}。",
            "- 重点国家：" + "；".join(f"{item.key} 展示 {item.impressions} / 点击 {item.clicks}" for item in performance.by_country[:5]),
            "- 重点关键词：" + "；".join(f"{item.key} 展示 {item.impressions} / 点击 {item.clicks} / 位置 {item.position or '尚未检查'}" for item in performance.by_query[:5]),
            "",
        ]
    else:
        lines += [
            "- 尚未导入 Google / Bing 搜索数据，无法判断真实展示、点击和平均位置。",
            "- 是否被搜索收录，在授权核验前不能直接下结论。",
            "",
        ]
    lines += ["### 搜索结果位置", ""]
    if serp and serp.latest_runs:
        lines += [
            f"- 关键词位置检查：{serp.status}。已记录 {serp.total_runs} 轮。",
            f"- 我方出现：{serp.own_visible_runs} 轮；竞品出现：{serp.competitor_visible_runs} 轮；我方最好位置：{serp.avg_own_position if serp.avg_own_position is not None else '未出现'}。",
            "",
        ]
        for run in serp.latest_runs[:8]:
            own = run.own_best_position if run.own_best_position is not None else "未出现"
            comp = run.competitor_best_position if run.competitor_best_position is not None else "未出现"
            lines.append(f"- {run.keyword}（{run.country}/{run.device}）：我方 {own}，竞品 {comp}，前 {run.result_count} 条中第三方 {run.third_party_count} 个。")
        if serp.top_third_party_domains:
            lines.append("- 常见第三方网站：" + "；".join(f"{item['domain']}({item['count']})" for item in serp.top_third_party_domains[:6]))
        lines.append("")
    else:
        lines += [
            "- 尚未查询目标词在 Google 前几页的位置。建议用目标国家和核心词核对我方、竞品和第三方平台。",
            "- 位置检查说明“有没有出现”，不等于点击、展示，也不等于外链质量。",
            "",
        ]
    if performance.speed_latest:
        lines += ["### 打开速度", ""]
        for audit in performance.speed_latest[:6]:
            lines.append(
                f"- {audit.strategy} · {audit.url}：性能 {_score_text(audit.performance_score)}，搜索友好度 {_score_text(audit.seo_score)}，最大内容绘制 {audit.lcp_ms or '尚未检查'}ms，状态 {audit.status}。"
            )
        lines.append("")
    else:
        lines += [
            "### 打开速度",
            "",
            "- 尚未测速。建议先测首页、核心产品页和方案页的手机端与电脑端。",
            "",
        ]
    if sessions:
        s = sessions[0]
        lines += [
            "## 查看概况",
            "",
            f"- 本次最多查看 {s.max_urls} 个网址，最大深度 {s.max_depth}。",
            f"- 实际发现 {s.discovered} 个网址，成功读取 {s.fetched} 个，失败 {s.failed} 个。",
            f"- 网站规则阻止 {s.robots_blocked} 个，疑似需要浏览器才能显示 {s.needs_js} 个。",
            f"- 备注：{s.note or '无'}",
            "",
        ]
    lines += [
        "## 主要风险",
        "",
        f"1. 打不开：{len(inaccessible)} 个页面访问失败、不存在、服务器错误或被网站规则阻止。",
        f"2. 是否收录：{len(gsc_needed)} 个页面需要接入 Google 后才能确认真实收录。",
        f"3. 页面结构：{sum(1 for i in active if i.category in {'canonical', 'schema', 'heading'})} 个问题影响搜索和 AI 理解页面。",
        f"4. 询盘转化：{len(b2b_issues)} 个问题影响海外买家判断能力和发起询盘。",
        f"5. 需浏览器显示：{len(needs_js)} 个页面普通打开可能读不到完整内容。",
        f"6. 搜索结果位置：{(serp.total_runs - serp.own_visible_runs) if serp else '尚未检查'} 轮关键词查询未看到我方结果。",
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
        "## 优先处理清单",
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
            f"- 查看依据：{issue.detail or '暂无详细依据'}",
            f"- 建议动作：{_issue_action(issue)}",
            f"- 建议负责人：{_issue_owner(issue)}",
            f"- 复查方式：{_issue_retest(issue)}",
            "",
        ]
    if not priority:
        lines.append("当前没有待处理问题。")
    lines += [
        "",
        "## 需要客户配合",
        "",
        "1. 提供 Google / Bing 搜索数据授权，用于确认真实收录、展示和点击。",
        "2. 确认产品参数、认证、应用行业、起订量、交期、质保和案例等事实，避免误写。",
        "3. 指定网站技术联系人，处理打不开、标准网址、页面说明、网站地图和模板问题。",
        "4. 每轮修改上线后，回到系统复查，形成“发现问题 - 修改 - 复查”。",
        "",
        "## 下一步建议",
        "",
        "1. 先处理打不开、不让收录、标准网址错误、页面说明缺失和重复网址。",
        "2. 再补齐产品/方案页的参数、应用场景、认证、案例和询盘入口。",
        "3. 然后优化文章、图片说明、站内链接和页面层级，让搜索和 AI 更容易理解。",
        "4. 说明中的系统建议均为草案，业务事实须人工确认后再上线。",
        "",
    ]
    return SeoReportOut(title=f"网站检查说明 - {tenant.name}", markdown="\n".join(lines), generated_at=generated)


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
        "建议改法",
        "建议负责人",
        "复查方式",
        "查看状态",
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
    return SeoReportTableOut(filename=f"网站改法执行表-{generated.date().isoformat()}.csv", csv=out.getvalue(), generated_at=generated)

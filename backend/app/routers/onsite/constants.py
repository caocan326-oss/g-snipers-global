CATEGORIES = {"tdk", "heading", "internal_link", "schema", "index", "crawl", "canonical", "image", "content", "b2b"}
ISSUE_STATUSES = {"open", "drafted", "draft_applied", "confirmed", "verified", "wont_fix"}
OPENISH = {"open", "drafted", "draft_applied", "confirmed"}
BOARD_ACTIONABLE = {"open", "drafted", "draft_applied", "confirmed"}
AI_BATCH_DEFAULT_LIMIT = 5
AI_BATCH_MAX_LIMIT = 10
SEVERITY_RANK = {"critical": 0, "high": 1, "low": 2}
SEVERITY_LABELS = {"critical": "紧急", "high": "重要", "low": "一般"}
CATEGORY_LABELS = {
    "tdk": "标题/描述",
    "heading": "页面标题结构",
    "internal_link": "内链入口",
    "schema": "结构化数据",
    "index": "收录确认",
    "crawl": "抓取访问",
    "canonical": "规范 URL",
    "image": "图片说明",
    "content": "内容质量",
    "b2b": "B2B 转化信息",
}
PAGE_TYPE_LABELS = {
    "home": "首页",
    "product": "产品页",
    "solution": "方案页",
    "case": "案例页",
    "article": "文章页",
    "contact": "联系页",
    "other": "其他页面",
}

INTEGRATION_FIELDS = {
    "gsc_oauth_client_id": ("Google OAuth Client ID", "gsc_oauth_client_id"),
    "gsc_oauth_client_secret": ("Google OAuth Client Secret", "gsc_oauth_client_secret"),
    "gsc_oauth_redirect_uri": ("Google OAuth Redirect URI", "gsc_oauth_redirect_uri"),
    "pagespeed_api_key": ("PageSpeed API Key", "pagespeed_api_key"),
    "brightdata_dataset_api_key": ("Bright Data Dataset API Key", "brightdata_dataset_api_key"),
    "brightdata_serp_dataset_id": ("Bright Data SERP Dataset ID", "brightdata_serp_dataset_id"),
    "brightdata_serp_endpoint": ("Bright Data SERP Endpoint", "brightdata_serp_endpoint"),
}
CRAWL_LABELS = {
    "ok": "可正常访问",
    "http_4xx": "页面不存在或访问失败",
    "http_5xx": "服务器错误",
    "robots_blocked": "robots 阻止抓取",
    "needs_js": "疑似需要浏览器渲染",
    "fetch_error": "抓取失败",
    "untested": "未抓取",
}

PERFORMANCE_SOURCE_LABELS = {"gsc_csv": "Google Search Console CSV", "bing_csv": "Bing Webmaster CSV"}
PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
GSC_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GSC_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GSC_SEARCH_ANALYTICS_ENDPOINT = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
BRIGHTDATA_SERP_INPUT_URL = "https://www.google.com/"

CSV_ALIASES = {
    "query": {"query", "queries", "查询", "搜索查询", "关键词", "关键字"},
    "page_url": {"page", "pages", "url", "landing page", "网页", "页面", "着陆页", "链接"},
    "country": {"country", "countries", "国家/地区", "国家", "地区", "region"},
    "device": {"device", "设备", "终端"},
    "date": {"date", "日期", "day"},
    "clicks": {"clicks", "点击次数", "点击", "click"},
    "impressions": {"impressions", "展示次数", "曝光", "曝光量", "展现"},
    "ctr": {"ctr", "点击率"},
    "position": {"position", "avg. position", "average position", "平均排名", "排名"},
}

CATEGORY_GUIDANCE = {
    "tdk": {
        "impact": "影响搜索结果标题/摘要表达和买家点击判断。",
        "action": "检查页面主题、目标市场和品牌表达，补齐或改写 Title / Description。",
        "retest": "回抓页面后比对 title、description 与处理方案是否一致。",
        "owner": "内容运营 / 客户经理",
    },
    "heading": {
        "impact": "影响页面主题识别、内容层级和用户阅读路径。",
        "action": "补齐 H1 或调整冲突标题，让页面主题和正文结构一致。",
        "retest": "回抓页面后检查 H1 与 headings 是否已更新。",
        "owner": "内容运营 / 网站编辑",
    },
    "internal_link": {
        "impact": "影响核心页面发现、页面权重传递和买家继续浏览路径。",
        "action": "在相关页面加入可抓取的真实 href 内链，并使用清晰锚文本。",
        "retest": "回抓页面后检查目标 URL 是否出现在内链列表。",
        "owner": "内容运营 / 网站编辑",
    },
    "schema": {
        "impact": "影响搜索引擎和 AI 系统理解公司、产品、文章或面包屑信息。",
        "action": "生成 JSON-LD 草案，人工核实公司、产品、认证、价格等事实后上线。",
        "retest": "回抓页面后检查 JSON-LD 类型和语法；关键页再人工用 Rich Results Test 复核。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "index": {
        "impact": "影响是否能确认 Google/Bing 真实索引状态；无授权时只能保持未测。",
        "action": "接入 GSC/Bing 后复核真实索引状态；未授权前不要编造已收录或未收录。",
        "retest": "授权平台数据后复查 URL Inspection 或搜索平台状态。",
        "owner": "客户经理 / 客户授权人",
    },
    "crawl": {
        "impact": "影响系统能否读取页面事实，抓取失败时不能继续判断内容质量。",
        "action": "排查 HTTP 状态、robots、跳转、TLS、超时或 JS 空壳问题。",
        "retest": "修复后重新抓取页面，确认状态码、最终 URL 和正文可读取。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "canonical": {
        "impact": "影响搜索引擎判断规范 URL，错误 canonical 可能让核心页被合并到错误页面。",
        "action": "确认页面规范版本，修正 canonical 指向；高风险项必须人工确认。",
        "retest": "回抓页面后检查 canonical 是否指向预期 URL。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "image": {
        "impact": "影响图片内容理解、图片搜索和无障碍体验。",
        "action": "为关键产品图、认证图、应用图补充准确 alt，无法确认图片内容时人工核对。",
        "retest": "回抓页面后检查图片数量和缺失 alt 数是否下降。",
        "owner": "内容运营 / 网站编辑",
    },
    "content": {
        "impact": "影响买家理解产品价值，也影响搜索和 AI 系统抽取可引用内容。",
        "action": "补充产品参数、应用场景、FAQ、案例、认证或询盘入口，业务事实必须人工确认。",
        "retest": "回抓页面后检查正文可抽取字数、标题结构和关键内容是否已补齐。",
        "owner": "内容运营 / 客户经理",
    },
    "b2b": {
        "impact": "影响海外 B2B 买家判断供应商能力、产品适配度和是否发起询盘。",
        "action": "补齐产品参数、应用行业、认证、案例、MOQ/交期/质保等需确认信息，并强化询盘入口。",
        "retest": "回抓页面后检查正文、内链、CTA 和结构化信息是否覆盖关键 B2B 决策字段。",
        "owner": "客户经理 / 内容运营",
    },
}

B2B_PATH_HINTS = ("product", "products", "solution", "solutions", "application", "applications", "case", "cases", "industry", "industries")

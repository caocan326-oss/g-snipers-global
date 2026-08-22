CATEGORIES = {"tdk", "heading", "internal_link", "schema", "index", "crawl", "canonical", "image", "content", "b2b"}
ISSUE_STATUSES = {"open", "drafted", "draft_applied", "confirmed", "verified", "wont_fix"}
OPENISH = {"open", "drafted", "draft_applied", "confirmed"}
BOARD_ACTIONABLE = {"open", "drafted", "draft_applied", "confirmed"}
AI_BATCH_DEFAULT_LIMIT = 5
AI_BATCH_MAX_LIMIT = 10
SEVERITY_RANK = {"critical": 0, "high": 1, "low": 2}
SEVERITY_LABELS = {"critical": "紧急", "high": "优先", "low": "常规"}
ISSUE_PLAIN_TITLES = {
    "收录状态未测（需 GSC）": "还没确认谷歌有没有收到这个页",
    "搜索是否收录尚未检查": "还没确认谷歌有没有收到这个页",
    "Canonical 未登记": "标准网址没写清，搜索可能认错页",
    "标准网址未登记": "标准网址没写清，搜索可能认错页",
    "缺少 JSON-LD / schema": "页面缺少给搜索看的说明",
    "缺少页面说明标记": "页面缺少给搜索看的说明",
    "页面缺少给搜索看的说明": "页面缺少给搜索看的说明",
    "首页缺少公司介绍说明": "首页缺少公司介绍说明",
    "产品页缺少给搜索看的产品说明": "产品页缺少给搜索看的产品说明",
    "页面说明和正文对不上": "页面说明和正文对不上",
    "关键页告诉搜索不要收录": "关键页告诉搜索不要收录",
    "不打开脚本时几乎没有正文": "不打开脚本时几乎没有正文",
    "页面开头没有直接回答买家问题": "页面开头没有直接回答买家问题",
    "首页公司说明标记缺失": "首页缺少公司介绍说明",
    "页面声明 noindex": "这个页告诉搜索不要收录",
    "缺少 H1": "页面缺少主标题",
    "缺少 Title": "搜索结果里可能没有标题",
    "Description 过短或为空": "搜索摘要几乎是空的",
    "页面摘要过短": "搜索摘要太短",
    "德文 Description 为空": "德文页摘要是空的",
    "正文内容过薄": "正文太少，买家看不够",
    "图片 Alt 缺失": "图片没有文字说明",
    "缺少内链": "和其他页缺少互相链接",
    "URL 层级过深": "网址层级太深，不好被找到",
    "页面能否打开尚未检查": "还没确认这个页打不打得开",
    "首页标题过长": "首页标题过长",
    "GEO-ENT-002 缺少 Organization / WebSite schema": "首页缺少公司介绍说明",
    "GEO-ENT-002 产品/方案页缺少 Product 或 Service schema": "产品页缺少给搜索看的产品说明",
    "产品页缺少 Product schema": "产品页缺少给搜索看的产品说明",
    "GEO-SCHEMA-002 Schema 类型与正文弱一致": "页面说明和正文对不上",
    "GEO-INDEX-001 关键页声明 noindex": "关键页告诉搜索不要收录",
    "GEO-CRAWL-003 无 JS 正文过短": "不打开脚本时几乎没有正文",
    "GEO-STRUCT-001 首屏缺少直接答案": "页面开头没有直接回答买家问题",
}
CATEGORY_LABELS = {
    "tdk": "标题与摘要",
    "heading": "页面标题",
    "internal_link": "站内链接",
    "schema": "页面说明标记",
    "index": "搜索是否收录",
    "crawl": "页面能否打开",
    "canonical": "标准网址",
    "image": "图片说明",
    "content": "正文",
    "b2b": "询盘页",
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
    "gsc_oauth_client_id": ("Google 授权 Client ID", "gsc_oauth_client_id"),
    "gsc_oauth_client_secret": ("Google 授权 Client Secret", "gsc_oauth_client_secret"),
    "gsc_oauth_redirect_uri": ("Google 授权回调地址", "gsc_oauth_redirect_uri"),
    "pagespeed_api_key": ("网页测速 API Key", "pagespeed_api_key"),
    "ce17_user": ("17CE 账号", "ce17_user"),
    "ce17_api_pwd": ("17CE api_pwd", "ce17_api_pwd"),
    "brightdata_dataset_api_key": ("排名检查 API Key", "brightdata_dataset_api_key"),
    "brightdata_serp_zone": ("排名检查 SERP 区", "brightdata_serp_zone"),
    "brightdata_serp_dataset_id": ("排名检查数据集 ID", "brightdata_serp_dataset_id"),
    "brightdata_serp_endpoint": ("排名检查接口地址", "brightdata_serp_endpoint"),
}
CRAWL_LABELS = {
    "ok": "可正常访问",
    "http_4xx": "页面不存在或访问失败",
    "http_5xx": "服务器错误",
    "robots_blocked": "robots 阻止抓取",
    "needs_js": "疑似需要浏览器渲染",
    "fetch_error": "抓取失败",
    "untested": "尚未查看",
}

PERFORMANCE_SOURCE_LABELS = {"gsc_csv": "Google Search Console CSV", "bing_csv": "Bing Webmaster CSV"}
PAGESPEED_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
GSC_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GSC_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GSC_SEARCH_ANALYTICS_ENDPOINT = "https://searchconsole.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"
GSC_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
BRIGHTDATA_SERP_SEARCH_URL = "https://www.google.com/search"

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
        "impact": "影响搜索结果里的标题、摘要，以及买家是否愿意点开。",
        "action": "按页面主题和目标市场，补齐或改写标题与摘要。",
        "retest": "重新打开页面，核对标题、摘要是否已按改法更新。",
        "owner": "内容运营 / 客户经理",
    },
    "heading": {
        "impact": "影响页面主题识别、内容层级和用户阅读路径。",
        "action": "补齐 H1 或调整冲突标题，让页面主题和正文结构一致。",
        "retest": "重新打开页面，检查主标题和层级是否已更新。",
        "owner": "内容运营 / 网站编辑",
    },
    "internal_link": {
        "impact": "影响核心页面发现、页面权重传递和买家继续浏览路径。",
        "action": "在相关页面加入可点击的站内链接，并用清楚的文字说明去向。",
        "retest": "重新打开页面，检查目标网址是否出现在站内链接中。",
        "owner": "内容运营 / 网站编辑",
    },
    "schema": {
        "impact": "影响搜索和 AI 是否能正确理解公司、产品和文章信息。",
        "action": "起草页面说明标记（JSON-LD），人工核实公司、产品、认证等事实后再上线。",
        "retest": "重新打开页面，检查说明标记是否已更新；关键页再人工复核。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "index": {
        "impact": "影响能否确认 Google / Bing 是否真正收录该页；未授权时只能写尚未检查。",
        "action": "接入 Google / Bing 后再核真实收录。未授权前不要写成已收录或未收录。",
        "retest": "授权后对照平台里的网址检查结果。",
        "owner": "客户经理 / 客户授权人",
    },
    "crawl": {
        "impact": "影响系统能否读到页面内容；打不开时无法继续判断正文质量。",
        "action": "排查打不开、跳转、安全证书、超时或需浏览器才能显示的问题。",
        "retest": "修复后重新打开页面，确认能读到最终网址和正文。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "canonical": {
        "impact": "影响搜索把哪一个网址当作正式页面；指错会导致核心页被合并到错误地址。",
        "action": "确认正式网址，修正标准网址指向；优先项必须人工确认。",
        "retest": "重新打开页面，检查标准网址是否指向预期地址。",
        "owner": "技术执行 / 客户网站负责人",
    },
    "image": {
        "impact": "影响图片内容理解、图片搜索和无障碍体验。",
        "action": "为关键产品图、认证图、应用图补充准确 alt，无法确认图片内容时人工核对。",
        "retest": "重新打开页面，检查缺说明的图片是否减少。",
        "owner": "内容运营 / 网站编辑",
    },
    "content": {
        "impact": "影响买家理解产品价值，也影响搜索和 AI 系统抽取可引用内容。",
        "action": "补充产品参数、应用场景、FAQ、案例、认证或询盘入口，业务事实必须人工确认。",
        "retest": "重新打开页面，检查正文、标题和关键内容是否已补齐。",
        "owner": "内容运营 / 客户经理",
    },
    "b2b": {
        "impact": "影响海外 B2B 买家判断供应商能力、产品适配度和是否发起询盘。",
        "action": "补齐产品参数、应用行业、认证、案例、MOQ/交期/质保等需确认信息，并强化询盘入口。",
        "retest": "重新打开页面，检查正文、链接和询盘入口是否覆盖买家决策信息。",
        "owner": "客户经理 / 内容运营",
    },
}

B2B_PATH_HINTS = ("product", "products", "solution", "solutions", "application", "applications", "case", "cases", "industry", "industries")

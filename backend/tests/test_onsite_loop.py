from app.models import OnsiteIssue, SitePage
from app.onsite_loop import (
    ONSITE_CUSTOMER_CLOSE,
    issue_customer_note,
    issue_customer_paste,
    plain_issue_title,
    weekly_onsite_paste,
    weekly_onsite_picks,
)


def test_plain_issue_title_strips_internal_codes() -> None:
    assert plain_issue_title("GEO-ENT-002 缺少 Organization / WebSite schema") == "首页缺少公司介绍说明"
    assert "schema" not in plain_issue_title("产品页缺少 Product schema").lower()
    assert plain_issue_title("缺少 JSON-LD / schema") == "页面缺少给搜索看的说明"


def test_issue_customer_note_has_page_url_ask_and_retest() -> None:
    page = SitePage(
        id="p1",
        tenant_id="t1",
        path="/products/nexode-100w",
        locale="en-US",
        title="Nexode 100W",
        crawl_status="ok",
    )
    issue = OnsiteIssue(
        id="i1",
        tenant_id="t1",
        page_id=page.id,
        category="tdk",
        title="首页标题过长",
        severity="critical",
        risk="high",
        status="open",
        proposed_change="把标题改成 100W USB-C Charger for Laptops | UGREEN",
    )
    note = issue_customer_note(issue, page, "https://www.ugreen.com")
    assert "请改这一页：Nexode 100W（/products/nexode-100w）" in note
    assert "https://www.ugreen.com/products/nexode-100w" in note
    assert "问题：首页标题过长" in note
    assert "请做：把标题改成 100W USB-C Charger for Laptops | UGREEN" in note
    assert "重新打开页面" in note
    assert ONSITE_CUSTOMER_CLOSE in note

    paste = issue_customer_paste(issue, page, "https://www.ugreen.com")
    assert paste == note


def test_issue_customer_note_falls_back_to_category_action() -> None:
    page = SitePage(
        id="p2",
        tenant_id="t1",
        path="/",
        locale="en-US",
        title="Home",
        crawl_status="ok",
        final_url="https://www.example.com/",
    )
    issue = OnsiteIssue(
        id="i2",
        tenant_id="t1",
        page_id=page.id,
        category="schema",
        title="缺少 JSON-LD / schema",
        severity="high",
        risk="high",
        status="open",
        proposed_change="",
    )
    note = issue_customer_note(issue, page)
    assert "https://www.example.com/" in note
    assert "问题：页面缺少给搜索看的说明" in note
    assert "请做：起草页面说明标记" in note
    assert ONSITE_CUSTOMER_CLOSE in note


def test_weekly_onsite_picks_one_issue_per_page_prefers_urgent() -> None:
    home = SitePage(id="p-home", tenant_id="t1", path="/", title="Home")
    product = SitePage(id="p-pro", tenant_id="t1", path="/products/a", title="A")
    about = SitePage(id="p-about", tenant_id="t1", path="/about", title="About")
    extra = SitePage(id="p-blog", tenant_id="t1", path="/blog", title="Blog")
    issues = [
        OnsiteIssue(id="l1", tenant_id="t1", page_id=home.id, category="image", title="图片没有文字说明", severity="low", status="open"),
        OnsiteIssue(id="c1", tenant_id="t1", page_id=home.id, category="tdk", title="首页标题过长", severity="critical", status="open"),
        OnsiteIssue(id="c2", tenant_id="t1", page_id=home.id, category="heading", title="页面缺少主标题", severity="critical", status="open"),
        OnsiteIssue(id="h1", tenant_id="t1", page_id=product.id, category="content", title="正文太少，买家看不够", severity="high", status="open"),
        OnsiteIssue(id="h2", tenant_id="t1", page_id=about.id, category="schema", title="缺少 JSON-LD / schema", severity="high", status="open"),
        OnsiteIssue(id="l2", tenant_id="t1", page_id=extra.id, category="image", title="图片没有文字说明", severity="low", status="open"),
    ]
    picks = weekly_onsite_picks(issues)
    assert [row.id for row in picks] == ["c1", "h1", "h2"]
    assert len({row.page_id for row in picks}) == 3
    paste = weekly_onsite_paste("SNIPERS", [issue_customer_note(row, home if row.page_id == home.id else product) for row in picks[:1]])
    assert "SNIPERS 这周请改这几处" in paste
    assert ONSITE_CUSTOMER_CLOSE in paste

from tests.conftest import auth_header


def test_markdown_becomes_html_without_hash_marks() -> None:
    from app.report_export import markdown_to_report_html

    html = markdown_to_report_html(
        title="本周客户说明",
        markdown_text="# 本周客户说明\n\n## 已测事实\n\n- 官网能打开\n\n## AI建议\n\n- 先改首页标题\n",
    )
    assert "<h1>" in html
    assert "<h2>" in html
    assert "<li>" in html
    assert "官网能打开" in html
    assert "# 本周客户说明" not in html
    assert "## 已测事实" not in html
    assert "- 官网能打开" not in html
    assert "G-Snipers 海外版" in html


def test_customer_brief_pdf_uses_html_renderer(client, demo_user, monkeypatch) -> None:
    from app import report_export

    monkeypatch.setattr(report_export, "html_to_pdf", lambda html: b"%PDF-1.4 mock")
    headers = auth_header(client)
    res = client.get("/api/dashboard/customer-brief.pdf", headers=headers)
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("application/pdf")
    assert res.content.startswith(b"%PDF-1.4")
    assert "filename*=UTF-8''" in res.headers["content-disposition"]


def test_onsite_and_geo_pdf_endpoints(client, demo_user, monkeypatch) -> None:
    from app import report_export

    monkeypatch.setattr(report_export, "html_to_pdf", lambda html: b"%PDF-1.4 mock")
    headers = auth_header(client)
    onsite = client.get("/api/onsite/report.pdf", headers=headers)
    geo = client.get("/api/geo/report.pdf", headers=headers)
    assert onsite.status_code == 200, onsite.text
    assert geo.status_code == 200, geo.text
    assert onsite.content.startswith(b"%PDF-1.4")
    assert geo.content.startswith(b"%PDF-1.4")

"""Turn existing report markdown into a customer-facing PDF. Diagnosis stays untouched."""

from __future__ import annotations

from urllib.parse import quote

import markdown
from fastapi.responses import Response

REPORT_STYLE = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
html, body { margin: 0; padding: 0; }
body {
  color: #0f172a;
  font-family: "Noto Sans CJK SC", "Noto Sans CJK", "Source Han Sans SC",
    "Microsoft YaHei", "PingFang SC", "Noto Sans", sans-serif;
  font-size: 12.5pt;
  line-height: 1.65;
}
.header { border-bottom: 2px solid #1d4ed8; padding-bottom: 10px; margin-bottom: 18px; }
.kicker { color: #1d4ed8; font-size: 10pt; font-weight: 700; letter-spacing: 0.04em; }
h1 { font-size: 20pt; margin: 6px 0 0; line-height: 1.3; }
h2 { font-size: 13.5pt; margin: 22px 0 8px; color: #1e3a8a; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
h3 { font-size: 12pt; margin: 16px 0 6px; }
p { margin: 0 0 10px; }
ul, ol { margin: 0 0 12px; padding-left: 1.3em; }
li { margin: 0 0 4px; }
strong { font-weight: 700; }
.footer { margin-top: 28px; padding-top: 10px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 9.5pt; }
"""


def markdown_to_report_html(*, title: str, markdown_text: str) -> str:
    body = markdown.markdown(
        markdown_text,
        extensions=["sane_lists", "tables", "nl2br"],
        output_format="html5",
    )
    safe_title = title.replace("<", "").replace(">", "")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{safe_title}</title>
  <style>{REPORT_STYLE}</style>
</head>
<body>
  <div class="header">
    <div class="kicker">G-Snipers 海外版 · 给客户的说明</div>
  </div>
  {body}
  <div class="footer">只写已经检查到的事实。尚未检查的不会写成 0，也不会编造排名或推荐。</div>
</body>
</html>
"""


def html_to_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except Exception as exc:  # ImportError / OSError when system libs are missing
        raise RuntimeError("PDF 渲染不可用。服务器镜像需要安装 WeasyPrint 依赖。") from exc
    return HTML(string=html).write_pdf()


def pdf_response(*, title: str, markdown_text: str, filename: str) -> Response:
    html = markdown_to_report_html(title=title, markdown_text=markdown_text)
    data = html_to_pdf(html)
    ascii_name = "report.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}",
        },
    )

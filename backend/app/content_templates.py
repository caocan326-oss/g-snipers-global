"""Local outline / draft / meta templates.

This slice does not call Google, SERP, or third-party content APIs.
Account managers edit the generated text before any human confirm-to-ready step.
"""

from __future__ import annotations


def generate_outline(keyword: str, locale: str) -> str:
    lang = locale.split("-")[0].lower()
    if lang == "zh":
        return (
            f"# {keyword}\n\n"
            f"## 读者要解决的问题\n"
            f"- 用一句话说明 {keyword} 适合谁、不适合谁\n"
            f"- 列出购买或使用前必须确认的 3 个条件\n\n"
            f"## 核心要点（H2）\n"
            f"### 如何选择 / 评估\n"
            f"### 落地步骤\n"
            f"### 常见误区\n\n"
            f"## 本地化注意\n"
            f"- 法规、电源/规格、售后渠道\n\n"
            f"## FAQ\n"
            f"- 安装要多久？\n"
            f"- 和本地主流方案差在哪？\n"
        )
    if lang == "ja":
        return (
            f"# {keyword}\n\n"
            f"## この記事で分かること\n"
            f"- {keyword} の対象読者と前提条件\n\n"
            f"## 選び方\n"
            f"## 導入手順\n"
            f"## よくある失敗\n"
            f"## よくある質問\n"
        )
    if lang == "de":
        return (
            f"# {keyword}\n\n"
            f"## Worum es geht\n"
            f"- Für wen {keyword} geeignet ist\n\n"
            f"## Auswahlkriterien\n"
            f"## Umsetzungsschritte\n"
            f"## Häufige Fehler\n"
            f"## FAQ\n"
        )
    return (
        f"# {keyword}\n\n"
        f"## Who this is for\n"
        f"- State the job-to-be-done for {keyword}\n"
        f"- List 3 checks before buying or installing\n\n"
        f"## How to evaluate options\n"
        f"## Step-by-step\n"
        f"## Mistakes to avoid\n"
        f"## Local considerations (warranty, voltage, support)\n"
        f"## FAQ\n"
    )


def generate_draft(keyword: str, locale: str, outline: str) -> str:
    lang = locale.split("-")[0].lower()
    if lang == "zh":
        return (
            f"{keyword}：给出海团队的可改稿正文\n\n"
            f"这是工作台根据大纲生成的初稿，不是终稿，也未对任何站点发布。"
            f"请客户经理按目标市场改写语气、规格与合规表述。\n\n"
            f"{outline}\n\n"
            f"开篇先回答「这是什么、给谁用、为什么现在看」。"
            f"中间按大纲逐节展开，每节先给结论再给步骤。"
            f"结尾放下一步行动（询盘、下载规格书或预约安装）。\n"
        )
    if lang == "ja":
        return (
            f"{keyword} の下書きです。公開前に必ず人が確認してください。\n\n"
            f"{outline}\n\n"
            f"導入で結論を述べ、各見出しで手順と注意点を具体化します。\n"
        )
    if lang == "de":
        return (
            f"Entwurf zu {keyword}. Nicht veröffentlichen, bevor ein Mensch bestätigt.\n\n"
            f"{outline}\n\n"
            f"Beginnen Sie mit der Antwort, dann Schritte, dann lokale Hinweise.\n"
        )
    return (
        f"Draft for “{keyword}”. This is a starting manuscript for the account manager, "
        f"not a live page.\n\n"
        f"{outline}\n\n"
        f"Lead with the answer, then walk through evaluation, steps, and local caveats. "
        f"Close with a single next action (inquiry or spec download).\n"
    )


def generate_meta(keyword: str, locale: str, title: str) -> tuple[str, str]:
    lang = locale.split("-")[0].lower()
    if lang == "zh":
        meta_title = f"{keyword}｜选购与落地指南"
        meta_desc = (
            f"面向 {locale} 市场的 {keyword} 说明：适用场景、步骤与常见误区。"
            f"由客户经理改稿后人工确认，不会自动发布。"
        )
    elif lang == "ja":
        meta_title = f"{keyword}｜選び方と導入"
        meta_desc = f"{keyword} の対象、手順、注意点。公開前に担当者が確認します。"
    elif lang == "de":
        meta_title = f"{keyword} | Auswahl und Umsetzung"
        meta_desc = f"Leitfaden zu {keyword}: Eignung, Schritte, typische Fehler. Freigabe nur durch Menschen."
    else:
        meta_title = f"{keyword} | How to choose and get started"
        meta_desc = (
            f"A {locale} page on {keyword}: who it is for, the steps, and mistakes to avoid. "
            f"Account manager edits; nothing auto-publishes."
        )
    return meta_title[:60], meta_desc[:160]

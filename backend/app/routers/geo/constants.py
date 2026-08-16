RECORDED_OBS = {"mentioned", "not_mentioned", "cited", "verified"}
EVIDENCE_LABELS = {
    "none": "无证据",
    "mentioned": "正文提及",
    "cited": "引用待核验",
    "verified": "引用已核验",
}
PROTOCOL_VERSION = "geo-test-protocol-v1"
EXPORT_B2B_PACK_ID = "export-b2b-observation-v1"
PROMPT_TYPES = {"branded", "category", "competitor", "task", "custom"}
EXPORT_B2B_PROMPTS = [
    ("EX-EN-B01", "branded", "en", "What is {Brand} and what does the company do?"),
    ("EX-EN-B02", "branded", "en", "What is {Brand} best known for in {ProductCategory}?"),
    ("EX-EN-B03", "branded", "en", "Who should buy from {Brand}? What kind of buyers fit best?"),
    ("EX-EN-B04", "branded", "en", "What certifications or quality standards is {Brand} associated with?"),
    ("EX-EN-B05", "branded", "en", "Where is {Brand} based and which markets does it export to?"),
    ("EX-EN-C01", "category", "en", "Best {ProductCategory} manufacturers for export to {Country}"),
    ("EX-EN-C02", "category", "en", "How to choose a reliable {ProductCategory} supplier for B2B import?"),
    ("EX-EN-C03", "category", "en", "Key quality checks when sourcing {ProductCategory} from overseas"),
    ("EX-EN-C04", "category", "en", "{ProductCategory} specifications buyers usually request in RFQs"),
    ("EX-EN-C05", "category", "en", "Difference between industrial-grade and cheap {ProductCategoryAlt}"),
    ("EX-EN-C06", "category", "en", "Top considerations for OEM / ODM {ProductCategory} partnerships"),
    ("EX-EN-C07", "category", "en", "How are {ProductCategory} typically certified for {Country} market entry?"),
    ("EX-EN-C08", "category", "en", "Common failure modes or quality risks in {ProductCategory} supply chains"),
    ("EX-EN-P01", "competitor", "en", "{Brand} vs {Competitor} for {ProductCategory} - how should a buyer compare them?"),
    ("EX-EN-P02", "competitor", "en", "Alternatives to {Competitor} for {ProductCategory} export buyers"),
    ("EX-EN-P03", "competitor", "en", "Which companies are often mentioned for {ProductCategory} in {Application}?"),
    ("EX-EN-T01", "task", "en", "How should a B2B exporter structure a product page so engineers can evaluate {ProductCategory}?"),
    ("EX-EN-T02", "task", "en", "What documents should a {ProductCategory} supplier prepare for an international RFQ?"),
    ("EX-EN-T03", "task", "en", "How can a manufacturer measure whether AI search tools recommend their brand?"),
    ("EX-ZH-B01", "branded", "zh", "{Brand} 是做什么的？主要服务哪些客户？"),
    ("EX-ZH-B02", "branded", "zh", "{Brand} 在 {ProductCategory} 领域以什么闻名？"),
    ("EX-ZH-C01", "category", "zh", "出口到 {Country} 的 {ProductCategory} 供应商怎么选？"),
    ("EX-ZH-C02", "category", "zh", "进口 {ProductCategory} 时，B2B 买家通常看哪些质量与认证？"),
    ("EX-ZH-C03", "category", "zh", "{ProductCategory} 国际询盘里常见的技术参数有哪些？"),
    ("EX-ZH-P01", "competitor", "zh", "{Brand} 和 {Competitor} 在 {ProductCategory} 上如何比较？"),
    ("EX-ZH-T01", "task", "zh", "出口型 B2B 官网产品页应具备哪些工程师可评估的信息？"),
]

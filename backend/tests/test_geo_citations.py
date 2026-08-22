from app.geo_citations import classify_citation, marketplace_urls, split_citations


def test_owned_wins_over_marketplace_host() -> None:
    assert classify_citation("https://item.jd.com/100", "ugreen.com") == "marketplace"
    assert classify_citation("https://www.ugreen.com/100w", "https://www.ugreen.com") == "owned"
    assert classify_citation("https://item.jd.com/100", "jd.com") == "owned"


def test_amazon_and_cn_shops_are_marketplace() -> None:
    assert classify_citation("https://www.amazon.com/dp/B0", "ugreen.com") == "marketplace"
    assert classify_citation("https://www.amazon.co.uk/dp/B0", "ugreen.com") == "marketplace"
    assert classify_citation("https://smile.amazon.com/dp/B0", "ugreen.com") == "marketplace"
    assert classify_citation("https://detail.tmall.com/item.htm?id=1", "ugreen.com") == "marketplace"
    assert classify_citation("https://mobile.yangkeduo.com/goods.html", "ugreen.com") == "marketplace"
    assert classify_citation("https://www.aliexpress.com/item/1.html", "ugreen.com") == "marketplace"


def test_review_and_generic_hosts_stay_other() -> None:
    assert classify_citation("https://www.globalspec.com/supplier/ugreen", "ugreen.com") == "other"
    assert classify_citation("https://industry.example.org/list", "example.com") == "other"
    assert classify_citation("https://amazing.com/not-amazon", "ugreen.com") == "other"


def test_split_keeps_owned_out_of_third_party() -> None:
    owned, marketplace, other = split_citations(
        [
            "https://www.ugreen.com/charger",
            "https://item.jd.com/123",
            "https://www.reddit.com/r/UsbCHardware",
            "https://item.jd.com/123",
        ],
        "ugreen.com",
    )
    assert owned == ["https://www.ugreen.com/charger"]
    assert marketplace == ["https://item.jd.com/123"]
    assert other == ["https://www.reddit.com/r/UsbCHardware"]
    assert marketplace_urls(marketplace + other) == marketplace

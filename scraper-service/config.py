MAGAZINE = {
    "PC Garage": {
        "url_search": "https://www.pcgarage.ro/cauta/{query}",
        "selector_card": ".product_box_container",
        "selector_titlu": ".my-name a",
        "selector_pret": ".price",
        "selector_link": ".my-name a",
    },
    "Vexio": {
        "url_search": "https://www.vexio.ro/cauta/{query}/",
        "selector_card": ".product-box",
        "selector_titlu": "h2.name a",
        "selector_pret": ".price",
        "selector_link": "h2.name a",
    },
    "Cel.ro": {
        "url_search": "https://www.cel.ro/cauta/{query}/",
        "selector_card": ".productListing-data",
        "selector_titlu": ".productTitle a",
        "selector_pret": ".price",
        "selector_link": ".productTitle a",
        "stoc_text_epuizat": "stoc epuizat",
    },
}
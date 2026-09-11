"""Built-in whitelist for brands, formats, abbreviations and identifiers."""

BASE_EXCEPTIONS = {
    # Common brands and product names.
    "gorenje", "bosch", "samsung", "lg", "apple", "philips", "siemens",
    "haier", "beko", "miele", "electrolux", "aeg", "xiaomi", "google",
    "sony", "panasonic", "toshiba", "asus", "lenovo", "hp", "huawei",
    "honor", "tesla", "ikea", "whirlpool", "indesit", "karcher", "tefal",
    "braun", "nespresso", "dolce gusto", "airpods", "iphone", "ipad",
    "simplicity", "ora-ito", "karim rashid",

    # File formats and technical extensions.
    "jpg", "jpeg", "png", "gif", "svg", "webp", "avif", "mp4", "mp3", "avi", "mov", "webm",
    "pdf", "doc", "docx", "xls", "xlsx", "zip", "rar", "csv", "json", "xml",
    "url", "http", "https", "api", "id", "qr", "pin", "sim", "usb", "type-c", "micro-usb",
    "hdmi", "led", "oled", "qled", "hd", "full hd", "4k", "8k", "wi-fi", "bluetooth",
    "nfc", "gps", "rgb", "cmyk", "css", "html", "seo", "faq", "vip",
    "top", "new", "sale", "ok", "datamatrix", "gtin", "sscc", "gln",
    "ооо", "ип", "инн", "огрн",

    # Technical specifications, units, standards.
    "kwh", "w", "kw", "v", "a", "ma", "hz", "khz", "mhz", "ghz", "db", "rpm",
    "bar", "pa", "din", "ip20", "ip44", "ip65", "ip68", "iso", "ce",
    "com", "ru", "net", "org", "info", "by", "kz", "рф",

    # Social networks and messengers.
    "instagram", "youtube", "facebook", "telegram", "whatsapp", "viber", "tiktok", "vk",

    # Payment and operating systems.
    "visa", "mastercard", "mir", "paypal", "android", "ios", "windows", "macos",

    # Common appliance / UI modes left in Latin script.
    "tv", "smart", "eco", "inverter", "wifi", "no frost", "total no frost",
    "hi-light", "aqua stop", "aquastop", "touch control", "soft close",
    "online", "outlet", "premium", "alt", "title", "recaptcha",
}

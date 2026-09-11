"""Built-in whitelist for brands, formats, abbreviations and identifiers."""

BASE_EXCEPTIONS = {
    # Бренды и производители
    "gorenje", "bosch", "samsung", "lg", "apple", "philips", "siemens",
    "haier", "beko", "miele", "electrolux", "aeg", "xiaomi", "google",
    "sony", "panasonic", "toshiba", "asus", "lenovo", "hp", "huawei",
    "honor", "tesla", "ikea", "whirlpool", "indesit", "karcher", "tefal",
    "braun", "nespresso", "dolce gusto", "airpods", "iphone", "ipad",
    "simplicity", "ora-ito", "karim rashid",

    # Форматы файлов и медиа-расширения
    "jpg", "jpeg", "png", "gif", "svg", "webp", "avif", "ico",
    "mp4", "mp3", "avi", "mov", "webm", "mkv", "flv",
    "pdf", "doc", "docx", "xls", "xlsx", "zip", "rar", "csv", "json", "xml",
    "css", "js", "woff", "woff2", "ttf", "eot",

    # Технические протоколы, разъемы и стандарты
    "url", "http", "https", "api", "id", "qr", "pin", "sim", "usb", "type-c", "micro-usb",
    "hdmi", "vga", "dvi", "displayport", "lan", "aux",
    "led", "oled", "qled", "hd", "full hd", "4k", "8k", "wi-fi", "bluetooth",
    "nfc", "gps", "rgb", "cmyk", "html", "seo", "faq", "vip",
    "top", "new", "sale", "ok", "datamatrix", "gtin", "sscc", "gln",
    "ооо", "ип", "инн", "огрн",

    # Единицы измерений и физические величины
    "kwh", "w", "kw", "v", "a", "ma", "hz", "khz", "mhz", "ghz",
    "db", "rpm", "bar", "pa", "kpa", "btu", "din",
    "kg", "g", "mg", "l", "ml", "mm", "cm", "m",
    "ip20", "ip44", "ip65", "ip68", "iso", "ce",

    # Доменные зоны
    "com", "ru", "net", "org", "info", "by", "kz", "рф",

    # Социальные сети и мессенджеры
    "instagram", "youtube", "facebook", "telegram", "whatsapp", "viber", "tiktok", "vk",

    # Платежные и операционные системы
    "visa", "mastercard", "mir", "paypal", "android", "ios", "windows", "macos", "linux",

    # Характеристики бытовой техники и элементы интерфейса
    "tv", "smart", "eco", "inverter", "wifi", "no frost", "total no frost",
    "hi-light", "aqua stop", "aquastop", "touch control", "soft close",
    "child lock", "super cool", "super freeze", "fast freeze",
    "online", "outlet", "premium", "alt", "title", "recaptcha",
}

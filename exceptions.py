"""Built-in whitelist for brands, formats, abbreviations and identifiers."""

BASE_EXCEPTIONS = {
    # Сквозные элементы шаблона сети, подвал и юридические данные
    "kvalitet trade", "max max", "recaptcha", "design&technologies",
    "consumer electronics", "appliances", "artplay", "art play",
    "rutube", "rutube rutube", "max max rutube rutube", "cookie", "cookies",
    "email", "shop", "business", "company", "kvalitet",

    # Бренды и производители техники
    "gorenje", "miele", "bosch", "samsung", "lg", "apple", "philips", "siemens",
    "haier", "beko", "electrolux", "aeg", "xiaomi", "google", "sony",
    "panasonic", "toshiba", "asus", "lenovo", "hp", "huawei", "honor",
    "whirlpool", "indesit", "karcher", "tefal", "braun", "nespresso",
    "simplicity", "ora-ito", "karim rashid",

    # Фирменные технологии и линейки MIELE
    "directsensor", "fragrancedos", "powerdisk", "profieco", "autoopen",
    "powerflex", "airclean", "addload", "stop&go", "onetouch", "ecodry",
    "ecopower", "quickpowerwash", "capdosing", "vitroline", "aromaticsystem",
    "dynamicdrive", "easyclick", "autoclean", "easycontrol", "booster",
    "diamondfinish", "comfortclean", "brilliantlight", "twinflow",
    "comfortsize", "perfectclean", "pyrofit", "wireless food probe",
    "foodview", "tastecontrol", "flexiclip", "hydroclean", "softclose",
    "nofrost", "mtouch", "powerwash", "perfectfresh", "multisteam",
    "monosteam", "sous-vide", "ecospeed", "artline", "profiline",
    "con@ctivity", "con", "ctivity", "immer besser",

    # Фирменные технологии GORENJE / BOSCH
    "crispzone", "silvermatte", "aquaclean", "supersize", "multibox",
    "ionair", "powerboost", "zerozone", "frostless", "gentleclose",
    "simpleslide", "cleanzone", "multiclack", "totalweight", "carbotech",
    "allergycare", "stainexpert", "perfectgrill", "moodlite", "iq sensor",
    "homechef", "no frost", "total no frost", "hi-light", "aqua stop",
    "aquastop", "touch control", "soft close", "child lock", "super cool",
    "super freeze", "fast freeze", "adapttech", "dynamooling", "inverterpowerdrive",
    "ecosilence drive", "home connect", "activewater", "varioflex", "perfectdry",

    # Цветовые решения и серии
    "pearl beige", "obsidian black", "graphite grey", "brilliant white",
    "clean steel", "edst", "edition 125", "active", "gala ed", "havana brown",

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

    # Общие термины каталога
    "tv", "smart", "eco", "inverter", "wifi", "online", "outlet", "premium", "alt", "title", "placeholder",
}

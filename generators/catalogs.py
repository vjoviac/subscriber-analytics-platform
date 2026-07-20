PLANS = [
    "Unlimited",
    "Premium",
    "Standard",
    "Prepaid"
]

APPLICATION_CATALOG = [
    {
        "application_id": "app-001",
        "name": "YouTube",
        "category": "Video Streaming",
    },
    {
        "application_id": "app-002",
        "name": "Netflix",
        "category": "Video Streaming",
    },
    {
        "application_id": "app-003",
        "name": "TikTok",
        "category": "Social Media",
    },
    {
        "application_id": "app-004",
        "name": "WhatsApp",
        "category": "Messaging",
    },
    {
        "application_id": "app-005",
        "name": "Instagram",
        "category": "Social Media",
    },
    {
        "application_id": "app-006",
        "name": "Spotify",
        "category": "Audio Streaming",
    },
    {
        "application_id": "app-007",
        "name": "Zoom",
        "category": "Real-Time Communication",
    },
]

APPLICATION_TRAFFIC_PROFILES = {
    "app-001": {
        "bytes_dl_range": (5_000_000, 50_000_000),
        "bytes_ul_range": (100_000, 2_000_000),
    },
    "app-002": {
        "bytes_dl_range": (10_000_000, 80_000_000),
        "bytes_ul_range": (100_000, 1_500_000),
    },
    "app-003": {
        "bytes_dl_range": (3_000_000, 30_000_000),
        "bytes_ul_range": (200_000, 3_000_000),
    },
    "app-004": {
        "bytes_dl_range": (50_000, 2_000_000),
        "bytes_ul_range": (50_000, 1_500_000),
    },
    "app-005": {
        "bytes_dl_range": (1_000_000, 20_000_000),
        "bytes_ul_range": (200_000, 4_000_000),
    },
    "app-006": {
        "bytes_dl_range": (500_000, 8_000_000),
        "bytes_ul_range": (50_000, 500_000),
    },
    "app-007": {
        "bytes_dl_range": (1_000_000, 15_000_000),
        "bytes_ul_range": (1_000_000, 12_000_000),
    },
}

RAT_TYPES = [
    "4G",
    "5G",
    "WiFi"
]

CITIES = [
    "Ciudad de México",
    "Guadalajara",
    "Monterrey",
    "Puebla",
    "Querétaro"
]

DEVICE_CATALOG = [
    {
        "tac": "35693803",
        "vendor": "Samsung",
        "model": "Galaxy S24",
        "os": "Android",
    },
    {
        "tac": "35123456",
        "vendor": "Samsung",
        "model": "Galaxy A55",
        "os": "Android",
    },
    {
        "tac": "35209900",
        "vendor": "Apple",
        "model": "iPhone 15",
        "os": "iOS",
    },
    {
        "tac": "35733109",
        "vendor": "Apple",
        "model": "iPhone 14",
        "os": "iOS",
    },
    {
        "tac": "86423006",
        "vendor": "Xiaomi",
        "model": "Redmi Note 13",
        "os": "Android",
    },
]

NETWORK_CELLS = [
    {
        "cell_id": "33402056012345",
        "city": "Ciudad de México",
        "state": "Ciudad de México",
        "technology": "5G",
    },
    {
        "cell_id": "33402056012346",
        "city": "Ciudad de México",
        "state": "Ciudad de México",
        "technology": "4G",
    },
    {
        "cell_id": "33402056022345",
        "city": "Guadalajara",
        "state": "Jalisco",
        "technology": "5G",
    },
    {
        "cell_id": "33402056022346",
        "city": "Guadalajara",
        "state": "Jalisco",
        "technology": "4G",
    },
    {
        "cell_id": "33402056032345",
        "city": "Monterrey",
        "state": "Nuevo León",
        "technology": "5G",
    },
    {
        "cell_id": "33402056042345",
        "city": "Puebla",
        "state": "Puebla",
        "technology": "4G",
    },
    {
        "cell_id": "33402056052345",
        "city": "Querétaro",
        "state": "Querétaro",
        "technology": "4G",
    },
]

NETWORK_QUALITY_PROFILES = {
    "4G": {
        "latency_ms_range": (30, 100),
        "packet_loss_pct_range": (0.1, 2.0),
    },
    "5G": {
        "latency_ms_range": (10, 50),
        "packet_loss_pct_range": (0.0, 1.0),
    },
}
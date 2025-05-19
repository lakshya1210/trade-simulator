"""

Configuration settings for the trade simulator.
"""

# WebSocket endpoint
WEBSOCKET_URL = "wss://ws.okx.com/ws/v5/public"
# Default input parameters
DEFAULT_EXCHANGE = "OKX"
DEFAULT_ASSET = "BTC-USDT"
DEFAULT_ORDER_TYPE = "market"
DEFAULT_QUANTITY = 100  # USD equivalent
DEFAULT_VOLATILITY = 0.01  # Default volatility, can be updated from exchange data
DEFAULT_FEE_TIER = "Tier 1"  # Default fee tier based on OKX documentation

# OKX fee structure (based on their documentation)
FEE_TIERS = {
    "Tier 1": {"maker": 0.0008, "taker": 0.001},
    "Tier 2": {"maker": 0.0006, "taker": 0.0008},
    "Tier 3": {"maker": 0.0004, "taker": 0.0006},
    "Tier 4": {"maker": 0.0002, "taker": 0.0004},
    "Tier 5": {"maker": 0.0000, "taker": 0.0002},
}

# Almgren-Chriss model default parameters
AC_PARAMETERS = {
    "market_impact_factor": 0.1,
    "volatility_factor": 0.3,
    "risk_aversion": 1.0,
}

# UI settings
UI_REFRESH_RATE_MS = 500  # Update UI every 500ms

# Logging configuration
LOG_LEVEL = "INFO"

# Available spot assets for OKX
AVAILABLE_ASSETS = [
    "BTC-USDT",
    "ETH-USDT",
    "SOL-USDT",
    "XRP-USDT",
    "BNB-USDT",
]

# Order types
ORDER_TYPES = ["market", "limit"]

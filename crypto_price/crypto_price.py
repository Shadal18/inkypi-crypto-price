from plugins.base_plugin.base_plugin import BasePlugin
from datetime import datetime
import requests


def format_with_commas(value):
    try:
        return "{:,.2f}".format(float(value))
    except (ValueError, TypeError):
        return str(value)


def format_date_mmddyyyy(value):
    try:
        timestamp = int(value)
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%m/%d/%Y %H:%M:%S")
    except Exception:
        return str(value)


def split_symbol_pair(symbol):
    symbol = (symbol or "").upper().strip()

    known_quotes = [
        "USDT", "USDC", "BUSD", "DAI", "TUSD",
        "USD", "BTC", "ETH", "EUR", "GBP"
    ]

    for quote in known_quotes:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            base = symbol[:-len(quote)]
            return base, quote

    if len(symbol) >= 7:
        return symbol[:-4], symbol[-4:]
    if len(symbol) >= 6:
        return symbol[:-3], symbol[-3:]

    return symbol, ""


class CryptoPrice(BasePlugin):
    def generate_image(self, settings, device_config):
        symbol = (settings.get("symbol") or "BTCUSD").strip().upper()
        title = (settings.get("title") or "").strip() or "Crypto Price"

        if not symbol or len(symbol) < 6:
            raise RuntimeError("Please specify a valid crypto symbol pair such as BTCUSD or BTCUSDT.")

        api_key = device_config.load_env_key("API_NINJAS_KEY")
        if not api_key:
            raise RuntimeError("API Ninjas API key not configured.")

        api_url = f"https://api.api-ninjas.com/v1/cryptoprice?symbol={symbol}"
        headers = {"X-Api-Key": api_key}

        try:
            response = requests.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            content = e.response.text if e.response is not None else "No response content"
            status_code = e.response.status_code if e.response is not None else "unknown"
            raise RuntimeError(f"HTTP error {status_code}: {content}") from e
        except requests.exceptions.Timeout as e:
            raise RuntimeError("Request timed out trying to fetch crypto price data.") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Network or connection error: {str(e)}") from e

        try:
            data = response.json()
        except ValueError as e:
            raise RuntimeError("Failed to parse response as JSON.") from e

        if not isinstance(data, dict) or "price" not in data:
            raise RuntimeError(f"Unexpected crypto price data format or no data for symbol: {symbol}")

        price_raw = data.get("price")
        timestamp_raw = data.get("timestamp", "N/A")

        price_formatted = format_with_commas(price_raw)
        timestamp_formatted = format_date_mmddyyyy(timestamp_raw)

        base_symbol, quote_symbol = split_symbol_pair(symbol)

        width, height = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            width, height = height, width

        return self.render_image(
            dimensions=(width, height),
            html_file="crypto_price.html",
            css_file="crypto_price.css",
            template_params={
                "title": title,
                "symbol": symbol,
                "base_symbol": base_symbol,
                "quote_symbol": quote_symbol,
                "price": price_formatted,
                "timestamp": timestamp_formatted,
                "plugin_settings": settings,
            },
        )

    def generate_settings_template(self):
        template_params = super().generate_settings_template()
        template_params["style_settings"] = True
        template_params["symbol"] = {
            "required": True,
            "description": "Crypto symbol pair",
            "example": "BTCUSD or BTCUSDT",
        }
        template_params["title"] = {
            "required": False,
            "description": "Custom header text",
            "example": "Crypto Price",
        }
        return template_params
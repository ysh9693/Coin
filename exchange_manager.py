import ccxt
import pandas as pd

class ExchangeManager:
    def __init__(self):
        self.exchange = None
        self.exchange_id = None
    
    def connect(self, exchange_id, api_key, secret_key):
        """
        Connect to a specific exchange.
        """
        try:
            self.exchange_id = exchange_id.lower()
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'apiKey': api_key,
                'secret': secret_key,
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            # Verify connection by fetching balance (lightweight check)
            self.exchange.fetch_balance()
            return True, f"Connected to {exchange_id} successfully."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def fetch_balance(self, ticker=None):
        """
        Fetch balance. If ticker is provided, returns free balance for that currency.
        """
        if not self.exchange:
            return None
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            print(f"Error fetching balance: {e}")
            return None

    def fetch_current_price(self, symbol):
        """
        Fetch current price (ticker) for a symbol.
        """
        if not self.exchange:
            return None
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            print(f"Error fetching price: {e}")
            return None

    def create_market_buy_order(self, symbol, cost):
        """
        Create a market buy order.
        For Upbit/Bithumb, we often want to specify 'cost' (KRW amount) rather than quantity.
        """
        if not self.exchange:
            return False, "Not connected"
        try:
            # 1. Try CCXT's unified create_market_buy_order with cost params
            params = {}
            amount = 0
            
            # Upbit specific: requires cost in params for market buy
            if self.exchange_id == 'upbit':
                params['cost'] = cost
                # amount can be None for Upbit market buy if cost is provided in params
                order = self.exchange.create_order(symbol, 'market', 'buy', None, price=None, params=params)
                return True, order
            
            # General fallback: Calculate amount based on price
            price = self.fetch_current_price(symbol)
            if not price:
                return False, "Could not fetch price to calculate amount"
                
            amount = cost / price
            order = self.exchange.create_market_buy_order(symbol, amount)
            return True, order
        except Exception as e:
            return False, str(e)

    def create_market_sell_order(self, symbol, amount):
        """
        Create a market sell order.
        """
        if not self.exchange:
            return False, "Not connected"
        try:
            order = self.exchange.create_market_sell_order(symbol, amount)
            return True, order
        except Exception as e:
            return False, str(e)

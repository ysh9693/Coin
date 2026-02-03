import pandas as pd
from datetime import datetime

class BitSplitStrategy:
    def __init__(self, exchange_manager):
        self.ex = exchange_manager
        self.active = False
        self.splits = []  # List of dictionaries representing each split
        self.logs = []    
        self.dry_run = True
        
        # Strategy Parameters
        self.symbol = ""
        self.total_slots = 10
        self.investment_per_slot = 0.0
        self.start_price = 0.0
        self.gap_percent = 0.01  # 1% = 0.01
        self.target_return = 0.01 # 1% = 0.01

    def configure(self, symbol, total_slots, investment_per_slot, start_price, gap_percent, target_return, dry_run=True):
        self.symbol = symbol
        self.total_slots = int(total_slots)
        self.investment_per_slot = float(investment_per_slot)
        self.start_price = float(start_price)
        self.gap_percent = float(gap_percent)
        self.target_return = float(target_return)
        self.dry_run = dry_run
        
        # Initialize Splits
        self.splits = []
        for i in range(self.total_slots):
            # Calculate Buy Target Price for each split
            # Split 0: start_price
            # Split N: start_price * (1 - gap_percent)^N  <-- Simplistic geometric drop
            # Or linear drop: start_price - (gap_amount * i)?
            # WikiDocs guide implies percentage drop from PREVIOUS buy price, which is geometric.
            
            # Recalculating buy target for Split i
            # If i=0, target = start_price
            # If i>0, target = prev_buy_price * (1 - gap_percent)
            
            if i == 0:
                buy_target = self.start_price
            else:
                buy_target = self.splits[i-1]['buy_target'] * (1 - self.gap_percent)
                
            self.splits.append({
                "id": i + 1,
                "status": "READY",       # READY, BOUGHT, SOLD
                "buy_target": buy_target,
                "buy_price": 0.0,        # Actual executed price
                "quantity": 0.0,
                "sell_target": 0.0,      # Calculated after buy
                "profit_rate": 0.0
            })
            
        self.log(f"Strategy Configured: {symbol}, {total_slots} splits, Dry Run={dry_run}")
        self.active = True

    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logs.insert(0, f"[{timestamp}] {message}")
        if len(self.logs) > 100:
            self.logs = self.logs[:100]

    def run_step(self):
        """
        Execute one step of the strategy logic.
        """
        if not self.active:
            return None
        
        # 1. Fetch Current Price
        current_price = self.ex.fetch_current_price(self.symbol)
        if current_price is None:
            return "Failed to fetch price"

        # 2. Iterate through splits and check for actions
        for split in self.splits:
            
            # --- BUY LOGIC ---
            if split['status'] == 'READY':
                # If price is below buy target (with some buffer? No, simple <=)
                if current_price <= split['buy_target']:
                    self.execute_buy(split, current_price)
            
            # --- SELL LOGIC ---
            elif split['status'] == 'BOUGHT':
                # Update realtime profit rate for UI
                if split['buy_price'] > 0:
                    split['profit_rate'] = (current_price - split['buy_price']) / split['buy_price'] * 100
                    
                # Check for Sell Target
                if current_price >= split['sell_target']:
                    self.execute_sell(split, current_price)

        return current_price

    def execute_buy(self, split, price):
        qty = self.investment_per_slot / price
        
        msg = f"[Split {split['id']}] Buying..."
        if self.dry_run:
            split['status'] = 'BOUGHT'
            split['buy_price'] = price
            split['quantity'] = qty
            split['sell_target'] = price * (1 + self.target_return)
            self.log(f"🟢 [DRY RUN] BOUGHT Split {split['id']} @ {price:,.0f} (Target Sell: {split['sell_target']:,.0f})")
        else:
            # LIVE TRADING
            success, result = self.ex.create_market_buy_order(self.symbol, self.investment_per_slot)
            if success:
                split['status'] = 'BOUGHT'
                split['buy_price'] = result.get('price', price) # Use actual price if available
                split['quantity'] = result.get('amount', qty)
                split['sell_target'] = split['buy_price'] * (1 + self.target_return)
                self.log(f"🟢 [LIVE] BOUGHT Split {split['id']} @ {price:,.0f}")
            else:
                self.log(f"❌ [LIVE] BUY FAILED Split {split['id']}: {result}")

    def execute_sell(self, split, price):
        msg = f"[Split {split['id']}] Selling..."
        if self.dry_run:
            split['status'] = 'READY' # Reset to READY (Infinite Grid) or 'DONE'? Logic says infinite.
            # WikiDocs says: "When sold, it can buy again if price drops." -> Infinite.
            
            profit = (price - split['buy_price']) * split['quantity']
            self.log(f"🔴 [DRY RUN] SOLD Split {split['id']} @ {price:,.0f} (Profit: {profit:,.0f})")
            
            # Reset split
            split['buy_price'] = 0.0
            split['quantity'] = 0.0
            split['sell_target'] = 0.0
            split['profit_rate'] = 0.0
        else:
            # LIVE TRADING
            success, result = self.ex.create_market_sell_order(self.symbol, split['quantity'])
            if success:
                split['status'] = 'READY'
                self.log(f"🔴 [LIVE] SOLD Split {split['id']} @ {price:,.0f}")
                
                # Reset split
                split['buy_price'] = 0.0
                split['quantity'] = 0.0
                split['sell_target'] = 0.0
                split['profit_rate'] = 0.0
            else:
                self.log(f"❌ [LIVE] SELL FAILED Split {split['id']}: {result}")


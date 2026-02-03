import streamlit as st
import pandas as pd
import time
from exchange_manager import ExchangeManager
from strategy import BitSplitStrategy

# Page Configuration
st.set_page_config(page_title="BitSplit Bot", layout="wide")

# Initialize Session State
if 'exchange_manager' not in st.session_state:
    st.session_state.exchange_manager = ExchangeManager()
if 'strategy' not in st.session_state:
    st.session_state.strategy = BitSplitStrategy(st.session_state.exchange_manager)
if 'bot_active' not in st.session_state:
    st.session_state.bot_active = False

def main():
    st.title("🤖 BitSplit Auto-Trading Bot")

    # --- Security Check ---
    # If a password is set in secrets, require it
    if "general" in st.secrets and "password" in st.secrets["general"]:
        if "auth_status" not in st.session_state:
            st.session_state.auth_status = False
            
        if not st.session_state.auth_status:
            password_input = st.text_input("🔒 Enter App Password", type="password")
            if st.button("Login"):
                if password_input == st.secrets["general"]["password"]:
                    st.session_state.auth_status = True
                    st.rerun()
                else:
                    st.error("Incorrect Password")
            st.stop() # Stop execution here until logged in

    # --- Sidebar: Settings ---
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Exchange Settings
        st.subheader("1. Exchange")
        exchange_name = st.selectbox("Select Exchange", ["Upbit", "Bithumb", "Binance"])
        
        # Try to load keys from secrets (for cloud deployment convenience)
        # expected format in secrets.toml:
        # [exchange]
        # upbit_access = "..."
        # upbit_secret = "..."
        default_access = ""
        default_secret = ""
        
        if "exchange" in st.secrets:
            if exchange_name == "Upbit":
                default_access = st.secrets["exchange"].get("upbit_access", "")
                default_secret = st.secrets["exchange"].get("upbit_secret", "")
            elif exchange_name == "Bithumb":
                default_access = st.secrets["exchange"].get("bithumb_access", "")
                default_secret = st.secrets["exchange"].get("bithumb_secret", "")
            elif exchange_name == "Binance":
                default_access = st.secrets["exchange"].get("binance_access", "")
                default_secret = st.secrets["exchange"].get("binance_secret", "")

        api_key = st.text_input("Access Key", value=default_access, type="password")
        secret_key = st.text_input("Secret Key", value=default_secret, type="password")
        
        if st.button("Connect"):
            success, msg = st.session_state.exchange_manager.connect(exchange_name, api_key, secret_key)
            if success:
                st.success(msg)
            else:
                st.error(msg)
        
        st.markdown("---")
        
        # Strategy Settings
        st.subheader("2. Strategy")
        symbol = st.text_input("Symbol (e.g., KRW-BTC, BTC/USDT)", "KRW-BTC")
        total_slots = st.number_input("Total Splits (Max 50)", min_value=1, max_value=50, value=10)
        investment_per_slot = st.number_input("Investment per Split", min_value=0.0, value=6000.0)
        start_price = st.number_input("Start Price", min_value=0.0)
        gap_percent = st.slider("Gap % (Drop to Buy)", 0.1, 10.0, 1.0)
        target_return = st.slider("Target Return % (Rise to Sell)", 0.1, 10.0, 1.0)
        
        # Dry Run Mode
        dry_run = st.checkbox("Dry Run (Simulation Mode)", value=True)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        if col1.button("▶ START", use_container_width=True):
            st.session_state.bot_active = True
            st.session_state.strategy.configure(symbol, total_slots, investment_per_slot, start_price, gap_percent/100, target_return/100)
            st.success("Bot Started!")
            
        if col2.button("⏹ STOP", use_container_width=True):
            st.session_state.bot_active = False
            st.warning("Bot Stopped.")

    # --- Main Content ---
    
    # Dashboard stats
    col1, col2, col3 = st.columns(3)
    
    # Execute Strategy Step
    current_price = 0
    if st.session_state.bot_active:
        # Run step
        result_price = st.session_state.strategy.run_step()
        if isinstance(result_price, (int, float)):
            current_price = result_price
        
        # Auto-refresh
        time.sleep(1) 
        st.rerun()
    else:
        # If not active, just fetch price for display
        if st.session_state.exchange_manager.exchange:
            current_price = st.session_state.exchange_manager.fetch_current_price(symbol if 'symbol' in locals() else "KRW-BTC")
    
    col1.metric("Current Price", f"{current_price:,.0f}" if current_price else "Waiting...")
    col2.metric("Status", "RUNNING 🟢" if st.session_state.bot_active else "STOPPED 🔴")
    
    st.markdown("### 📊 Status by Split")
    
    # Convert strategy splits list to DataFrame
    if st.session_state.strategy.splits:
        df_splits = pd.DataFrame(st.session_state.strategy.splits)
        # Reorder/Rename for display
        display_df = df_splits[['id', 'status', 'buy_target', 'buy_price', 'quantity', 'sell_target', 'profit_rate']].copy()
        display_df.columns = ['Split #', 'Status', 'Buy Target', 'Avg Buy Price', 'Qty', 'Sell Target', 'Profit %']
        
        # Formatting
        st.dataframe(
            display_df.style.format({
                'Buy Target': '{:,.0f}',
                'Avg Buy Price': '{:,.0f}',
                'Qty': '{:.8f}',
                'Sell Target': '{:,.0f}',
                'Profit %': '{:.2f}%'
            }).map(lambda x: 'color: green' if x > 0 else 'color: red', subset=['Profit %']),
            use_container_width=True,
            height=400
        )
    else:
        st.info("Start the bot to see split status.")

    st.markdown("### 📝 Activity Log")
    log_text = "\n".join(st.session_state.strategy.logs)
    st.text_area("Log Output", log_text, height=200)


if __name__ == "__main__":
    main()

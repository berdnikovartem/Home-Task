import ccxt
import requests
import time
import math
import socket
import logging
import json
from datetime import datetime, timedelta
import threading

# ============================================
# API KEYS AND CONFIGURATIONS
# ============================================
BINANCE_API_KEY = 'pOuoRvxJeRTLqAopIxbtaviGv8HYYoW0LFopdOYTl0BwNHTSjSiuQcvl3WqHVzYa'
BINANCE_SECRET = 't8ZaCUupMLhdFDF6wqUhalpU2FU2JUMpy6RLTlbBjHfGwOHOu8NSgOXsBeTVDMvd'
TELEGRAM_TOKEN = '6697943968:AAEmrKxuDfBiDlvAjzx1gXsFUAaNaj7MmvE'
TELEGRAM_CHAT_ID = '782395586'

# ============================================
# LOGGING CONFIGURATION
# ============================================
logging.basicConfig(
    filename="bot_errors1.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ============================================
# BINANCE CLIENT SETUP
# ============================================
binance = ccxt.binance({
    'apiKey': BINANCE_API_KEY,
    'secret': BINANCE_SECRET,
    'enableRateLimit': True
})

# ============================================
# COIN CONFIGURATIONS
# ============================================
COIN_CONFIGS = {
    'SUI/USDT': {
        'amount': 2,
        'rsi_3m_threshold': 27,
        'rsi_30m_threshold': 27,
        'volume_threshold': 250000,
        'surge_multiplier': 1.65,
        'dca_levels': 7,
        'dca_percentage_drop': 0.03,
        'take_profit_percentage': 0.1,
        'extreme_volume': 3000000,
        'extreme_rsi_3m': 22,
        'hammer_shadow_multiplier_extreme': 0.55,
        'rsi_short_threshold': 70,
        'rsi30_short_threshold': 68,
        'short_percentage_rise': 0.04,
        'hedge_multiplier': 1.0
    },
    'APT/USDT': {
        'amount': 2,
        'rsi_3m_threshold': 32,
        'rsi_30m_threshold': 32,
        'volume_threshold': 80000,
        'surge_multiplier': 1.65,
        'dca_levels': 7,
        'dca_percentage_drop': 0.01,
        'take_profit_percentage': 0.1,
        'extreme_volume': 300000,
        'extreme_rsi_3m': 22,
        'hammer_shadow_multiplier_extreme': 0.55,
        'rsi_short_threshold': 70,
        'rsi30_short_threshold': 70,
        'short_percentage_rise': 0.05,
        'hedge_multiplier': 1.0
    }
}

# ============================================
# FILE PATHS
# ============================================
DCA_STATE_FILE = "C:/Users/Artem/Desktop/data1.json"
PROFIT_HISTORY_FILE = "profit_history.json"

# ============================================
# HELPER FUNCTIONS FOR STATE
# ============================================
def ensure_dca_state_keys(dca_state):
    defaults = {
        "total_amount": 0,
        "total_cost": 0,
        "dca_count": 0,
        "average_price": 0,
        "take_profit_price": 0,
        "last_buy_price": 0,
        "active": False,
        "total_short_amount": 0,
        "total_short_cost": 0,
        "short_dca_count": 0,
        "short_average_price": 0,
        "short_take_profit_price": 0,
        "last_short_price": 0,
        "active_short": False,
        "last_order_time": datetime.utcnow(),
        "last_short_order_time": datetime.utcnow(),
        "total_long_hedge_amount": 0,
        "total_long_hedge_cost": 0,
        "long_hedge_average_price": 0,
        "total_short_hedge_amount": 0,
        "total_short_hedge_cost": 0,
        "short_hedge_average_price": 0,
        "active_long_hedge": False,
        "hedge_active": False,
        "entry_price": 0
    }
    for key, default in defaults.items():
        if key not in dca_state:
            dca_state[key] = default
        else:
            if key.endswith("time") and isinstance(dca_state[key], str):
                try:
                    dca_state[key] = datetime.fromisoformat(dca_state[key])
                except Exception:
                    dca_state[key] = default
    return dca_state


def reset_long_state(dca_state):
    dca_state["leftshorthedge_amount"] = dca_state.get("total_short_hedge_amount", 0)
    dca_state["leftshorthedge_cost"] = dca_state.get("total_short_hedge_cost", 0)
    dca_state["leftshorthedge_avg"] = dca_state.get("short_hedge_average_price", 0)
    dca_state["total_amount"] = 0
    dca_state["total_cost"] = 0
    dca_state["dca_count"] = 0
    dca_state["average_price"] = 0
    dca_state["take_profit_price"] = 0
    dca_state["last_buy_price"] = 0
    dca_state["active"] = False
    dca_state["last_order_time"] = datetime.utcnow()
    dca_state["total_short_hedge_amount"] = 0
    dca_state["total_short_hedge_cost"] = 0
    dca_state["short_hedge_average_price"] = 0
    dca_state["hedge_active"] = False
    return dca_state


def reset_short_state(dca_state):
    dca_state["leftlonghedge_amount"] = dca_state.get("total_long_hedge_amount", 0)
    dca_state["leftlonghedge_cost"] = dca_state.get("total_long_hedge_cost", 0)
    dca_state["leftlonghedge_avg"] = dca_state.get("long_hedge_average_price", 0)
    dca_state["total_short_amount"] = 0
    dca_state["total_short_cost"] = 0
    dca_state["short_dca_count"] = 0
    dca_state["short_average_price"] = 0
    dca_state["short_take_profit_price"] = 0
    dca_state["last_short_price"] = 0
    dca_state["active_short"] = False
    dca_state["last_short_order_time"] = datetime.utcnow()
    dca_state["total_long_hedge_amount"] = 0
    dca_state["total_long_hedge_cost"] = 0
    dca_state["long_hedge_average_price"] = 0
    dca_state["active_long_hedge"] = False
    dca_state["hedge_active"] = False
    return dca_state

# ============================================
# STATE MANAGEMENT FUNCTIONS
# ============================================
def save_dca_state(dca_data):
    try:
        for symbol, dca_state in dca_data.items():
            for key in ("last_order_time", "last_short_order_time"):
                if key in dca_state and isinstance(dca_state[key], datetime):
                    dca_state[key] = dca_state[key].isoformat()
        with open(DCA_STATE_FILE, "w") as file:
            json.dump(dca_data, file, indent=4)
        print("DCA state saved successfully.")
    except Exception as e:
        print(f"Error saving DCA state: {e}")

def load_dca_state():
    try:
        with open(DCA_STATE_FILE, "r") as file:
            state = json.load(file)
            for symbol, dca_state in state.items():
                state[symbol] = ensure_dca_state_keys(dca_state)
            return state
    except FileNotFoundError:
        print("DCA state file not found. Starting fresh.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return {}
    except Exception as e:
        print(f"Error loading DCA state: {e}")
        return {}

active_dca_states = load_dca_state()

# ============================================
# PROFIT HISTORY FUNCTIONS
# ============================================
def load_profit_history():
    try:
        with open(PROFIT_HISTORY_FILE, "r") as f:
            history = json.load(f)
            return history
    except Exception:
        print("Profit history file not found, starting new.")
        return {}

def save_profit_history(history):
    try:
        with open(PROFIT_HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
        print("Profit history saved successfully.")
    except Exception as e:
        print(f"Error saving profit history: {e}")

profit_history = load_profit_history()


def calculate_net_profit(symbol):
    try:
        ticker = binance.fetch_ticker(symbol)
        current_price = float(ticker['last'])
    except Exception as e:
        print(f"Error fetching ticker for {symbol} in profit calculation: {e}")
        return 0
    dca_state = active_dca_states.get(symbol, {})
    total_amount = dca_state.get("total_amount", 0)
    average_price = dca_state.get("average_price", 0)
    profit_long = (current_price - average_price) * total_amount if total_amount and average_price else 0
    total_short_amount = dca_state.get("total_short_amount", 0)
    short_average_price = dca_state.get("short_average_price", 0)
    profit_short = (short_average_price - current_price) * total_short_amount if total_short_amount and short_average_price else 0
    net_profit = profit_long + profit_short
    return net_profit


def update_profit_history():
    global profit_history
    while True:
        for coin in COIN_CONFIGS:
            net_profit = calculate_net_profit(coin)
            entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "net_profit": net_profit
            }
            if coin not in profit_history:
                profit_history[coin] = []
            profit_history[coin].append(entry)
        save_profit_history(profit_history)
        time.sleep(900)

# ============================================
# NETWORK AND TELEGRAM FUNCTIONS
# ============================================
def check_network_connection(timeout=5):
    test_host = "8.8.8.8"
    test_port = 53
    try:
        with socket.create_connection((test_host, test_port), timeout):
            return True
    except (OSError, socket.timeout):
        return False


def listen_for_messages():
    global COIN_CONFIGS
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates'
    offset = None
    while True:
        if not check_network_connection():
            print("No internet connection. Retrying in 10 seconds...")
            time.sleep(10)
            continue
        time.sleep(4)
        params = {'timeout': 100}
        if offset:
            params['offset'] = offset
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result['ok']:
                for update in result['result']:
                    offset = update['update_id'] + 1
                    if 'message' in update:
                        message = update['message']
                        chat_id = message['chat']['id']
                        text = message.get('text', '')
                        if str(chat_id) == str(TELEGRAM_CHAT_ID):
                            if text.startswith("GET_CHECKERS"):
                                parts = text.split()
                                if len(parts) == 2:
                                    coin = parts[1].upper()
                                    if coin in COIN_CONFIGS:
                                        checkers = get_checkers(coin, COIN_CONFIGS[coin])
                                        send_telegram_message(f"Current checkers for {coin}:\n{checkers}")
                                    else:
                                        send_telegram_message(f"Coin {coin} not found in configuration.")
                                else:
                                    send_telegram_message("Usage: GET_CHECKERS <COIN_SYMBOL>")
                            elif text.startswith("GET_VALUES"):
                                parts = text.split()
                                if len(parts) == 2:
                                    coin = parts[1].upper()
                                    if coin in COIN_CONFIGS:
                                        values = "\n".join([f"{key}: {value}" for key, value in COIN_CONFIGS[coin].items()])
                                        send_telegram_message(f"Current values for {coin}:\n{values}")
                                    else:
                                        send_telegram_message(f"Coin {coin} not found in configuration.")
                                else:
                                    send_telegram_message("Usage: GET_VALUES <COIN_SYMBOL>")
                            else:
                                coin, config_key, value = parse_telegram_command(text)
                                if coin:
                                    try:
                                        if config_key in COIN_CONFIGS[coin]:
                                            new_value = float(value) if '.' in value else int(value)
                                            COIN_CONFIGS[coin][config_key] = new_value
                                            send_telegram_message(f"Updated {config_key} for {coin} to {new_value}.")
                                        else:
                                            send_telegram_message(f"Invalid config key: {config_key}. Available keys: {', '.join(COIN_CONFIGS[coin].keys())}.")
                                    except ValueError:
                                        send_telegram_message(f"Invalid value for {config_key}. Please provide a valid number.")
                                    except KeyError:
                                        send_telegram_message(f"Invalid coin: {coin}.")
                                else:
                                    send_telegram_message("Invalid command format.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching updates from Telegram: {e}")
            time.sleep(10)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(10)


def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Error sending telegram message: {e}")

# ============================================
# UTILITY FUNCTIONS
# ============================================
def fetch_and_check_conditions(symbol, config, is_recent_dca):
    try:
        ohlcv_3m = binance.fetch_ohlcv(symbol, timeframe='3m', limit=1000)
        ohlcv_30m = binance.fetch_ohlcv(symbol, timeframe='30m', limit=1000)
        closes_3m = [x[4] for x in ohlcv_3m]
        closes_30m = [x[4] for x in ohlcv_30m]
        rsi_3m = get_rsi(closes_3m)
        rsi_30m = get_rsi(closes_30m)
        volumes_3m = [x[5] for x in ohlcv_3m[-3:]]
        avg_volume = sum(volumes_3m[:-1]) / 2
        latest_volume = volumes_3m[-1]
        surge_condition = latest_volume >= avg_volume * config['surge_multiplier']
        volume_condition = sum(volumes_3m) >= config['volume_threshold']
        latest_candle = ohlcv_3m[-1]
        open_price = latest_candle[1]
        high_price = latest_candle[2]
        low_price = latest_candle[3]
        close_price = latest_candle[4]
        hammer_shadow_multiplier = 1.01
        if is_recent_dca and (latest_volume > config['extreme_volume'] and rsi_3m < config['extreme_rsi_3m']):
            hammer_shadow_multiplier = config.get('hammer_shadow_multiplier_extreme')
        body_size = abs(close_price - open_price)
        lower_shadow = min(open_price, close_price) - low_price
        upper_shadow = high_price - max(open_price, close_price)
        is_hammer = lower_shadow >= hammer_shadow_multiplier * body_size and upper_shadow <= body_size
        last_candle_close_time = datetime.utcfromtimestamp(latest_candle[0] / 1000)
        elapsed_time = datetime.utcnow() - last_candle_close_time
        sufficient_time_elapsed = timedelta(minutes=1) <= elapsed_time <= timedelta(minutes=3)
        return (rsi_3m < config['rsi_3m_threshold'] and
                rsi_30m < config['rsi_30m_threshold'] and
                surge_condition and
                volume_condition and
                is_hammer and
                sufficient_time_elapsed)
    except Exception as e:
        logging.error(f"Error fetching conditions for {symbol}: {e}")
        return False


def fetch_and_check_short_conditions(symbol, config, is_recent_dca):
    try:
        ohlcv_3m = binance.fetch_ohlcv(symbol, timeframe='3m', limit=1000)
        ohlcv_30m = binance.fetch_ohlcv(symbol, timeframe='30m', limit=1000)
        closes_3m = [x[4] for x in ohlcv_3m]
        closes_30m = [x[4] for x in ohlcv_30m]
        rsi_3m = get_rsi(closes_3m)
        rsi_30m = get_rsi(closes_30m)
        rsi_short_threshold = config.get('rsi_short_threshold')
        rsi30_short_threshold = config.get('rsi30_short_threshold')
        volumes_3m = [x[5] for x in ohlcv_3m[-3:]]
        avg_volume = sum(volumes_3m[:-1]) / 2
        latest_volume = volumes_3m[-1]
        surge_condition = latest_volume >= avg_volume * config['surge_multiplier']
        volume_condition = sum(volumes_3m) >= config['volume_threshold']
        latest_candle = ohlcv_3m[-1]
        open_price = latest_candle[1]
        high_price = latest_candle[2]
        low_price = latest_candle[3]
        close_price = latest_candle[4]
        body_size = abs(close_price - open_price)
        upper_shadow = high_price - max(open_price, close_price)
        lower_shadow = min(open_price, close_price) - low_price
        shooting_star_multiplier = 0.2
        is_shooting_star = upper_shadow >= shooting_star_multiplier * body_size and lower_shadow <= body_size
        last_candle_close_time = datetime.utcfromtimestamp(latest_candle[0] / 1000)
        elapsed_time = datetime.utcnow() - last_candle_close_time
        sufficient_time_elapsed = timedelta(minutes=1) <= elapsed_time <= timedelta(minutes=3)
        return (rsi_3m > rsi_short_threshold and
                rsi_30m > rsi30_short_threshold and
                surge_condition and
                volume_condition and
                is_shooting_star and
                sufficient_time_elapsed)
    except Exception as e:
        logging.error(f"Error fetching short conditions for {symbol}: {e}")
        return False


def get_checkers(symbol, config):
    try:
        ohlcv_3m = binance.fetch_ohlcv(symbol, timeframe='3m', limit=1000)
        ohlcv_30m = binance.fetch_ohlcv(symbol, timeframe='30m', limit=1000)
        closes_3m = [x[4] for x in ohlcv_3m]
        closes_30m = [x[4] for x in ohlcv_30m]
        rsi_3m = get_rsi(closes_3m)
        rsi_30m = get_rsi(closes_30m)
        volumes_3m = [x[5] for x in ohlcv_3m[-3:]]
        avg_volume = sum(volumes_3m) / len(volumes_3m)
        latest_volume = volumes_3m[-1]
        surge_condition = latest_volume >= avg_volume * config['surge_multiplier']
        latest_candle = ohlcv_3m[-1]
        open_price = latest_candle[1]
        high_price = latest_candle[2]
        low_price = latest_candle[3]
        close_price = latest_candle[4]
        body_size = abs(close_price - open_price)
        lower_shadow = min(open_price, close_price) - low_price
        upper_shadow = high_price - max(open_price, close_price)
        is_hammer = lower_shadow >= 0.2 * body_size and upper_shadow <= body_size
        return (
            f"RSI 3m: {rsi_3m}\n"
            f"RSI 30m: {rsi_30m}\n"
            f"Latest Volume: {latest_volume}\n"
            f"Average Volume (Last 3): {avg_volume}\n"
            f"Volume Surge Condition: {'Met' if surge_condition else 'Not Met'}\n"
            f"Is Hammer: {'Yes' if is_hammer else 'No'}\n"
            f"Open Price: {open_price}\n"
            f"Close Price: {close_price}\n"
            f"High Price: {high_price}\n"
            f"Low Price: {low_price}"
        )
    except Exception as e:
        logging.error(f"Error fetching checkers for {symbol}: {e}")
        return f"Error fetching checkers for {symbol}: {e}"


def parse_telegram_command(text):
    try:
        parts = text.split()
        if len(parts) == 3:
            coin, config_key, value = parts
            return coin.upper(), config_key, value
        else:
            return None, None, None
    except Exception as e:
        logging.error(f"Error parsing command: {e}")
        return None, None, None


def get_rsi(closes, period=14):
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [delta if delta > 0 else 0 for delta in deltas]
    losses = [-delta if delta < 0 else 0 for delta in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsis = []
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
        rsis.append(100 - (100 / (1 + rs)))
    return rsis[-1] if rsis else None

# --- ORDER & POSITION FUNCTIONS ---

def open_short_position(symbol, amount):
    try:
        ticker = binance.fetch_ticker(symbol)
        entry_price = ticker['last']
        order = binance.create_order(
            symbol=symbol,
            type='limit',
            side='sell',
            amount=amount,
            price=entry_price
        )
        return entry_price, True
    except Exception as e:
        send_telegram_message(f"Error opening short position for {symbol}: {e}")
        return None, False


def open_long_position(symbol, amount):
    try:
        ticker = binance.fetch_ticker(symbol)
        entry_price = ticker['last']
        order = binance.create_order(
            symbol=symbol,
            type='limit',
            side='buy',
            amount=amount,
            price=entry_price
        )
        return entry_price, True
    except Exception as e:
        send_telegram_message(f"Error opening long position for {symbol}: {e}")
        return None, False


def close_short_position(symbol, amount):
    try:
        ticker = binance.fetch_ticker(symbol)
        price = ticker['last']
        binance.create_order(
            symbol=symbol,
            type='limit',
            side='buy',
            amount=amount,
            price=price
        )
    except Exception as e:
        send_telegram_message(f"Cannot close short {symbol}: {e}")
    return True


def close_long_position(symbol, amount):
    try:
        ticker = binance.fetch_ticker(symbol)
        price = ticker['last']
        binance.create_order(
            symbol=symbol,
            type='limit',
            side='sell',
            amount=amount,
            price=price
        )
    except Exception as e:
        send_telegram_message(f"Cannot close long {symbol}: {e}")
    return True


def adjust_take_profit(symbol, amount, take_profit_price):
    try:
        open_orders = binance.fetch_open_orders(symbol)
        for order in open_orders:
            if order['side'] == 'sell' and order['type'] == 'limit' and float(order['price']) == take_profit_price:
                binance.cancel_order(order['id'], symbol)
                print(f"Cancelled conflicting take-profit order: {order['id']}")
        binance.create_order(
            symbol=symbol,
            type='limit',
            side='sell',
            amount=amount,
            price=take_profit_price
        )
        print(f"Take-profit order placed at {take_profit_price}")
    except Exception as e:
        print(f"Error setting take-profit order: {e}")
        send_telegram_message(f"Error setting take-profit for {symbol}: {e}")

# --- NEW HEDGE UPDATE FUNCTIONS ---

def update_long_hedge(symbol, config, dca_state):
    hedge_multiplier = config.get("hedge_multiplier", 1.0)
    required_hedge = math.floor((dca_state.get("total_amount", 0)) * hedge_multiplier)
    current_hedge = dca_state.get("total_short_hedge_amount", 0)
    if abs(current_hedge - required_hedge) > 1e-8:
        if current_hedge > 0:
            close_short_position(symbol, current_hedge)
        hedge_entry_price, success = open_short_position(symbol, required_hedge)
        if success and hedge_entry_price is not None:
            dca_state["total_short_hedge_amount"] = required_hedge
            dca_state["total_short_hedge_cost"] = hedge_entry_price * required_hedge
            dca_state["short_hedge_average_price"] = hedge_entry_price
            dca_state["hedge_active"] = True
            dca_state["entry_price"] = dca_state.get("last_buy_price", hedge_entry_price)
            send_telegram_message(f"Updated hedge SHORT for {symbol} to {required_hedge} at {hedge_entry_price}")
        else:
            send_telegram_message(f"Failed to open hedge SHORT for {symbol}")


def update_short_hedge(symbol, config, dca_state):
    hedge_multiplier = config.get("hedge_multiplier", 1.0)
    required_hedge = math.floor((dca_state.get("total_short_amount", 0)) * hedge_multiplier)
    current_hedge = dca_state.get("total_long_hedge_amount", 0)
    if abs(current_hedge - required_hedge) > 1e-8:
        if current_hedge > 0:
            close_long_position(symbol, current_hedge)
        hedge_entry_price, success = open_long_position(symbol, required_hedge)
        if success and hedge_entry_price is not None:
            dca_state["total_long_hedge_amount"] = required_hedge
            dca_state["total_long_hedge_cost"] = hedge_entry_price * required_hedge
            dca_state["long_hedge_average_price"] = hedge_entry_price
            dca_state["hedge_active"] = True
            dca_state["entry_price"] = dca_state.get("last_short_price", hedge_entry_price)
            send_telegram_message(f"Updated hedge LONG for {symbol} to {required_hedge} at {hedge_entry_price}")
        else:
            send_telegram_message(f"Failed to open hedge LONG for {symbol}")

# --- LONG DCA BOT WITH HEDGING ---

def start_dca_bot_with_hedge(symbol, config):
    global active_dca_states
    dca_state = active_dca_states.get(symbol, {})
    dca_state = ensure_dca_state_keys(dca_state)

    if not dca_state.get("active", False):
        last_long_price = binance.fetch_ticker(symbol)['last']
        entry_price, success = open_long_position(symbol, config['amount'])
        if not success or entry_price is None:
            send_telegram_message(f"Error: Unable to open initial LONG position for {symbol}.")
            return
        total_amount = config['amount']
        total_cost = entry_price * config['amount']
        average_price = total_cost / total_amount
        take_profit_price = average_price * (1 + config['take_profit_percentage'])
        last_long_price = entry_price
        dca_state.update({
            "total_amount": total_amount,
            "total_cost": total_cost,
            "dca_count": 1,
            "average_price": average_price,
            "take_profit_price": take_profit_price,
            "last_buy_price": last_long_price,
            "active": True,
            "last_order_time": datetime.utcnow(),
            "entry_price": entry_price
        })
        hedge_price, hedge_success = open_short_position(symbol, total_amount)
        if hedge_success and hedge_price is not None:
            dca_state.update({
                "total_short_hedge_amount": total_amount,
                "total_short_hedge_cost": hedge_price * total_amount,
                "short_hedge_average_price": hedge_price,
                "hedge_active": True
            })
            send_telegram_message(f"Opened hedge SHORT for {symbol}: {total_amount} at {hedge_price}")
        else:
            send_telegram_message(f"Failed to open initial hedge SHORT for {symbol}")
        active_dca_states[symbol] = dca_state
        save_dca_state(active_dca_states)
    else:
        last_long_price = dca_state["last_buy_price"]
        send_telegram_message(f"Resuming LONG DCA for {symbol}. State: {dca_state}")

    while True:
        time.sleep(1)
        if not check_network_connection():
            time.sleep(10)
            continue
        try:
            current_price = binance.fetch_ticker(symbol)['last']
        except Exception as e:
            send_telegram_message(f"Error fetching price for {symbol}: {e}")
            continue

        if dca_state.get("hedge_active", False):
            if current_price > dca_state.get("entry_price", last_long_price):
                close_short_position(symbol, dca_state["total_short_hedge_amount"])
                dca_state["hedge_active"] = False
                send_telegram_message(f"Closed hedge SHORT for {symbol} as price rose")
        else:
            if current_price <= dca_state.get("entry_price", last_long_price):
                hedge_price, hedge_success = open_short_position(symbol, dca_state["total_amount"])
                if hedge_success:
                    dca_state.update({
                        "total_short_hedge_amount": dca_state["total_amount"],
                        "total_short_hedge_cost": hedge_price * dca_state["total_amount"],
                        "short_hedge_average_price": hedge_price,
                        "hedge_active": True
                    })
                    send_telegram_message(f"Reopened hedge SHORT for {symbol} at {hedge_price}")

        if current_price > dca_state["take_profit_price"]:
            break

        if dca_state["dca_count"] < config['dca_levels']:
            elapsed_time_minutes = (datetime.utcnow() - dca_state["last_order_time"]).total_seconds() / 60
            is_recent_dca = elapsed_time_minutes <= 60
            percentage_drop_condition = current_price <= last_long_price * (1 - config['dca_percentage_drop'] * (dca_state["dca_count"] + 1))
            entry_conditions_met = fetch_and_check_conditions(symbol, config, is_recent_dca)
            if percentage_drop_condition and entry_conditions_met:
                last_long_price = current_price
                dca_state["dca_count"] += 1
                order_amount = config['amount']
                for _ in range(dca_state["dca_count"]):
                    order_amount = math.ceil(order_amount * 1.1)
                entry_price, success = open_long_position(symbol, order_amount)
                if not success or entry_price is None:
                    send_telegram_message(f"Error: Unable to open additional LONG for {symbol}.")
                    continue
                dca_state["total_amount"] += order_amount
                dca_state["total_cost"] += entry_price * order_amount
                dca_state["average_price"] = dca_state["total_cost"] / dca_state["total_amount"]
                dca_state["take_profit_price"] = dca_state["average_price"] * (1 + config['take_profit_percentage'])
                dca_state["last_buy_price"] = entry_price
                dca_state["last_order_time"] = datetime.utcnow()
                dca_state["entry_price"] = entry_price
                if dca_state.get("hedge_active", False):
                    close_short_position(symbol, dca_state["total_short_hedge_amount"])
                hedge_price, hedge_success = open_short_position(symbol, dca_state["total_amount"])
                if hedge_success:
                    dca_state.update({
                        "total_short_hedge_amount": dca_state["total_amount"],
                        "total_short_hedge_cost": hedge_price * dca_state["total_amount"],
                        "short_hedge_average_price": hedge_price,
                        "hedge_active": True
                    })
                    send_telegram_message(f"Adjusted hedge SHORT for {symbol} to {dca_state['total_amount']} at {hedge_price}")
                adjust_take_profit(symbol, dca_state["total_amount"], dca_state["take_profit_price"])
                active_dca_states[symbol] = dca_state
                save_dca_state(active_dca_states)

    try:
        close_long_position(symbol, dca_state["total_amount"])
        send_telegram_message(f"Closed main LONG position for {symbol} with volume {dca_state['total_amount']}")
    except Exception as e:
        send_telegram_message(f"Error closing main LONG position for {symbol}: {e}")
    if dca_state.get("hedge_active", False):
        close_short_position(symbol, dca_state["total_short_hedge_amount"])
    cycle_profit = calculate_net_profit(symbol)
    dca_state["cumulative_profit"] = dca_state.get("cumulative_profit", 0) + cycle_profit
    dca_state = reset_long_state(dca_state)
    active_dca_states[symbol] = dca_state
    save_dca_state(active_dca_states)
    send_telegram_message(f"LONG DCA strategy for {symbol} completed. Cumulative Profit: {dca_state.get('cumulative_profit', 0)}")

# --- SHORT DCA BOT WITH HEDGING ---

def start_dca_short_bot(symbol, config):
    global active_dca_states
    dca_state = active_dca_states.get(symbol, {})
    dca_state = ensure_dca_state_keys(dca_state)

    if not dca_state.get("active_short", False):
        entry_price, success = open_short_position(symbol, config['amount'])
        if not success or entry_price is None:
            send_telegram_message(f"Error: Unable to open initial SHORT for {symbol}.")
            return
        total_amount = config['amount']
        total_cost = entry_price * config['amount']
        average_price = entry_price
        take_profit_price = average_price * (1 - config['take_profit_percentage'])
        dca_state.update({
            "total_short_amount": total_amount,
            "total_short_cost": total_cost,
            "short_dca_count": 1,
            "short_average_price": average_price,
            "short_take_profit_price": take_profit_price,
            "last_short_price": entry_price,
            "active_short": True,
            "last_short_order_time": datetime.utcnow(),
            "entry_price": entry_price
        })
        hedge_price, hedge_success = open_long_position(symbol, total_amount)
        if hedge_success and hedge_price is not None:
            dca_state.update({
                "total_long_hedge_amount": total_amount,
                "total_long_hedge_cost": hedge_price * total_amount,
                "long_hedge_average_price": hedge_price,
                "hedge_active": True
            })
            send_telegram_message(f"Opened hedge LONG for {symbol}: {total_amount} at {hedge_price}")
        else:
            send_telegram_message(f"Failed to open initial hedge LONG for {symbol}")
        active_dca_states[symbol] = dca_state
        save_dca_state(active_dca_states)
    else:
        send_telegram_message(f"Resuming SHORT DCA for {symbol}. State: {dca_state}")

    while True:
        time.sleep(1)
        if not check_network_connection():
            time.sleep(10)
            continue
        try:
            current_price = binance.fetch_ticker(symbol)['last']
        except Exception as e:
            send_telegram_message(f"Error fetching price for {symbol}: {e}")
            continue

        if dca_state.get("hedge_active", False):
            if current_price < dca_state.get("entry_price", dca_state["last_short_price"]):
                close_long_position(symbol, dca_state["total_long_hedge_amount"])
                dca_state["hedge_active"] = False
                send_telegram_message(f"Closed hedge LONG for {symbol} as price dropped")
        else:
            if current_price >= dca_state.get("entry_price", dca_state["last_short_price"]):
                hedge_price, hedge_success = open_long_position(symbol, dca_state["total_short_amount"])
                if hedge_success:
                    dca_state.update({
                        "total_long_hedge_amount": dca_state["total_short_amount"],
                        "total_long_hedge_cost": hedge_price * dca_state["total_short_amount"],
                        "long_hedge_average_price": hedge_price,
                        "hedge_active": True
                    })
                    send_telegram_message(f"Reopened hedge LONG for {symbol} at {hedge_price}")

        if current_price < dca_state["short_take_profit_price"]:
            break

        if dca_state["short_dca_count"] < config['dca_levels']:
            elapsed_time_minutes = (datetime.utcnow() - dca_state["last_short_order_time"]).total_seconds() / 60
            is_recent_dca = elapsed_time_minutes <= 60
            percentage_rise_condition = current_price >= dca_state["last_short_price"] * (1 + config.get('short_percentage_rise', config.get('dca_percentage_drop', 0.01)) * (dca_state["short_dca_count"]))
            short_entry_conditions_met = fetch_and_check_short_conditions(symbol, config, is_recent_dca)
            if percentage_rise_condition and short_entry_conditions_met:
                dca_state["short_dca_count"] += 1
                short_order_amount = config['amount']
                for _ in range(dca_state["short_dca_count"]):
                    short_order_amount = math.ceil(short_order_amount * 1.1)
                entry_price, success = open_short_position(symbol, short_order_amount)
                if not success or entry_price is None:
                    send_telegram_message(f"Error: Unable to open additional SHORT for {symbol}.")
                    continue
                dca_state["total_short_amount"] += short_order_amount
                dca_state["total_short_cost"] += entry_price * short_order_amount
                dca_state["short_average_price"] = dca_state["total_short_cost"] / dca_state["total_short_amount"]
                dca_state["short_take_profit_price"] = dca_state["short_average_price"] * (1 - config['take_profit_percentage'])
                dca_state["last_short_price"] = entry_price
                dca_state["last_short_order_time"] = datetime.utcnow()
                dca_state["entry_price"] = entry_price
                if dca_state.get("hedge_active", False):
                    close_long_position(symbol, dca_state["total_long_hedge_amount"])
                hedge_price, hedge_success = open_long_position(symbol, dca_state["total_short_amount"])
                if hedge_success:
                    dca_state.update({
                        "total_long_hedge_amount": dca_state["total_short_amount"],
                        "total_long_hedge_cost": hedge_price * dca_state["total_short_amount"],
                        "long_hedge_average_price": hedge_price,
                        "hedge_active": True
                    })
                    send_telegram_message(f"Adjusted hedge LONG for {symbol} to {dca_state['total_short_amount']} at {hedge_price}")
                active_dca_states[symbol] = dca_state
                save_dca_state(active_dca_states)

    try:
        close_short_position(symbol, dca_state["total_short_amount"])
        send_telegram_message(f"Closed main SHORT position for {symbol} with volume {dca_state['total_short_amount']}")
    except Exception as e:
        send_telegram_message(f"Error closing main SHORT position for {symbol}: {e}")
    if dca_state.get("hedge_active", False):
        close_long_position(symbol, dca_state["total_long_hedge_amount"])
    cycle_profit = calculate_net_profit(symbol)
    dca_state["cumulative_profit"] = dca_state.get("cumulative_profit", 0) + cycle_profit
    dca_state = reset_short_state(dca_state)
    active_dca_states[symbol] = dca_state
    save_dca_state(active_dca_states)
    send_telegram_message(f"SHORT DCA strategy for {symbol} completed. Cumulative Profit: {dca_state.get('cumulative_profit', 0)}")

# --- MONITORING FUNCTION ---

def monitor_coin(symbol, config):
    global active_dca_states
    if symbol in active_dca_states and active_dca_states[symbol].get("active", False):
        print(f"Resuming active LONG strategy for {symbol}.")
        try:
            start_dca_bot_with_hedge(symbol, config)
        except Exception as e:
            send_telegram_message(f"Error resuming LONG DCA for {symbol}: {e}")
    if symbol in active_dca_states and active_dca_states[symbol].get("active_short", False):
        print(f"Resuming active SHORT strategy for {symbol}.")
        try:
            start_dca_short_bot(symbol, config)
        except Exception as e:
            send_telegram_message(f"Error resuming SHORT DCA for {symbol}: {e}")
    while True:
        try:
            if fetch_and_check_conditions(symbol, config, False) and not active_dca_states.get(symbol, {}).get("active", False):
                start_dca_bot_with_hedge(symbol, config)
            if fetch_and_check_short_conditions(symbol, config, False) and not active_dca_states.get(symbol, {}).get("active_short", False):
                start_dca_short_bot(symbol, config)
        except Exception as e:
            send_telegram_message(f"Error monitoring {symbol}: {e}")
        time.sleep(1)

# --- AUXILIARY TECHNICAL FUNCTIONS ---

def calculate_bollinger_bands(ohlcv, period=20):
    closes = [candle[4] for candle in ohlcv]
    sma = sum(closes[-period:]) / period
    std_dev = (sum([(close - sma) ** 2 for close in closes[-period:]]) / period) ** 0.5
    upper_band = sma + (2 * std_dev)
    lower_band = sma - (2 * std_dev)
    band_width = (upper_band - lower_band) / sma
    return band_width


def calculate_atr(ohlcv, period=14):
    highs = [candle[2] for candle in ohlcv]
    lows = [candle[3] for candle in ohlcv]
    closes = [candle[4] for candle in ohlcv]
    tr_values = [max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
                 for i in range(1, len(ohlcv))]
    return sum(tr_values[-period:]) / period


def is_sideways_market(symbol, period=20, rsi_range=(40, 60), band_width_threshold=0.002, atr_threshold=0.002):
    ohlcv = fetch_ohlcv_data(symbol, period)
    if not ohlcv:
        return False
    rsi = get_rsi([candle[4] for candle in ohlcv], period=14)
    band_width = calculate_bollinger_bands(ohlcv, period=20)
    atr = calculate_atr(ohlcv, period=14)
    return (rsi_range[0] <= rsi <= rsi_range[1] and
            band_width < band_width_threshold and
            atr / ohlcv[-1][4] < atr_threshold)


def fetch_ohlcv_data(symbol, period=20):
    try:
        return binance.fetch_ohlcv(symbol, timeframe='1m', limit=period)
    except Exception as e:
        print(f"Error fetching OHLCV data for {symbol}: {e}")
        return []

# --- MAIN EXECUTION ---

if __name__ == "__main__":
    listener_thread = threading.Thread(target=listen_for_messages)
    listener_thread.daemon = True
    listener_thread.start()

    profit_thread = threading.Thread(target=update_profit_history)
    profit_thread.daemon = True
    profit_thread.start()

    active_dca_states = load_dca_state()
    print(f"Active DCA States at startup: {active_dca_states}")
    for symbol, config in COIN_CONFIGS.items():
        time.sleep(0.2)
        thread = threading.Thread(target=monitor_coin, args=(symbol, config))
        thread.daemon = True
        thread.start()
    while True:
        time.sleep(1)

# End of trading bot script
# Additional comments for padding
# Padding line 1
# Padding line 2
# Padding line 3
# Padding line 4
# Padding line 5
# Padding line 6
# Padding line 7
# Padding line 8
# Padding line 9
# Padding line 10
# Padding line 11
# Padding line 12
# Padding line 13
# Padding line 14
# Padding line 15
# Padding line 16
# Padding line 17
# Padding line 18
# Padding line 19
# Padding line 20

# Padding line 21
# Padding line 22
# Padding line 23
# Padding line 24
# Padding line 25
# Padding line 26
# Padding line 27
# Padding line 28
# Padding line 29
# Padding line 30
# Padding line 31
# Padding line 32
# Padding line 33
# Padding line 34
# Padding line 35
# Padding line 36
# Padding line 37
# Padding line 38
# Padding line 39
# Padding line 40
# Padding line 41
# Padding line 42
# Padding line 43
# Padding line 44
# Padding line 45
# Padding line 46
# Padding line 47
# Padding line 48
# Padding line 49
# Padding line 50
# Padding line 51
# Padding line 52
# Padding line 53
# Padding line 54
# Padding line 55
# Padding line 56
# Padding line 57
# Padding line 58
# Padding line 59
# Padding line 60

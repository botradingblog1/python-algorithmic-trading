import json
import threading
import time
from binance import Client
from pprint import pformat
from unicorn_binance_websocket_api.manager import BinanceWebSocketApiManager


#  Testnet Binance
TEST_API_KEY = '<Your Binance API Key>'
TEST_API_SECRET = '<Your Binance API Secret>'
base_endpoint = 'https://api.binance.us'  #  NOTE: This may be different for your exchange. Check the docs


def is_empty_message(message):
    if message is False:
        return True
    if '"result":null' in message:
        return True
    if '"result":None' in message:
        return True
    return False


def handle_price_change(symbol, timestamp, price):
    print(f"Handle price change for symbol: {symbol}, timestamp: {timestamp}, price: {price}")


def process_stream_data(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        oldest_data = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()

        is_empty = is_empty_message(oldest_data)
        if is_empty:
            time.sleep(0.01)
        else:
            oldest_data_dict = json.loads(oldest_data)
            data = oldest_data_dict['data']

            #  Handle price change
            handle_price_change(symbol=data['s'], timestamp=data['T'], price=data['p'])


def start_websocket_listener():
    binance_us_websocket_api_manager = BinanceWebSocketApiManager(exchange="binance.us")
    channels = {'trade', }

    binance_us_websocket_api_manager.create_stream(channels, markets=lc_symbols, api_key=TEST_API_KEY, api_secret=TEST_API_SECRET)

    # Start a worker process to move the received stream_data from the stream_buffer to a print function
    worker_thread = threading.Thread(target=process_stream_data, args=(binance_us_websocket_api_manager,))
    worker_thread.start()


def compare_server_times():
    server_time = client.get_server_time()
    aa = str(server_time)
    bb = aa.replace("{'serverTime': ", "")
    aa = bb.replace("}", "")
    gg = int(aa)
    ff = gg - 10799260
    uu = ff / 1000
    yy = int(uu)
    tt = time.localtime(yy)
    print(f"Binance Server time: {tt}")
    print(f"Local time: {time.localtime()}")


def get_traded_symbols():
    symbols = []
    exchange_info = client.get_exchange_info()
    for s in exchange_info['symbols']:
        symbols.append(s['symbol'])
    return symbols


def get_exchange_info():
    info = client.get_exchange_info()
    print(pformat(info))
    tickers = client.get_all_tickers()
    print(pformat(tickers))


#  Define symbols
symbols = ['ETHUSDT', 'BTCUSDT', 'LTCUSDT',]
lc_symbols = []
for symbol in symbols:
    lc_symbols.append(symbol.lower())

#  Initialize binance client
client = Client(api_key=TEST_API_KEY, api_secret=TEST_API_SECRET, testnet=True, tld='us')

#  Compare server and local times
compare_server_times()

#  Get traded symbols
traded_symbols = get_traded_symbols()
print("Traded symbols: ", traded_symbols)

start_websocket_listener()

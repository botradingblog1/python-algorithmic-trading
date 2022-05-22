from datetime import datetime
import pandas as pd
import pandas_ta as ta
import datetime
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
US_BUSINESS_DAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pycoingecko import CoinGeckoAPI
import time
from yattag import Doc
import requests


def get_coin_ids():
    try:
        #  Slow response on Coingecko
        # uri = 'https://api.coingecko.com/api/v3/coins/list'
        uri = 'https://raw.githubusercontent.com/justmobiledev/python-algorithmic-trading/main/data/coingecko-list.json'
        response = requests.get(uri).json()

        return response

    except Exception as e:
        print('Failed to look up Coinbase assets', e)
        return None


def calculate_technical_indicators(df):
    df['60_MA'] = df['close'].rolling(window=60).mean()
    df['40_MA'] = df['close'].rolling(window=40).mean()
    df['15_MA'] = df['close'].rolling(window=15).mean()
    df['RSI'] = ta.rsi(df["close"], length=14)

    return df


def calculate_metrics(df):
    #  Values 2 days ago. 6 values per day (data every 4 hours)
    df['60_MA_2d_ago'] = df.iloc[-12]['60_MA']
    df['40_MA_2d_ago'] = df.iloc[-12]['40_MA']
    df['RSI_2d_ago'] = df.iloc[-12]['RSI']

    #  Values 5 days ago. 6 values per day (data every 4 hours)
    df['60_MA_5d_ago'] = df.iloc[-30]['60_MA']
    df['40_MA_5d_ago'] = df.iloc[-30]['40_MA']
    df['RSI_5d_ago'] = df.iloc[-30]['RSI']

    #  min and max
    df['min_close'] = df['close'].min()
    df['max_close'] = df['close'].max()

    # Condition 6: Current Price is at least 30% above 52-week low
    df['within_close_low'] = df['min_close'] * 1.30
    # Condition 7: Current Price is within 90% of 52-week high
    df['within_close_high'] = df['max_close'] * 0.90

    return df


def evaluate_conditions(df):
    df['condition1'] = (df['close'] > df['60_MA']) & (df['close'] > df['60_MA'])
    df['condition2'] = df['40_MA'] > df['60_MA']
    df['condition3'] = df['60_MA'] > df['60_MA_2d_ago']
    df['condition4'] = (df['40_MA'] > df['60_MA']) & (df['15_MA'] > df['40_MA'])
    df['condition5'] = df['close'] > df['15_MA']
    df['condition6'] = df['close'] < df['within_close_low']
    df['condition7'] = df['RSI_2d_ago'] >= 80

    #  Select stocks where all conditions are met
    query = "condition1 == True & condition2 == True & condition3 == True & condition4 == True & \
            condition5 == True & condition6 == True & condition7 == True"

    selection_df = df.query(query)

    return selection_df


def plot_candlestick(coin_id, df, period):
    plot_info = f"{coin_id}-ohlc-{period}"
    fig = make_subplots(rows=1, cols=1, subplot_titles=[plot_info])

    #  Plot close price
    fig.add_trace(go.Candlestick(x=df['epoch'],
                                 open=df['open'],
                                 high=df['high'],
                                 low=df['low'],
                                 close=df['close']), row=1, col=1)

    fig.update_layout(
        title={'text': '', 'x': 0.5},
        autosize=False,
        width=800, height=600)
    fig.update_yaxes(range=[0, 1000000000], secondary_y=True)
    fig.update_yaxes(visible=False, secondary_y=True)  # hide range slider

    # fig.show()
    fig.write_image(f"{plot_info}.png", format="png")


def get_coin_info(cg, coin_id):
    try:
        response = cg.get_coin_by_id(coin_id)
        categories = response['categories']
        public_notice = response['public_notice']
        name = response['name']
        description = response['description']['en']
        links = response['links']
        homepage_link = links['homepage']
        blockchain_site = links['blockchain_site']
        if blockchain_site is not None:
            blockchain_site = ",".join(blockchain_site)
        official_forum_url = links['official_forum_url']
        chat_url = links['chat_url']
        announcement_url = links['announcement_url']
        twitter_screen_name = links['twitter_screen_name']
        facebook_username = links['facebook_username']
        telegram_channel_identifier = links['telegram_channel_identifier']
        subreddit_url = links['subreddit_url']
        sentiment_votes_up_percentage = response['sentiment_votes_up_percentage']
        sentiment_votes_down_percentage = response['sentiment_votes_down_percentage']
        market_cap_rank = response['market_cap_rank']
        coingecko_rank = response['coingecko_rank']
        coingecko_score = response['coingecko_score']
        community_score = response['community_score']
        liquidity_score = response['liquidity_score']
        public_interest_score = response['public_interest_score']

        row = pd.DataFrame(
            {'id': [coin_id], 'name': [name], 'categories': [categories], 'public_notice': [public_notice], \
             'description': [description], 'homepage_link': [homepage_link], \
             'blockchain_site': [blockchain_site], 'official_forum_url': [official_forum_url], \
             'chat_url': [chat_url], 'announcement_url': [announcement_url], \
             'twitter_screen_name': [twitter_screen_name], 'facebook_username': [facebook_username], \
             'telegram_channel_identifier': [telegram_channel_identifier], 'subreddit_url': [subreddit_url], \
             'sentiment_votes_up_percentage': [sentiment_votes_up_percentage], \
             'sentiment_votes_down_percentage': [sentiment_votes_down_percentage], \
             'market_cap_rank': [market_cap_rank], \
             'coingecko_rank': [coingecko_rank], \
             'coingecko_score': [coingecko_score], 'coingecko_score': [coingecko_score], \
             'community_score': [community_score], 'liquidity_score': [liquidity_score], \
             'public_interest_score': [public_interest_score]})
        row = row.set_index('id')
        return row
    except Exception as e:
        print('Failed to fetch CoinGecko coin info', e)
        return None


def get_ohlc(cg, coin_id, vs_currency, days):
    try:
        response = cg.get_coin_ohlc_by_id(coin_id, vs_currency=vs_currency, days=days)

        ohlc_df = pd.DataFrame()
        for ohlc in response:
            row = pd.DataFrame(
                {'epoch': [ohlc[0]], 'open': [ohlc[1]], 'high': [ohlc[2]], 'low': [ohlc[3]], 'close': [ohlc[4]]})
            ohlc_df = pd.concat([ohlc_df, row], axis=0, ignore_index=True)

        return ohlc_df
    except Exception as e:
        print('Failed to fetch CoinGecko price info', e)
        return None


def build_report(coin_ids, info_map):
    # doc, tag, text, line = Doc().tagtext()
    doc, tag, text, line = Doc().ttl()
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    with tag('html'):
        with tag('head'):
            with tag('style'):
                text("""div{ width: 100%; }
                        html { margin: 0; padding: 10px; background: #1e81b0;}
                        body { font: 12px verdana, sans-serif;line-height: 1.88889; margin: 5%; background: #ffffff; padding: 1%; width: 90%; }
                        p { margin-top: 5px; text-align: justify; font: normal 0.9em verdana, sans-serif;color:#484848}
                        li { font: normal 0.8em verdana, sans-serif;color:#484848}
                        h1 { font: normal 1.8em verdana, sans-serif; letter-spacing: 1px; margin-bottom: 0; color: #063970,}
                        h2 { font: normal 1.6em verdana, sans-serif; letter-spacing: 1px; margin-bottom: 0; color: #154c79}
                        h3 { font: normal 1.6em verdana, sans-serif; letter-spacing: 1px; margin-bottom: 0; color: #154c79}
                        p.bold_text{ font: normal 0.9em verdana, sans-serif; letter-spacing: 1px; margin-bottom: 0; color: #154c79; font-weight: bold}""")

        with tag('body', id='body'):
            with tag('h1'):
                text(f"Trending Crypto Report for {now_str}")
            with tag('hr'):
                text('')

            for coin_id in coin_ids:
                coin_df = info_map[coin_id]
                with tag('h2'):
                    text(f"{coin_id.upper()}")
                with tag('div'):
                    line('p', f"Name: {coin_df['name'].values[0]}", klass="bold_text")
                    line('p', coin_df['name'].values[0])
                    line('p', f"Description:", klass="bold_text")
                    line('p', coin_df['description'].values[0])
                    line('p', f"Categories:", klass="bold_text")
                    category_list = ""
                    if coin_df['categories'].values[0] is not None:
                        for category_str in coin_df['categories'].values[0]:
                            if category_str is None:
                                continue
                            if len(category_list) > 0:
                                category_list += ", "
                            category_list += category_str
                    line('p', f"{category_list}")
                    line('p', f"Public Notice:", klass="bold_text")
                    line('p', f"{coin_df['public_notice'].values[0]}")
                    line('p', f"Links:", klass="bold_text")
                    with tag('ul', id='links-list'):
                        url_list = ""
                        if coin_df['homepage_link'].values[0] is not None:
                            for link_str in coin_df['homepage_link'].values[0]:
                                url_list += link_str
                        line('li', f"Home Page: {url_list}")
                        line('li', f"Blockchain Site: {coin_df['blockchain_site'].values[0]}")
                        url_list = ""
                        if coin_df['official_forum_url'].values[0] is not None:
                            for link_str in coin_df['official_forum_url'].values[0]:
                                url_list += link_str
                        line('li', f"Official Forum URLs: {url_list}")
                        url_list = ""
                        if coin_df['chat_url'].values[0] is not None:
                            for link_str in coin_df['chat_url'].values[0]:
                                url_list += link_str
                        line('li', f"Chat URLs: {url_list}")
                    line('p', f"Social Media:", klass="bold_text")
                    with tag('ul', id='social-list'):
                        line('li', f"Twitter: {coin_df['twitter_screen_name'].values[0]}")
                        line('li', f"Facebook: {coin_df['facebook_username'].values[0]}")
                        line('li', f"Telegram: {coin_df['telegram_channel_identifier'].values[0]}")
                    line('p', f"Sentiment:", klass="bold_text")
                    with tag('ul', id='sentiment-list'):
                        line('li', f"Votes Up: {coin_df['sentiment_votes_up_percentage'].values[0]}")
                        line('li', f"Votes Down: {coin_df['sentiment_votes_down_percentage'].values[0]}")
                    line('p', f"Ranks:", klass="bold_text")
                    with tag('ul', id='sentiment-list'):
                        line('li', f"Market Cap Rank: {coin_df['market_cap_rank'].values[0]}")
                        line('li', f"Gecko Rank: {coin_df['coingecko_rank'].values[0]}")
                        line('li', f"Gecko Score: {coin_df['coingecko_score'].values[0]}")
                        line('li', f"Community Score: {coin_df['community_score'].values[0]}")
                        line('li', f"Public Interest Score: {coin_df['public_interest_score'].values[0]}")
                    with tag('div', id='photo-container'):
                        line('p', f"Day Plot:", klass="bold_text")
                        doc.stag('img', src=f"{coin_id}-ohlc-day.png", klass="day_plot")
                        line('p', f"Month Plot:", klass="bold_text")
                        doc.stag('img', src=f"{coin_id}-ohlc-month.png", klass="day_plot")
                    with tag('hr'):
                        text('')

    #  Save report
    report_file = open("screener-coins-report.html", "w")
    report_file.write(doc.getvalue())
    report_file.close()


#  Initialize clients
cg = CoinGeckoAPI()

#  Get all coinbase assets
max_coins = 5
month_ohlc_map = {}
info_map = {}
selected_coin_ids = []
coin_list = get_coin_ids()
num_selections = 0
max_selections = 3
i = 0
for coin in coin_list:
    coin_id = coin['id']
    name = coin['name']
    symbol = coin['symbol']

    #  Skip unwanted coins
    if "RealT" in name:
        continue

    print(f"Processing '{name}', ({symbol})")

    #  Get monthly prices - 4 hour period
    ohlc_df = get_ohlc(cg, coin_id, vs_currency='usd', days=30)
    if len(ohlc_df) < 30:
        continue
    ohlc_df = calculate_technical_indicators(ohlc_df)

    #  Calculate SMAs and RSI
    metrics_df = calculate_metrics(ohlc_df)
    selections_df = evaluate_conditions(metrics_df)
    if len(selections_df) > 0:
        #  Get coin info
        time.sleep(1.3)
        info_df = get_coin_info(cg, coin_id)
        if info_df is None:
            continue
        info_map[coin_id] = info_df

        #  Store prices
        ohlc_df.to_csv(f"{coin_id}_ohlc_df.csv")

        print(f"-> Match: {coin_id}, {name}")
        selected_coin_ids.append(coin_id)

        num_selections += 1
        if num_selections >= max_selections:
            break

    time.sleep(1.3)

#  Build report
build_report(selected_coin_ids, info_map)

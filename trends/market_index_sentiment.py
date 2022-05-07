import os
import math
import numpy as np
import pandas as pd
import datetime
from datetime import date
import pandas_ta as ta
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
from yahoo_fin import stock_info as si
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
US_BUSINESS_DAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())


def calculate_smas(df):
    df['SMA20'] = ta.sma(df["close"], length=20)
    df['SMA5'] = ta.sma(df["close"], length=5)
    df['SMA5_SMA20'] = df['SMA5'] / df['SMA20']
    df['SMA5_SMA20_NORM'] = (df['SMA5_SMA20'] - df['SMA5_SMA20'].min()) / (df['SMA5_SMA20'].max() - df['SMA5_SMA20'].min())

    return df


def determine_market_trend(df):
    short_term_sentiment = round(df['SMA5_SMA20_NORM'].tail(20).mean(),2)

    return short_term_sentiment


def load_daily_data(symbol):
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    start_date = today - (220 * US_BUSINESS_DAY)
    start_date_str = datetime.datetime.strftime(start_date, "%Y-%m-%d")
    try:
        # Download data from Yahoo Finance
        df = si.get_data(symbol, start_date=start_date_str, end_date=today_str, index_as_date=False)
        return df
    except:
        print('Error loading stock data for ' + symbol)
        return None


def plot_trend_indicator(df, name):
    fig = make_subplots(rows=2, cols=1)

    #  Plot close price
    fig.add_trace(go.Line(x=df.index, y=df['close'], line=dict(color="blue", width=1), name=name),
                  row=1, col=1)

    #  SMAs
    fig.add_trace(go.Line(x=df.index, y=df['SMA20'], line=dict(color="#f95738", width=1), name="SMA 20"),
                  row=1, col=1)
    fig.add_trace(go.Line(x=df.index, y=df['SMA5'], line=dict(color="#ee964b", width=1), name="SMA 5"),
                  row=1, col=1)


    #  Plot Indicator
    fig.add_trace(go.Line(x=df.index, y=df['SMA5_SMA20_NORM'], line=dict(color="#f95738", width=1), name="Short Term Trend Indicator"),
                  row=2, col=1)


    fig.add_hline(y=0.5, row=2, col=1)

    fig.update_layout(
        title={'text': f"{name} Trend Indicator", 'x': 0.5},
        autosize=True,
        width=800, height=800)
    fig.update_yaxes(autorange=True, fixedrange=False, secondary_y=True, row=1, col=1)
    fig.update_yaxes(range=[0,1], row=2, col=1)

    fig.write_image(f"{name}_trend_indictor.png")



def get_market_sentiment():
    #  Retrieve prices for DOW
    dji_df = load_daily_data('^DJI')
    dji_df = calculate_smas(dji_df)
    dow_short_term_trend = determine_market_trend(dji_df)

    #  NASDAQ
    nasdaq_df = load_daily_data('^IXIC')
    nasdaq_df = calculate_smas(nasdaq_df)
    nasdaq_short_term_trend = determine_market_trend(nasdaq_df)

    #  S&P 500
    snp_df = load_daily_data('^GSPC')
    snp_df = calculate_smas(snp_df)
    snp_short_term_trend = determine_market_trend(snp_df)

    #  Crypto index
    crypto_df = load_daily_data('BITW')
    crypto_df = calculate_smas(crypto_df)
    crypto_short_term_trend = determine_market_trend(crypto_df)

    #  Visualize results
    plot_trend_indicator(dji_df.tail(200), 'DJI')
    plot_trend_indicator(nasdaq_df.tail(200), 'NASDAQ')
    plot_trend_indicator(snp_df.tail(200), 'S&P')
    plot_trend_indicator(crypto_df.tail(200), 'BITW')

    combined_trend = (dow_short_term_trend + nasdaq_short_term_trend + snp_short_term_trend + crypto_short_term_trend) / 4
    combined_trend = str(round(combined_trend,2))
    print(combined_trend)

get_market_sentiment()
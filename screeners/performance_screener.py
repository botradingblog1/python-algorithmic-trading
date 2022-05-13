import os
import numpy as np
import pandas_ta as ta
import pandas as pd
import datetime
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
US_BUSINESS_DAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())
from yahoo_fin import stock_info as si
import time
from random import randint


"""
Strategy Rules:
- Current stock price is above the 150 and 200 days moving average (MA).
- The 150 days moving average is above the 200 days moving average.
- The 200 days moving average is trending up for at least a month.
- The 50 day MA is above the 150 and 200 MAs
- Stock price is above the 50 day MA
- Current share price is at least 30% above its 52 week low
- Current stock price is at least within 25% of the 52 week high
"""


def get_past_business_days_delta_str(current_date_str, business_day_delta):
    target_date = datetime.datetime.strptime(current_date_str, "%Y-%m-%d")
    delta_date = target_date + (business_day_delta * US_BUSINESS_DAY)
    delta_date_str = datetime.datetime.strftime(delta_date, "%Y-%m-%d")
    return delta_date_str


def load_nasdaq_symbols():
    nasdaq_df = pd.read_csv(
        'https://raw.githubusercontent.com/justmobiledev/python-algorithmic-trading/main/data/nasdaq.csv')
    symbols = nasdaq_df['Symbol'].to_numpy()
    return symbols


def load_historic_data(symbol):
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    #  Get last 2 years of data
    start_date = today - (522 * US_BUSINESS_DAY)
    start_date_str = datetime.datetime.strftime(start_date, "%Y-%m-%d")
    try:
        # Download data from Yahoo Finance
        df = si.get_data(symbol, start_date=start_date_str, end_date=today_str, index_as_date=False)
        return df
    except:
        print('Error loading stock data for ' + symbol)
        return None


def calculate_technical_indicators(df):
    df['200_MA'] = df['adjclose'].rolling(window=200).mean()
    df['150_MA'] = df['adjclose'].rolling(window=150).mean()
    df['50_MA'] = df['adjclose'].rolling(window=50).mean()

    return df


def calculate_metrics(df):
    #  Get 1 month ago values -> 20 business days
    today = datetime.datetime.today()
    today_str = today.strftime("%Y-%m-%d")
    one_month_ago_str = get_past_business_days_delta_str(today_str, -20)
    mask = (df['date'] >= one_month_ago_str)
    df['200_MA_1m_ago'] = df[mask]['200_MA']
    df['150_MA_1m_ago'] = df[mask]['150_MA']

    #  Get 2 month ago values
    two_months_ago_str = get_past_business_days_delta_str(today_str, -40)
    mask = (df['date'] >= two_months_ago_str)
    df['200_MA_2m_ago'] = df[mask]['200_MA']
    df['150_MA_2m_ago'] = df[mask]['150_MA']

    #  Get 52w values
    one_year_ago_str = get_past_business_days_delta_str(today_str, -261)
    mask = (df['date'] >= one_year_ago_str) & (df['date'] <= today_str)
    df['52w_low'] = df[mask]['adjclose'].min()
    df['52w_high'] = df[mask]['adjclose'].max()

    # Condition 6: Current Price is at least 30% above 52-week low
    df['above_52w_low'] = df['52w_low'] * 1.30
    # Condition 7: Current Price is within 25% of 52-week high
    df['within_52w_high'] = df['52w_high'] * 0.75

    return df


def evaluate_conditions(df):
    df['condition1'] = (df['adjclose'] > df['200_MA']) & (df['adjclose'] > df['150_MA'])
    df['condition2'] = df['150_MA'] > df['200_MA']
    df['condition3'] = df['200_MA'] > df['200_MA_1m_ago']
    df['condition4'] = (df['50_MA'] > df['200_MA']) & (df['50_MA'] > df['150_MA'])
    df['condition5'] = df['adjclose'] > df['50_MA']
    df['condition6'] = df['adjclose'] > df['above_52w_low']
    df['condition7'] = df['adjclose'] > df['within_52w_high']

    #  Select stocks where all conditions are met
    query = "condition1 == True & condition2 == True & condition3 == True & condition4 == True & \
              condition5 == True & condition6 == True & condition7 == True"

    selection_df = df.query(query)

    return selection_df


#  MAIN
def main():
    results_df = pd.DataFrame({"symbol": []})
    symbols = load_nasdaq_symbols()

    #  Iterate through symbols
    for symbol in symbols:
        #  Skip indices
        if '^' in symbol:
            continue

        print(f"Processing: {symbol}")
        #  Load daily historic prices
        price_df = load_historic_data(symbol)
        if price_df is None:
            continue

        #  Only need last two year
        price_df = price_df.tail(522)
        if len(price_df) < 522:
            continue

        #  Calculate indicators for all rows
        price_df = calculate_technical_indicators(price_df)

        #  Calculate metrics
        price_df = calculate_metrics(price_df)

        #  Evaluate conditions
        selections_df = evaluate_conditions(price_df)
        if not selections_df.empty:
            print(f"Candidate stock: {symbol}")
            result_df = pd.DataFrame({"symbol": [symbol]})
            results_df = pd.concat([results_df, result_df], axis=0, ignore_index=True)

        #  Avoid DOS issues
        time.sleep(randint(0,1))

    print(f"Selections: {results_df['symbol'].values[0]}")


if __name__ == "__main__":
    main()

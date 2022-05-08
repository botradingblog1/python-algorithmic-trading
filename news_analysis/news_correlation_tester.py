
import pandas as pd
import math
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np
import datetime
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
US_BUSINESS_DAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())
from yahoo_fin import stock_info as si
from setup import *
import time
import requests
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

#  Based on https://wandb.ai/ivangoncharov/FinBERT_Sentiment_Analysis_Project/reports/Financial-Sentiment-Analysis-on-Stock-Market-Headlines-With-FinBERT-Hugging-Face--VmlldzoxMDQ4NjM0

#  Init tokenizers and finbert model
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")


# Newsfilter API endpoint
API_KEY = "6276a200705764.72205745"


def load_daily_data(symbol, past_days):
    today = datetime.date.today()
    today_str = today.strftime("%Y-%m-%d")
    start_date = today - (past_days * US_BUSINESS_DAY)
    start_date_str = datetime.datetime.strftime(start_date, "%Y-%m-%d")
    try:
        # Download data from Yahoo Finance
        df = si.get_data(symbol, start_date=start_date_str, end_date=today_str, index_as_date=False)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        return df
    except:
        print('Error loading stock data for ' + symbol)
        return None


def fetch_news(symbol, start_date_str, end_date_str, limit, offset=0):
    url = f'https://eodhistoricaldata.com/api/news?api_token={API_KEY}&s={symbol}&limit={limit}&offset={offset}&from={start_date_str}&to={end_date_str}'
    news_json = requests.get(url).json()

    results_df = pd.DataFrame()
    for item in news_json:

        title = item['title']
        desc = item['content']
        date = pd.to_datetime(item["date"], utc=True)
        result_df = pd.DataFrame({"title": [title], "desc": [desc], "date": [date]})
        results_df = pd.concat([results_df, result_df], axis=0, ignore_index=True)

    return results_df


def load_news(symbol, past_days):
    limit = 30
    today = datetime.datetime.today()
    today_date_str = today.strftime("%Y-%m-%d")
    news_df = pd.DataFrame()
    #  Get news for each day
    for i in range(0, past_days):
        start_day = past_days - i
        end_day = past_days - i - 1
        start_date_str = get_biz_days_delta_date(today_date_str, - start_day)
        end_date_str = get_biz_days_delta_date(today_date_str, - end_day)

        #  Fetch news
        if i % 10 == 0:
            print(f"Fetching news for day {start_day} of {past_days}")
        day_news_df = fetch_news(symbol, start_date_str, end_date_str, limit, 0)
        news_df = pd.concat([news_df, day_news_df])
        #  Throttle requests
        if i % 20 == 0:
            time.sleep(2)

    return news_df


def is_empty_string(str):
    if str == '' or (isinstance(str, float) and math.isnan(str)):
        return True
    else:
        return False


def perform_sentiment_analysis(df):
    results_df = pd.DataFrame([], columns=['date', 'positive','negative'])

    count = 0
    headlines = []
    dates = []
    for index, row in df.iterrows():
        count += 1
        if count % 10 == 0:
            print(f"Performing sentiment analysis {count} of {len(df)}")

        date = row["date"]
        title = row["title"]
        desc = row["desc"]

        if is_empty_string(title) or is_empty_string(desc):
            continue

        headlines.append(title)
        dates.append(date)

    if len(headlines) == 0:
        return results_df

    #  Run sentiment analysis
    inputs = tokenizer(headlines, padding=True, truncation=True, return_tensors='pt')

    outputs = model(** inputs)

    predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)

    positive = predictions[:,0].tolist()
    negative = predictions[:,1].tolist()
    neutral = predictions[:,2].tolist()

    table = {"headline": headlines,
             "positive": positive,
             "negative": negative,
             "neutral": neutral,
             "date": dates}

    results_df = pd.DataFrame(table, columns=["headline", "positive", "negative", "neutral", "date"])

    return results_df


def plot_graphs(symbol, df):
    fig = make_subplots(rows=2, cols=1, subplot_titles=["Close", "Sentiment",])

    #  Plot close price
    fig.add_trace(go.Line(x=df.index, y=df['close'], line=dict(color="blue", width=1), name=name),
                  row=1, col=1)

    # Plot the histogram
    fig.append_trace(
        go.Bar(
            x=df.index,
            y=df['positive'],
            name='Positive Sentiment',
            marker_color="green",
        ), row=2, col=1
    )

    # Plot the histogram
    df['negative'] *= -1
    fig.append_trace(
        go.Bar(
            x=df.index,
            y=df['negative'],
            name='Negative Sentiment',
            marker_color="red",
        ), row=2, col=1
    )

    fig.update_layout(
        title={'text': f"{name} News Correlation", 'x': 0.5},
        autosize=True,
        width=800, height=1200)

    #  Save file
    file_name = f"{symbol}_news_correlation.png"
    file_path = os.path.join(NEWS_RESULTS_DIR, file_name)
    fig.write_image(file_path, format="png")


def get_biz_days_delta_date(start_date_str, delta_days):
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = start_date + (delta_days * US_BUSINESS_DAY)
    end_date_str = datetime.datetime.strftime(end_date, "%Y-%m-%d")
    return end_date_str


symbol = 'TSLA'
name = 'Telsa'
past_days = 100
news_df = load_news(symbol, past_days)
news_df.fillna(0)
news_df.to_csv('news_df.csv')

#  Perform sentiment analysis
results_df = perform_sentiment_analysis(news_df)

#  Group by date
grouped_df = results_df.set_index('date').groupby(pd.Grouper(freq='D')).sum()

 #  Load daily stock price info
daily_df = load_daily_data(symbol, past_days)

#  Merge with news df
merged_df = pd.merge(daily_df, grouped_df, how="outer", on="date")
merged_df = merged_df.dropna()

#  Plot graphs
#plot_graphs(symbol, merged_df)

#  Normalize prices and sentiments for correlation calculation
merged_df['close_norm'] = (merged_df['close'] - merged_df['close'].min()) / (merged_df['close'].max() - merged_df['close'].min())
merged_df['positive_norm'] = (merged_df['positive'] - merged_df['positive'].min()) / (merged_df['positive'].max() - merged_df['positive'].min())
merged_df['negative_norm'] = (merged_df['negative'] - merged_df['negative'].min()) / (merged_df['negative'].max() - merged_df['negative'].min())

#  Calculate correlation
news_pos_corr = merged_df['close_norm'].corr(merged_df['positive_norm'])
news_neg_corr = merged_df['close_norm'].corr(merged_df['negative_norm'])
print('Pos correlation: ', str(round(news_pos_corr, 2)))
print('Neg correlation: ', str(round(news_neg_corr, 2)))



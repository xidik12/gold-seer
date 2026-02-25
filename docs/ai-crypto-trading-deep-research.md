# AI-Powered Cryptocurrency Trading Analysis Platform
## Comprehensive Deep Research Report (February 2026)

---

## Table of Contents
1. [Crypto Price Prediction - ML/AI Models](#1-crypto-price-prediction---mlai-models)
2. [New Coin Listing Detection](#2-new-coin-listing-detection)
3. [Social Media & News Sentiment Analysis](#3-social-media--news-sentiment-analysis)
4. [Memecoin & Altcoin Analysis](#4-memecoin--altcoin-analysis)
5. [Exchange APIs](#5-exchange-apis)
6. [Proven Trading Strategies](#6-proven-trading-strategies)
7. [Real-time Data Architecture](#7-real-time-data-architecture)

---

## 1. Crypto Price Prediction - ML/AI Models

### 1.1 Best-Performing Models (Ranked by Research Consensus)

| Model | Strengths | Typical Accuracy | Best For |
|-------|-----------|-----------------|----------|
| **Temporal Fusion Transformer (TFT)** | Interpretable attention, handles known/unknown inputs | Lowest RMSE across studies | Multi-horizon forecasting |
| **Transformer (Vanilla)** | Captures long-range dependencies | Outperforms LSTM on short+long term | General price prediction |
| **LSTM + XGBoost (Hybrid)** | Temporal + non-linear boosting | Beats individual models consistently | Combined signal approach |
| **GRU** | Faster training, lower error than LSTM | Outperforms LSTM for BTC/ETH/LTC | Resource-constrained environments |
| **LSTM (Univariate)** | Well-studied, reliable baseline | 55-65% directional accuracy | Single-asset prediction |
| **CNN-LSTM Hybrid** | Spatial feature extraction + temporal | Enhanced interpretability with autoencoders | Pattern recognition |
| **Informer** | Efficient self-attention for long sequences | Competitive with TFT | Very long sequence forecasting |

### 1.2 Temporal Fusion Transformer (TFT) - Implementation

The TFT is the current state-of-the-art for crypto forecasting. It provides:
- **Multi-horizon forecasting** (predict multiple future time steps)
- **Interpretable attention weights** (know which features matter)
- **Quantile loss** for probabilistic forecasts (uncertainty estimation)

**Python Implementation (pytorch-forecasting):**
```python
pip install pytorch-forecasting pytorch-lightning

from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.metrics import QuantileLoss

# Define dataset
training = TimeSeriesDataSet(
    data,
    time_idx="time_idx",
    target="close_price",
    group_ids=["symbol"],
    max_encoder_length=168,    # 7 days of hourly data
    max_prediction_length=24,  # predict 24 hours ahead
    time_varying_known_reals=["hour", "day_of_week", "rsi", "macd"],
    time_varying_unknown_reals=["close_price", "volume", "open_interest"],
    static_categoricals=["symbol"],
)

# Build model
tft = TemporalFusionTransformer.from_dataset(
    training,
    learning_rate=0.001,
    hidden_size=64,
    attention_head_size=4,
    dropout=0.1,
    hidden_continuous_size=16,
    loss=QuantileLoss(),
    reduce_on_plateau_patience=4,
)
```

**Alternative: Darts Library**
```python
pip install darts

from darts.models import TFTModel
from darts import TimeSeries

model = TFTModel(
    input_chunk_length=168,
    output_chunk_length=24,
    hidden_size=64,
    lstm_layers=1,
    num_attention_heads=4,
    dropout=0.1,
    batch_size=32,
    n_epochs=100,
    likelihood=QuantileRegression(quantiles=[0.1, 0.5, 0.9]),
)
```

### 1.3 Technical Analysis Indicators

**Core Indicators and Formulas:**

#### RSI (Relative Strength Index)
```
RSI = 100 - (100 / (1 + RS))
RS = Average Gain over N periods / Average Loss over N periods
Default N = 14

Interpretation:
- RSI > 70 = Overbought (potential sell signal)
- RSI < 30 = Oversold (potential buy signal)
- RSI divergence from price = trend reversal signal
```

#### MACD (Moving Average Convergence Divergence)
```
MACD Line = EMA(12) - EMA(26)
Signal Line = EMA(9) of MACD Line
Histogram = MACD Line - Signal Line

EMA formula: EMA_today = Price_today * k + EMA_yesterday * (1-k)
where k = 2 / (N + 1)

Signals:
- MACD crosses above Signal = Bullish
- MACD crosses below Signal = Bearish
- Histogram expansion = Momentum increasing
```

#### Bollinger Bands
```
Middle Band = SMA(20)
Upper Band = SMA(20) + 2 * StdDev(20)
Lower Band = SMA(20) - 2 * StdDev(20)

%B = (Price - Lower Band) / (Upper Band - Lower Band)
Bandwidth = (Upper Band - Lower Band) / Middle Band

Signals:
- Price touches Lower Band = Potential buy (mean reversion)
- Price touches Upper Band = Potential sell (mean reversion)
- Bandwidth squeeze = Volatility breakout imminent
```

#### Additional Critical Indicators
```
# ATR (Average True Range) - Volatility measure
True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
ATR = SMA(True Range, 14)

# OBV (On-Balance Volume) - Volume-price confirmation
OBV += Volume if Close > PrevClose
OBV -= Volume if Close < PrevClose

# VWAP (Volume Weighted Average Price)
VWAP = Cumulative(Price * Volume) / Cumulative(Volume)

# Stochastic RSI
StochRSI = (RSI - min(RSI, N)) / (max(RSI, N) - min(RSI, N))

# ADX (Average Directional Index) - Trend strength
ADX > 25 = Strong trend
ADX < 20 = Weak/no trend
```

**Python Implementation:**
```python
pip install ta-lib pandas-ta

# Using TA-Lib
import talib
rsi = talib.RSI(close_prices, timeperiod=14)
macd, signal, hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
upper, middle, lower = talib.BBANDS(close_prices, timeperiod=20, nbdevup=2, nbdevdn=2)
atr = talib.ATR(high, low, close, timeperiod=14)

# Using pandas-ta (no C dependency)
import pandas_ta as ta
df.ta.rsi(length=14, append=True)
df.ta.macd(fast=12, slow=26, signal=9, append=True)
df.ta.bbands(length=20, std=2, append=True)
df.ta.atr(length=14, append=True)
df.ta.obv(append=True)
df.ta.vwap(append=True)
df.ta.stochrsi(length=14, append=True)
df.ta.adx(length=14, append=True)
```

### 1.4 On-Chain Analysis Metrics

| Metric | Formula | Signal |
|--------|---------|--------|
| **MVRV Ratio** | Market Cap / Realized Cap | >3.5 = overvalued, <1 = undervalued |
| **MVRV Z-Score** | (Market Cap - Realized Cap) / StdDev(Market Cap) | >7 = top, <0.1 = bottom |
| **SOPR** | Value of outputs at spent time / Value at creation time | >1 = profit taking, <1 = capitulation |
| **NVT Ratio** | Market Cap / Daily Transaction Volume (USD) | >95 = overvalued, <45 = undervalued |
| **Puell Multiple** | Daily Issuance Value / 365-day MA of Issuance | >4 = top zone, <0.5 = accumulation |
| **Stock-to-Flow** | Current Supply / Annual Production | Higher = more scarce |
| **Active Addresses** | Unique sending+receiving addresses per day | Rising = growing adoption |
| **Exchange Netflow** | Inflow - Outflow from exchanges | Positive = selling pressure |
| **Realized P/L Ratio** | Realized Profit / Realized Loss | Extreme values = reversals |

**Data Providers for On-Chain Metrics:**
- **Glassnode** - Gold standard, API access from $29/month, `api.glassnode.com`
- **CryptoQuant** - Exchange flow data, `api.cryptoquant.com`
- **Santiment** - Social + on-chain combined, `api.santiment.net`
- **CoinMetrics** - Community (free) + Pro APIs, `api.coinmetrics.io`
- **IntoTheBlock** - ML-powered on-chain analytics
- **Messari** - Fundamental analysis + on-chain

### 1.5 Time Series Forecasting Methods

**Model Comparison for Crypto:**
```
Traditional:
- ARIMA/SARIMA: Poor for crypto (assumes stationarity)
- Prophet (Meta): Good baseline, handles seasonality, but weak on crypto volatility
- VAR: Useful for multi-asset correlation modeling

Deep Learning:
- LSTM: Good baseline, capture temporal dependencies
- GRU: Faster, often matches/beats LSTM
- Transformer: Best for long sequences
- TFT: Best overall (interpretable + accurate)
- N-BEATS: Strong univariate forecasting
- N-HiTS: Efficient hierarchical forecasting

Ensemble/Hybrid:
- LSTM + XGBoost: Best hybrid approach per 2025 research
- CNN + LSTM: Feature extraction + temporal modeling
- Attention-LSTM: Best of attention + recurrence

Practical Accuracy Benchmarks:
- Directional accuracy: 55-65% (above 60% is very good)
- Most models fail during black swan events
- Ensemble methods reduce false signals by 15-20%
```

---

## 2. New Coin Listing Detection

### 2.1 Detection Methods

#### Method 1: Binance API Polling (Symbol Monitoring)
```python
import requests
import time

BINANCE_API = "https://api.binance.com/api/v3/exchangeInfo"
known_symbols = set()

def check_new_listings():
    response = requests.get(BINANCE_API)
    data = response.json()
    current_symbols = {s['symbol'] for s in data['symbols']}

    new_symbols = current_symbols - known_symbols
    if new_symbols and known_symbols:  # Skip first run
        for symbol in new_symbols:
            alert_new_listing(symbol)

    known_symbols.update(current_symbols)

# Poll every 30 seconds (respect rate limits)
while True:
    check_new_listings()
    time.sleep(30)
```

#### Method 2: Binance Announcement Scraping
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
import re

BINANCE_ANNOUNCEMENTS = "https://www.binance.com/en/support/announcement/new-cryptocurrency-listing"

def scrape_announcements():
    driver = webdriver.Chrome()
    driver.get(BINANCE_ANNOUNCEMENTS)

    articles = driver.find_elements(By.CSS_SELECTOR, "a[class*='announcement']")
    for article in articles:
        title = article.text
        if "Lists" in title or "Will List" in title:
            # Extract token symbol using regex
            match = re.search(r'\(([A-Z]+)\)', title)
            if match:
                symbol = match.group(1)
                alert_new_listing(symbol, title)

    driver.quit()
```

#### Method 3: Binance Alpha Monitoring
Binance Alpha (launched 2025) is a feature in the Binance Wallet where tokens being considered for full listing appear first. Monitor:
- `https://www.binance.com/en/support/announcement/list/48` (announcements feed)
- Telegram channel: `https://t.me/binance_api_announcements`

#### Method 4: CryptocurrencyAlerting.com Service
- Webhook notifications for new listings as they are detected
- Supports Binance, Coinbase, Kraken, and 100+ exchanges
- API-based detection (faster than scraping)

### 2.2 DEX-to-CEX Pipeline (Finding Coins Before Major Listings)

**The typical flow:**
```
Token Launch on DEX (Uniswap/Raydium)
  -> Community Growth + Volume
  -> Tier-3 CEX listing (MEXC, Gate.io)
  -> Tier-2 CEX listing (KuCoin, Bybit)
  -> Tier-1 CEX listing (Binance, Coinbase)
```

**Monitoring New DEX Pairs:**

For **Ethereum/Uniswap:**
```python
# Using web3-ethereum-defi library
pip install web3-ethereum-defi

from web3 import Web3
from eth_defi.uniswap_v2.pair import fetch_pair_details

# Listen for PairCreated events on Uniswap V2 Factory
UNISWAP_V2_FACTORY = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
PAIR_CREATED_TOPIC = "0x0d3648bd0f6ba80134a33ba9275ac585d9d315f0ad8355cddefde31afa28d0e9"

w3 = Web3(Web3.WebsocketProvider("wss://eth-mainnet.g.alchemy.com/v2/YOUR_KEY"))

pair_filter = w3.eth.filter({
    "address": UNISWAP_V2_FACTORY,
    "topics": [PAIR_CREATED_TOPIC]
})
```

For **Solana/Raydium:**
```python
# Monitor Raydium Pool V4 for initialize2 instructions
# Using solana-py and WebSocket subscription

import asyncio
from solana.rpc.websocket_api import connect

RAYDIUM_POOL_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

async def monitor_new_pools():
    async with connect("wss://api.mainnet-beta.solana.com") as ws:
        await ws.logs_subscribe(
            {"mentions": [RAYDIUM_POOL_V4]},
            commitment="confirmed"
        )
        async for msg in ws:
            logs = msg.result.value.logs
            if any("initialize2" in log for log in logs):
                # New pool created!
                process_new_pool(msg)
```

**Key Tools for DEX-to-CEX Detection:**
- **DexScreener** (`dexscreener.com/new-pairs`) - Real-time new pair tracking
- **ListingSpy** (`listingspy.net`) - Unified listing tracker
- **Birdeye** (`birdeye.so`) - Solana token analytics
- **DEXTools** (`dextools.io`) - Multi-chain DEX analytics
- **Binance Alpha** - Pre-listing consideration list

### 2.3 Historical Price Patterns After Exchange Listings

```
Typical Binance Listing Pattern:
- Pre-announcement pump: +50-200% (if leaked/anticipated)
- Announcement to listing: +20-80% additional
- First 15 minutes after listing: Extremely volatile, often +100-500%
- Within 24-48 hours: 60-80% retrace from peak in most cases
- Exception: Strong projects may sustain gains

Strategy Implications:
- Buy the rumor (pre-listing on DEX)
- Sell within first 30 minutes of CEX listing
- Or wait for 48-hour retrace and DCA in
```

---

## 3. Social Media & News Sentiment Analysis

### 3.1 Best APIs for Crypto News Aggregation

| API | Free Tier | Features | Endpoint |
|-----|-----------|----------|----------|
| **CryptoPanic** | 50 req/hr | News aggregation, votes, filters | `cryptopanic.com/api/v1/posts/` |
| **CoinGecko** | 30 calls/min | Trending, status updates | `api.coingecko.com/api/v3/` |
| **Messari** | Limited | Research, news, profiles | `data.messari.io/api/v1/news` |
| **NewsAPI.org** | 100 req/day | General news search | `newsapi.org/v2/everything?q=crypto` |
| **CryptoPanic RSS** | Unlimited | RSS feeds by currency | `cryptopanic.com/news/rss/` |
| **The Block API** | Paid | Institutional research | `api.theblockcrypto.com/` |

### 3.2 Twitter/X Sentiment Analysis

**X API Access (2026):**
- Free tier: 1,500 tweets/month read (severely limited)
- Basic ($100/mo): 10,000 tweets/month
- Pro ($5,000/mo): 1M tweets/month
- Enterprise: Custom

**Alternative X Data Sources:**
```python
# Option 1: Use Nitter instances (unofficial, may break)
# Option 2: LunarCrush API (aggregates X data)
# Option 3: Snscrape (unofficial scraper)

pip install snscrape

import snscrape.modules.twitter as sntwitter
import pandas as pd

query = "#Bitcoin OR $BTC since:2026-02-01 until:2026-02-17"
tweets = []
for tweet in sntwitter.TwitterSearchScraper(query).get_items():
    if len(tweets) >= 1000:
        break
    tweets.append({
        'date': tweet.date,
        'content': tweet.rawContent,
        'likes': tweet.likeCount,
        'retweets': tweet.retweetCount,
        'user_followers': tweet.user.followersCount
    })
df = pd.DataFrame(tweets)
```

### 3.3 Reddit Sentiment Analysis

```python
# Reddit API (free via PRAW)
pip install praw

import praw

reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="crypto_sentiment_bot/1.0"
)

# Monitor key subreddits
CRYPTO_SUBREDDITS = [
    "CryptoCurrency", "Bitcoin", "ethereum",
    "altcoin", "CryptoMoonShots", "SatoshiStreetBets",
    "defi", "solana", "CryptoMarkets"
]

for subreddit_name in CRYPTO_SUBREDDITS:
    subreddit = reddit.subreddit(subreddit_name)
    for post in subreddit.hot(limit=100):
        analyze_sentiment(post.title, post.selftext, post.score, post.num_comments)
```

### 3.4 Telegram Group Monitoring

```python
# Using Telethon for Telegram scraping
pip install telethon

from telethon import TelegramClient
from telethon.tl.types import Channel

API_ID = "YOUR_API_ID"       # Get from my.telegram.org
API_HASH = "YOUR_API_HASH"

client = TelegramClient('session', API_ID, API_HASH)

CRYPTO_GROUPS = [
    "binance_announcements",
    "CryptoComOfficial",
    "whale_alert_io",
    # Add alpha groups, signal groups, etc.
]

async def monitor_groups():
    await client.start()
    for group in CRYPTO_GROUPS:
        entity = await client.get_entity(group)
        async for message in client.iter_messages(entity, limit=100):
            sentiment = analyze_sentiment(message.text)
            store_sentiment(group, message.date, sentiment)

# Rate limiting note: Don't scrape too aggressively
# Use rotating proxies if needed
```

### 3.5 Building a Crypto Sentiment Score

**Composite Sentiment Score Formula:**
```
Sentiment_Score = (
    w1 * twitter_sentiment +
    w2 * reddit_sentiment +
    w3 * news_sentiment +
    w4 * telegram_sentiment +
    w5 * fear_greed_index_normalized +
    w6 * funding_rate_sentiment +
    w7 * social_volume_zscore
) / sum(weights)

Recommended weights:
- w1 (Twitter/X): 0.25
- w2 (Reddit): 0.15
- w3 (News): 0.20
- w4 (Telegram): 0.10
- w5 (Fear & Greed): 0.15
- w6 (Funding Rate): 0.10
- w7 (Social Volume): 0.05

Scale: -1.0 (Extreme Fear/Bearish) to +1.0 (Extreme Greed/Bullish)
```

**Fear & Greed Index API (Free):**
```python
# Alternative.me API - Free, no key required
import requests

# Current value
response = requests.get("https://api.alternative.me/fng/")
data = response.json()
# Returns: {"value": "75", "value_classification": "Greed", "timestamp": "..."}

# Historical data (all available)
response = requests.get("https://api.alternative.me/fng/?limit=0&format=json")
# Rate limit: 60 requests/minute
```

### 3.6 NLP Models for Crypto Sentiment

**Ranked by suitability for crypto:**

| Model | Source | Training Data | Accuracy |
|-------|--------|---------------|----------|
| **CryptoBERT (ElKulako)** | HuggingFace | 3.2M crypto social posts | Best for crypto slang |
| **CryptoBERT (kk08)** | HuggingFace | Fine-tuned FinBERT on crypto | Best for crypto news |
| **FinBERT** | ProsusAI/finBERT | Financial corpus | Best for financial text |
| **GPT-4 (zero-shot)** | OpenAI API | General | Good but expensive |
| **VADER** | nltk | General | Fast baseline, poor on crypto |
| **TextBlob** | textblob | General | Fast baseline |

**CryptoBERT Implementation:**
```python
pip install transformers torch

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load CryptoBERT
model_name = "ElKulako/cryptobert"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

def analyze_crypto_sentiment(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)

    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    labels = ["Bearish", "Neutral", "Bullish"]

    predicted_class = torch.argmax(probs).item()
    confidence = probs[0][predicted_class].item()

    return {
        "sentiment": labels[predicted_class],
        "confidence": confidence,
        "scores": {label: prob.item() for label, prob in zip(labels, probs[0])}
    }

# Example
result = analyze_crypto_sentiment("Bitcoin is going to the moon! HODL!")
# Output: {"sentiment": "Bullish", "confidence": 0.94, ...}
```

**FinBERT for News Headlines:**
```python
from transformers import pipeline

finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")

headlines = [
    "Bitcoin surges past $100K as institutional buying accelerates",
    "SEC delays Bitcoin ETF decision again",
    "Ethereum network upgrade completed successfully"
]

for headline in headlines:
    result = finbert(headline)[0]
    print(f"{headline}: {result['label']} ({result['score']:.3f})")
```

### 3.7 Sentiment Data Providers (Pre-Built)

| Provider | API | Free Tier | Key Feature |
|----------|-----|-----------|-------------|
| **LunarCrush** | `lunarcrush.com/api` | Limited | Social intelligence for 4000+ coins |
| **Santiment** | `api.santiment.net` | Limited free | On-chain + social combined |
| **Augmento** | `api.augmento.ai` | Research | 93 sentiment topics tracked |
| **The TIE** | `thetie.io` | Paid | Institutional sentiment data |
| **Optimae** | `optimae.app` | Coming soon | Twitter + Reddit aggregated |

---

## 4. Memecoin & Altcoin Analysis

### 4.1 Identifying Potential Moonshots Early

**Screening Criteria Pipeline:**
```
Stage 1 - Discovery:
  [x] New pair detected on DEX (DexScreener, Birdeye)
  [x] Contract verified on block explorer
  [x] Liquidity > $10K (filters out honeypots)
  [x] Not a copy/fork of known scam contract

Stage 2 - Safety Check:
  [x] Liquidity locked (check Unicrypt, Team.Finance, PinkSale)
  [x] No mint function in contract (or renounced)
  [x] Top 10 holders < 30% of supply (excluding dead wallets/LP)
  [x] No blacklist/whitelist functions
  [x] Tax < 10% buy/sell
  [x] GoPlus/TokenSniffer safety score > 70

Stage 3 - Growth Signals:
  [x] Holder count growing >5% per hour in first 24h
  [x] Social mentions accelerating (Twitter, Telegram)
  [x] Smart money wallets buying (Nansen/Arkham labels)
  [x] Volume/Market Cap ratio > 0.5 in first 24h
  [x] Organic buy pressure (not single whale)

Stage 4 - Momentum Confirmation:
  [x] Listed on CoinGecko or CoinMarketCap
  [x] Growing DEX volume for 3+ consecutive days
  [x] Positive mentions from crypto influencers
  [x] Community engagement metrics rising
```

### 4.2 On-Chain Metrics That Predict Memecoin Pumps

```python
# Key metrics to track for each token

metrics = {
    # Holder Growth Rate
    "holder_growth_rate": "delta(holders) / holders per hour",
    # >5% hourly in first 48h = strong signal

    # Buy/Sell Ratio
    "buy_sell_ratio": "buy_transactions / sell_transactions",
    # >2.0 = accumulation phase

    # Average Transaction Size Trend
    "avg_tx_size_trend": "current_avg_tx / 24h_avg_tx",
    # Increasing = whales entering

    # Unique Buyers vs Sellers
    "unique_buyer_ratio": "unique_buyers / (unique_buyers + unique_sellers)",
    # >0.6 = broad buying interest

    # DEX Volume Acceleration
    "volume_acceleration": "volume_1h / volume_24h_avg",
    # >3.0 = breakout potential

    # Smart Money Activity
    "smart_money_buys": "count of labeled smart money wallets buying",
    # Any > 0 is significant for new tokens

    # Liquidity Depth
    "liquidity_depth": "total_liquidity_usd / market_cap",
    # >0.1 = healthy, <0.01 = dangerous (easy to rug)
}
```

### 4.3 Whale Wallet Tracking

**Platforms and APIs:**

| Platform | API | Focus | Free Tier |
|----------|-----|-------|-----------|
| **Nansen** | `api.nansen.ai` | Smart Money labels, 500M+ addresses | Limited |
| **Arkham Intelligence** | `api.arkhamintelligence.com` | Entity identification, 10+ chains | Limited free |
| **Whale Alert** | `api.whale-alert.io` | Large transaction alerts | 10 req/min free |
| **Etherscan** | `api.etherscan.io` | Raw wallet data, ERC20 balances | 5 req/sec free |
| **Solscan** | `api.solscan.io` | Solana wallet tracking | Free tier |
| **DeBank** | `open-api.debank.com` | Multi-chain portfolio | 20 req/sec free |

**Whale Alert API Example:**
```python
import requests

API_KEY = "YOUR_WHALE_ALERT_KEY"
url = f"https://api.whale-alert.io/v1/transactions?api_key={API_KEY}&min_value=1000000&currency=btc"

response = requests.get(url)
transactions = response.json()["transactions"]

for tx in transactions:
    print(f"Amount: {tx['amount']} BTC")
    print(f"From: {tx['from']['owner_type']} ({tx['from'].get('owner', 'unknown')})")
    print(f"To: {tx['to']['owner_type']} ({tx['to'].get('owner', 'unknown')})")
    # owner_type: "exchange", "unknown" (whale), etc.
```

**Etherscan Token Holder Analysis:**
```python
import requests

ETHERSCAN_KEY = "YOUR_KEY"
TOKEN_ADDRESS = "0x..."  # ERC20 token contract

# Get top token holders (requires Etherscan Pro plan for API)
# Alternative: scrape token holder chart page
# https://etherscan.io/token/tokenholderchart/{TOKEN_ADDRESS}

# Get token transfers for a wallet
url = f"https://api.etherscan.io/api?module=account&action=tokentx&address={WALLET}&contractaddress={TOKEN_ADDRESS}&sort=desc&apikey={ETHERSCAN_KEY}"
```

### 4.4 Token Holder Distribution Analysis

**Key Distribution Metrics:**
```
Healthy Distribution:
- Top 10 holders (excluding LP/dead): < 30% of supply
- Top 100 holders: < 60% of supply
- Gini coefficient: < 0.7 (lower = more distributed)

Red Flags:
- Single wallet > 5% (non-team/LP) = whale risk
- Team/insider wallets unlocking soon
- Large % held in unlabeled wallets
- Decreasing holder count
```

**Concentration Score Formula:**
```
HHI (Herfindahl-Hirschman Index) = sum(s_i^2) for top N holders
where s_i = share of holder i as decimal

HHI < 0.01 = highly distributed (good)
HHI 0.01-0.10 = moderate concentration
HHI > 0.10 = high concentration (risky)
```

### 4.5 Liquidity Analysis

**DEX Liquidity Health Check:**
```python
# Using DexScreener API
import requests

def analyze_liquidity(chain_id, pair_address):
    url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_address}"
    data = requests.get(url).json()
    pair = data["pairs"][0]

    liquidity = pair["liquidity"]["usd"]
    volume_24h = pair["volume"]["h24"]
    market_cap = pair.get("marketCap", pair.get("fdv", 0))

    # Key ratios
    liq_to_mcap = liquidity / market_cap if market_cap else 0
    vol_to_liq = volume_24h / liquidity if liquidity else 0

    # Price impact estimation
    # For constant product AMM: price_impact = trade_size / (liquidity / 2)

    return {
        "liquidity_usd": liquidity,
        "liq_to_mcap_ratio": liq_to_mcap,  # >0.05 = healthy
        "vol_to_liq_ratio": vol_to_liq,      # 0.5-3.0 = healthy activity
        "is_liquidity_locked": check_lock(pair_address),  # Check Unicrypt/TeamFinance
    }
```

**Rug Pull Detection Checklist:**
```
Contract Analysis:
[ ] Ownership renounced or multi-sig
[ ] No proxy upgradeable pattern (or transparent)
[ ] No hidden mint functions
[ ] No blacklist/pause functions
[ ] Max transaction limits reasonable
[ ] Tax < 10%

Liquidity Analysis:
[ ] LP tokens locked (>6 months minimum)
[ ] LP lock verified on-chain (not just claimed)
[ ] Multiple LP providers (not just deployer)
[ ] No single-sided liquidity removal capability

Holder Analysis:
[ ] Deployer doesn't hold >5% supply
[ ] No connected wallets holding large %
[ ] Token distributed to >500 unique holders

Tools:
- GoPlus API: api.gopluslabs.io/api/v1/token_security/{chain_id}?contract_addresses={address}
- TokenSniffer: tokensniffer.com
- RugDoc: rugdoc.io
- De.Fi Scanner: de.fi/scanner
```

---

## 5. Exchange APIs

### 5.1 Binance API

**Base URLs:**
```
REST API:     https://api.binance.com
WebSocket:    wss://stream.binance.com:9443
Futures REST: https://fapi.binance.com
Futures WS:   wss://fstream.binance.com
Testnet:      https://testnet.binance.vision
Data API:     https://data-api.binance.vision
```

**Key Endpoints:**
```
# Market Data (no auth required)
GET /api/v3/exchangeInfo          # All trading pairs, rules, filters
GET /api/v3/ticker/price          # Latest price for all symbols
GET /api/v3/ticker/24hr           # 24h stats for all symbols
GET /api/v3/klines                # OHLCV candlestick data
GET /api/v3/depth                 # Order book depth
GET /api/v3/trades                # Recent trades
GET /api/v3/aggTrades             # Compressed/aggregate trades

# Account (auth required)
GET /api/v3/account               # Account info, balances
POST /api/v3/order                # Place order
GET /api/v3/openOrders            # Current open orders
GET /api/v3/myTrades              # Trade history

# Futures-specific
GET /fapi/v1/fundingRate          # Funding rate history
GET /fapi/v1/openInterest         # Open interest
GET /fapi/v1/topLongShortPositionRatio  # Long/Short ratio
```

**WebSocket Streams:**
```python
import websocket
import json

# Single stream
ws_url = "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"

# Combined streams
ws_url = "wss://stream.binance.com:9443/stream?streams=btcusdt@kline_1m/ethusdt@kline_1m/btcusdt@depth20@100ms"

# Available streams per symbol:
# {symbol}@trade          - Real-time trades
# {symbol}@kline_{interval} - Candlestick (1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h,1d,3d,1w,1M)
# {symbol}@depth{levels}@{speed}ms - Order book (5,10,20 levels; 100ms or 1000ms)
# {symbol}@miniTicker     - Mini ticker
# {symbol}@ticker         - Full ticker
# {symbol}@bookTicker     - Best bid/ask
# !miniTicker@arr         - All market mini tickers
# !ticker@arr             - All market tickers

def on_message(ws, message):
    data = json.loads(message)
    if data.get('e') == 'kline':
        kline = data['k']
        print(f"Symbol: {kline['s']}, Close: {kline['c']}, Volume: {kline['v']}")

ws = websocket.WebSocketApp(ws_url, on_message=on_message)
ws.run_forever()
```

**Python Library:**
```python
pip install python-binance

from binance.client import Client
from binance import ThreadedWebsocketManager

client = Client(api_key, api_secret)

# Get klines
klines = client.get_klines(symbol='BTCUSDT', interval=Client.KLINE_INTERVAL_1HOUR, limit=500)

# Get new listing info
info = client.get_exchange_info()
symbols = [s['symbol'] for s in info['symbols'] if s['status'] == 'TRADING']

# WebSocket
twm = ThreadedWebsocketManager()
twm.start()
twm.start_kline_socket(callback=handle_kline, symbol='BTCUSDT', interval='1m')
```

**Rate Limits:**
```
REST API:
- 6,000 weight/minute (most endpoints = 1-50 weight)
- 10 orders/second
- 200,000 orders/24h

WebSocket:
- 5 messages/second per connection
- 1,024 streams per connection
- Connection valid for 24 hours
- Max 300 connections per 5 minutes
```

### 5.2 CoinGecko API

**Base URL:** `https://api.coingecko.com/api/v3/`
**Pro URL:** `https://pro-api.coingecko.com/api/v3/`

**Pricing (2026):**
| Plan | Price | Rate Limit | Monthly Calls |
|------|-------|-----------|---------------|
| Demo (Free) | $0 | 30/min | ~43,000 |
| Analyst | $14/mo | 30/min | 500,000 |
| Lite | $59/mo | 300/min | 1,000,000 |
| Pro | $129/mo | 500/min | 3,000,000 |
| Enterprise | Custom | Custom | Custom |

**Key Endpoints:**
```
# No auth required (Demo plan)
GET /ping                                      # Server status
GET /simple/price?ids=bitcoin&vs_currencies=usd  # Simple price
GET /coins/markets?vs_currency=usd&order=market_cap_desc&per_page=250  # Top coins
GET /coins/{id}                                # Detailed coin data
GET /coins/{id}/market_chart?vs_currency=usd&days=365  # Historical chart
GET /coins/{id}/ohlc?vs_currency=usd&days=30   # OHLCV data
GET /search/trending                           # Trending coins
GET /global                                    # Global market data
GET /coins/categories                          # All categories

# GeckoTerminal (DEX data - included free)
GET /onchain/simple/networks/{network}/token_price/{addresses}
GET /onchain/networks/{network}/pools/{address}
GET /onchain/networks/{network}/new_pools
GET /onchain/search/pools?query={query}
GET /onchain/networks/{network}/trending_pools
```

**Python Implementation:**
```python
pip install pycoingecko

from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()

# Get top 250 coins by market cap
markets = cg.get_coins_markets(vs_currency='usd', order='market_cap_desc', per_page=250, page=1)

# Get Bitcoin historical data
history = cg.get_coin_market_chart_by_id(id='bitcoin', vs_currency='usd', days=365)

# Get trending coins
trending = cg.get_search_trending()

# Get OHLCV
ohlcv = cg.get_coin_ohlc_by_id(id='bitcoin', vs_currency='usd', days=30)
```

### 5.3 CoinMarketCap API

**Base URL:** `https://pro-api.coinmarketcap.com/`

**Free Tier (Basic):**
- 10,000 credits/month (~333 calls/day)
- 11 core endpoints
- 30 calls/minute

**Key Free Endpoints:**
```
GET /v1/cryptocurrency/listings/latest    # All coins ranked (10 credits)
GET /v1/cryptocurrency/map                # ID mapping (1 credit)
GET /v1/cryptocurrency/info               # Metadata (1 credit)
GET /v2/cryptocurrency/quotes/latest      # Latest quotes (1 credit)
GET /v1/global-metrics/quotes/latest      # Global stats (1 credit)

# Headers required:
# X-CMC_PRO_API_KEY: your-api-key
```

```python
import requests

CMC_API_KEY = "YOUR_KEY"
url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
params = {"start": 1, "limit": 100, "convert": "USD", "sort": "market_cap"}

response = requests.get(url, headers=headers, params=params)
data = response.json()["data"]

for coin in data:
    print(f"{coin['name']}: ${coin['quote']['USD']['price']:.2f}")
```

### 5.4 DexScreener API

**Base URL:** `https://api.dexscreener.com/`
**Free, no API key required**

**Key Endpoints:**
```
# Token Profiles
GET /token-profiles/latest/v1                     # Latest token profiles
GET /token-boosts/latest/v1                        # Latest boosted tokens
GET /token-boosts/top/v1                           # Top boosted tokens

# DEX Data
GET /latest/dex/pairs/{chainId}/{pairAddresses}    # Get pairs by address
GET /latest/dex/tokens/{tokenAddresses}            # Get token pairs
GET /latest/dex/search?q={query}                   # Search pairs
GET /token-pairs/v1/{chainId}/{tokenAddress}       # Token pairs by chain

# Supported chains: ethereum, bsc, polygon, arbitrum, optimism, avalanche,
#                   solana, base, fantom, cronos, and 80+ more
```

```python
import requests

# Search for a token
def search_dex(query):
    url = f"https://api.dexscreener.com/latest/dex/search?q={query}"
    return requests.get(url).json()

# Get specific pair info
def get_pair(chain_id, pair_address):
    url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_address}"
    data = requests.get(url).json()
    pair = data["pairs"][0]
    return {
        "price_usd": pair["priceUsd"],
        "volume_24h": pair["volume"]["h24"],
        "price_change_24h": pair["priceChange"]["h24"],
        "liquidity_usd": pair["liquidity"]["usd"],
        "txns_24h_buys": pair["txns"]["h24"]["buys"],
        "txns_24h_sells": pair["txns"]["h24"]["sells"],
        "fdv": pair.get("fdv"),
        "pair_created_at": pair.get("pairCreatedAt"),
    }
```

**Limitations:** No historical OHLCV data, no WebSocket, rate limits (undocumented but ~300 req/min), no advanced filtering.

### 5.5 DEX-Specific APIs

**Uniswap (The Graph / Subgraph):**
```graphql
# Uniswap V3 Subgraph
# Endpoint: https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3

{
  pools(first: 10, orderBy: totalValueLockedUSD, orderDirection: desc) {
    id
    token0 { symbol name }
    token1 { symbol name }
    totalValueLockedUSD
    volumeUSD
    feeTier
  }
}

{
  swaps(first: 100, orderBy: timestamp, orderDirection: desc,
    where: { pool: "0x..." }) {
    timestamp
    amount0
    amount1
    amountUSD
    sender
    origin
  }
}
```

**Raydium (Solana):**
```python
# Bitquery API for Raydium data
# Or use Raydium SDK directly

# Via Birdeye API (comprehensive Solana DEX data)
# https://public-api.birdeye.so/
headers = {"X-API-KEY": "YOUR_BIRDEYE_KEY"}
url = "https://public-api.birdeye.so/defi/txs/token?address={token_address}&tx_type=swap"
```

### 5.6 Alternative Data Providers

| Provider | Focus | API | Pricing |
|----------|-------|-----|---------|
| **Kaiko** | Institutional market data | gRPC + REST | Enterprise |
| **CoinAPI** | 400+ exchanges unified | REST + WS | Free: 100 req/day |
| **Amberdata** | On-chain + market data | REST + WS | From $100/mo |
| **CryptoCompare** | Aggregated prices | REST + WS | Free: 100K calls/mo |
| **Bitquery** | Blockchain GraphQL | GraphQL | Free: 10K points/mo |
| **Moralis** | Web3 data | REST | Free: 40K CU/day |
| **Alchemy** | Node + enhanced APIs | REST + WS | Free: 300M CU/mo |
| **QuickNode** | Node infrastructure | RPC + WS | Free: limited |
| **Chainlink** | Price feeds (on-chain) | Smart contract | Free (gas only) |
| **DeFiLlama** | TVL + yields | REST | Free, no key |

### 5.7 CCXT - Unified Exchange Library

```python
pip install ccxt

import ccxt

# Initialize multiple exchanges
binance = ccxt.binance({'apiKey': '...', 'secret': '...'})
coinbase = ccxt.coinbase({'apiKey': '...', 'secret': '...'})
kraken = ccxt.kraken({'apiKey': '...', 'secret': '...'})

# Unified interface across 100+ exchanges
for exchange in [binance, coinbase, kraken]:
    ticker = exchange.fetch_ticker('BTC/USDT')
    print(f"{exchange.id}: ${ticker['last']}")

    # OHLCV data
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=100)

    # Order book
    orderbook = exchange.fetch_order_book('BTC/USDT', limit=20)

    # Place order (auth required)
    # order = exchange.create_limit_buy_order('BTC/USDT', amount, price)

# Cross-exchange arbitrage detection
def find_arbitrage(symbol, exchanges):
    prices = {}
    for ex in exchanges:
        ticker = ex.fetch_ticker(symbol)
        prices[ex.id] = {'bid': ticker['bid'], 'ask': ticker['ask']}

    best_bid = max(prices.items(), key=lambda x: x[1]['bid'])
    best_ask = min(prices.items(), key=lambda x: x[1]['ask'])

    spread = (best_bid[1]['bid'] - best_ask[1]['ask']) / best_ask[1]['ask'] * 100

    if spread > 0.5:  # >0.5% spread after fees
        return {
            "buy_on": best_ask[0],
            "buy_price": best_ask[1]['ask'],
            "sell_on": best_bid[0],
            "sell_price": best_bid[1]['bid'],
            "spread_pct": spread
        }

# CCXT Pro (WebSocket) - paid
# pip install ccxt[pro]
# Provides: watchTicker, watchOrderBook, watchTrades, watchOHLCV
```

---

## 6. Proven Trading Strategies

### 6.1 Mean Reversion Strategies

**Bollinger Band Mean Reversion:**
```python
import pandas as pd
import numpy as np

def bollinger_mean_reversion(df, window=20, num_std=2):
    df['sma'] = df['close'].rolling(window).mean()
    df['std'] = df['close'].rolling(window).std()
    df['upper'] = df['sma'] + (num_std * df['std'])
    df['lower'] = df['sma'] - (num_std * df['std'])
    df['pct_b'] = (df['close'] - df['lower']) / (df['upper'] - df['lower'])

    # Signal generation
    df['signal'] = 0
    df.loc[df['close'] < df['lower'], 'signal'] = 1   # Buy at lower band
    df.loc[df['close'] > df['upper'], 'signal'] = -1  # Sell at upper band

    # Add RSI confirmation
    df['rsi'] = compute_rsi(df['close'], 14)
    df.loc[(df['signal'] == 1) & (df['rsi'] > 40), 'signal'] = 0   # Cancel if RSI not oversold
    df.loc[(df['signal'] == -1) & (df['rsi'] < 60), 'signal'] = 0  # Cancel if RSI not overbought

    return df
```

**Z-Score Mean Reversion (for pairs/spreads):**
```python
def zscore_strategy(series, lookback=20, entry_z=2.0, exit_z=0.5):
    mean = series.rolling(lookback).mean()
    std = series.rolling(lookback).std()
    zscore = (series - mean) / std

    positions = pd.Series(0, index=series.index)
    positions[zscore < -entry_z] = 1     # Long when z-score very negative
    positions[zscore > entry_z] = -1     # Short when z-score very positive
    positions[abs(zscore) < exit_z] = 0  # Exit near mean

    return positions

# Research result: BTC-neutral residual mean reversion achieves Sharpe ~2.3
```

### 6.2 Momentum Strategies

**Dual Momentum (Absolute + Relative):**
```python
def dual_momentum(prices_df, lookback=30, risk_free_rate=0.0):
    """
    prices_df: DataFrame with columns for each asset
    Returns: which asset to hold (or cash if no positive momentum)
    """
    returns = prices_df.pct_change(lookback)

    # Absolute momentum: Is return > risk-free rate?
    abs_momentum = returns.iloc[-1] > risk_free_rate

    # Relative momentum: Which asset has best return?
    best_asset = returns.iloc[-1].idxmax()

    if abs_momentum[best_asset]:
        return best_asset  # Hold best performing asset
    else:
        return "USDT"  # Move to stablecoin
```

**RSI Momentum with Volume Confirmation:**
```python
def rsi_momentum(df, rsi_period=14, vol_ma=20):
    df['rsi'] = compute_rsi(df['close'], rsi_period)
    df['vol_ma'] = df['volume'].rolling(vol_ma).mean()
    df['vol_ratio'] = df['volume'] / df['vol_ma']

    # Buy: RSI crossing above 50 with above-average volume
    df['signal'] = 0
    df.loc[(df['rsi'] > 50) & (df['rsi'].shift(1) <= 50) & (df['vol_ratio'] > 1.5), 'signal'] = 1

    # Sell: RSI crossing below 50 or RSI > 80
    df.loc[(df['rsi'] < 50) & (df['rsi'].shift(1) >= 50), 'signal'] = -1
    df.loc[df['rsi'] > 80, 'signal'] = -1

    return df
```

### 6.3 Arbitrage Opportunities

**Types of Crypto Arbitrage:**
```
1. Cross-Exchange Arbitrage:
   - Buy BTC on Exchange A at $99,500
   - Sell BTC on Exchange B at $100,000
   - Profit: $500 minus fees (~0.1% * 2 = ~$200)
   - Net: ~$300 per BTC
   - Challenge: Transfer time, requires pre-funded accounts

2. Triangular Arbitrage (single exchange):
   - BTC/USDT -> ETH/BTC -> ETH/USDT
   - Example: Buy 1 ETH for 3000 USDT, convert ETH->BTC->USDT
   - If BTC/ETH and BTC/USDT misprice: profit
   - Must complete in <1 second

3. DEX-CEX Arbitrage:
   - Price on Uniswap vs Binance differs
   - Buy on cheaper, sell on more expensive
   - Challenge: Gas fees on DEX, timing

4. Funding Rate Arbitrage (Futures):
   - When funding rate is very positive (+0.1%/8h):
     Buy spot, short perpetual futures
     Collect funding rate as risk-free yield
   - Annualized: 0.1% * 3 * 365 = 109.5% APR
```

**Cross-Exchange Arbitrage Implementation:**
```python
import ccxt
import asyncio

exchanges = {
    'binance': ccxt.binance(),
    'coinbase': ccxt.coinbase(),
    'kraken': ccxt.kraken(),
    'bybit': ccxt.bybit(),
}

async def scan_arbitrage(symbol='BTC/USDT', min_spread_pct=0.3):
    tickers = {}
    for name, exchange in exchanges.items():
        try:
            ticker = exchange.fetch_ticker(symbol)
            tickers[name] = {
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'bid_volume': ticker['bidVolume'],
                'ask_volume': ticker['askVolume'],
            }
        except:
            continue

    opportunities = []
    for buy_ex, buy_data in tickers.items():
        for sell_ex, sell_data in tickers.items():
            if buy_ex == sell_ex:
                continue

            spread = (sell_data['bid'] - buy_data['ask']) / buy_data['ask'] * 100

            if spread > min_spread_pct:
                # Estimate fees
                buy_fee = 0.1   # 0.1% typical
                sell_fee = 0.1
                net_spread = spread - buy_fee - sell_fee

                if net_spread > 0:
                    opportunities.append({
                        'buy_exchange': buy_ex,
                        'buy_price': buy_data['ask'],
                        'sell_exchange': sell_ex,
                        'sell_price': sell_data['bid'],
                        'gross_spread_pct': spread,
                        'net_spread_pct': net_spread,
                        'max_size': min(buy_data['ask_volume'], sell_data['bid_volume'])
                    })

    return sorted(opportunities, key=lambda x: x['net_spread_pct'], reverse=True)
```

### 6.4 DCA with AI Timing

**Smart DCA Strategy:**
```python
def smart_dca(price, fear_greed_index, rsi, base_amount=100):
    """
    Adjusts DCA amount based on market conditions.
    Buy more when fearful/oversold, less when greedy/overbought.
    """
    # Fear multiplier (0-100 index, lower = more fear)
    if fear_greed_index < 20:       # Extreme Fear
        fear_mult = 2.0
    elif fear_greed_index < 40:     # Fear
        fear_mult = 1.5
    elif fear_greed_index < 60:     # Neutral
        fear_mult = 1.0
    elif fear_greed_index < 80:     # Greed
        fear_mult = 0.5
    else:                            # Extreme Greed
        fear_mult = 0.25

    # RSI multiplier
    if rsi < 30:
        rsi_mult = 1.5
    elif rsi < 40:
        rsi_mult = 1.2
    elif rsi > 70:
        rsi_mult = 0.5
    elif rsi > 80:
        rsi_mult = 0.25
    else:
        rsi_mult = 1.0

    # Combined multiplier (weighted average)
    multiplier = 0.6 * fear_mult + 0.4 * rsi_mult

    buy_amount = base_amount * multiplier
    return round(buy_amount, 2)

# Example: base $100 DCA
# Extreme Fear + RSI 25: $100 * (0.6*2.0 + 0.4*1.5) = $180
# Extreme Greed + RSI 85: $100 * (0.6*0.25 + 0.4*0.25) = $25
```

### 6.5 Risk Management Formulas

#### Kelly Criterion
```
Full Kelly: f* = (W * R - L) / R

Where:
  f* = fraction of capital to risk
  W  = win rate (decimal, e.g., 0.55)
  L  = loss rate (1 - W = 0.45)
  R  = reward/risk ratio (avg_win / avg_loss)

Example:
  Win rate = 55%, Avg win = $1,500, Avg loss = $1,000
  R = 1.5, W = 0.55, L = 0.45
  f* = (0.55 * 1.5 - 0.45) / 1.5 = 0.25 (25%)

IMPORTANT: Use fractional Kelly for crypto:
  Quarter Kelly = f* / 4 = 6.25%  (recommended for crypto)
  Half Kelly    = f* / 2 = 12.5%  (moderate)
  Tenth Kelly   = f* / 10 = 2.5%  (conservative, good starting point)
```

#### Position Sizing
```python
def calculate_position_size(account_balance, risk_pct, entry_price, stop_loss_price):
    """
    Calculate position size based on fixed risk percentage.

    account_balance: Total account value in USD
    risk_pct: Percentage of account to risk (e.g., 0.02 for 2%)
    entry_price: Planned entry price
    stop_loss_price: Stop loss price
    """
    risk_amount = account_balance * risk_pct
    price_risk = abs(entry_price - stop_loss_price)
    price_risk_pct = price_risk / entry_price

    position_size_usd = risk_amount / price_risk_pct
    position_size_units = position_size_usd / entry_price

    # Cap at max position size (e.g., 20% of account)
    max_position = account_balance * 0.20
    position_size_usd = min(position_size_usd, max_position)

    return {
        "risk_amount": risk_amount,
        "position_size_usd": position_size_usd,
        "position_size_units": position_size_units,
        "leverage_needed": position_size_usd / account_balance
    }

# Example: $10,000 account, 2% risk, BTC at $100,000, stop at $97,000
# Risk amount: $200
# Price risk: 3%
# Position size: $200 / 0.03 = $6,667 (~0.0667 BTC)
```

#### Maximum Drawdown Control
```python
def should_reduce_exposure(current_drawdown, max_allowed_drawdown=0.15):
    """
    Progressive risk reduction as drawdown increases.

    current_drawdown: Current drawdown from peak (e.g., 0.08 = 8%)
    max_allowed_drawdown: Maximum allowed drawdown (e.g., 15%)
    """
    if current_drawdown >= max_allowed_drawdown:
        return {"action": "STOP_TRADING", "exposure_mult": 0.0}

    # Linear reduction: at 50% of max drawdown, reduce to 50% exposure
    exposure_mult = 1.0 - (current_drawdown / max_allowed_drawdown)
    exposure_mult = max(exposure_mult, 0.1)  # Minimum 10% exposure

    return {"action": "REDUCE", "exposure_mult": exposure_mult}
```

### 6.6 Backtesting Frameworks

**Framework Comparison:**

| Framework | Speed | Live Trading | Learning Curve | Best For |
|-----------|-------|-------------|----------------|----------|
| **VectorBT** | Fastest (vectorized) | Via adapters | Medium | Large-scale research |
| **Backtrader** | Medium (event-driven) | Built-in broker support | Easy | Swing trading |
| **Zipline-Reloaded** | Medium | Via extensions | Medium | Portfolio strategies |
| **Backtesting.py** | Fast | No | Easiest | Quick prototyping |
| **NautilusTrader** | Very fast (Rust core) | Built-in | Hard | Professional HFT |
| **QuantConnect/Lean** | Cloud-based | Yes | Medium | Multi-asset |

**VectorBT Example:**
```python
pip install vectorbt

import vectorbt as vbt
import pandas as pd

# Download data
btc_price = vbt.YFData.download('BTC-USD', period='2y').get('Close')

# RSI strategy
rsi = vbt.RSI.run(btc_price, window=14)
entries = rsi.rsi_crossed_below(30)  # Buy when RSI < 30
exits = rsi.rsi_crossed_above(70)    # Sell when RSI > 70

# Run backtest
portfolio = vbt.Portfolio.from_signals(
    btc_price,
    entries,
    exits,
    init_cash=10000,
    fees=0.001,  # 0.1% fee
    freq='1D'
)

# Results
print(f"Total Return: {portfolio.total_return():.2%}")
print(f"Sharpe Ratio: {portfolio.sharpe_ratio():.2f}")
print(f"Max Drawdown: {portfolio.max_drawdown():.2%}")
print(f"Win Rate: {portfolio.trades.win_rate():.2%}")
portfolio.plot().show()
```

**Backtrader Example:**
```python
pip install backtrader

import backtrader as bt

class MeanReversionStrategy(bt.Strategy):
    params = (('bb_period', 20), ('bb_dev', 2), ('rsi_period', 14),)

    def __init__(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close, period=self.params.bb_period, devfactor=self.params.bb_dev
        )
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def next(self):
        if not self.position:
            if self.data.close[0] < self.bb.bot[0] and self.rsi[0] < 30:
                self.buy(size=self.broker.getcash() * 0.95 / self.data.close[0])
        else:
            if self.data.close[0] > self.bb.mid[0] or self.rsi[0] > 70:
                self.close()

cerebro = bt.Cerebro()
cerebro.addstrategy(MeanReversionStrategy)
cerebro.adddata(bt.feeds.PandasData(dataname=df))
cerebro.broker.setcash(10000)
cerebro.broker.setcommission(commission=0.001)
cerebro.run()
cerebro.plot()
```

---

## 7. Real-time Data Architecture

### 7.1 Recommended Architecture

```
                        +-------------------+
                        |   Data Sources    |
                        |  (Exchanges, DEX, |
                        |   Social, News)   |
                        +--------+----------+
                                 |
                    WebSocket / REST / gRPC
                                 |
                    +------------v-----------+
                    |    Ingestion Layer     |
                    |  (Python AsyncIO /     |
                    |   Node.js Workers)     |
                    +------------+-----------+
                                 |
                    +------------v-----------+
                    |    Message Queue       |
                    |  (Apache Kafka /       |
                    |   Redis Streams)       |
                    +------+-----+----------+
                           |     |
              +------------+     +------------+
              |                               |
    +---------v----------+     +--------------v---------+
    |  Stream Processing |     |   Batch Processing     |
    |  (Faust / Kafka    |     |   (Spark / Pandas)     |
    |   Streams)         |     |                        |
    +---------+----------+     +--------------+---------+
              |                               |
    +---------v----------+     +--------------v---------+
    |  Hot Storage        |     |  Cold Storage          |
    |  (Redis / TimescaleDB)   |  (PostgreSQL / S3 /    |
    |  (real-time data)   |     |   ClickHouse)          |
    +----+-----+----------+     +--------------------------+
         |     |
    +----v-----v----------+
    |   Application Layer |
    |  (FastAPI / Django)  |
    |  ML Models, Alerts,  |
    |  Trading Signals     |
    +---------+-----------+
              |
    +---------v-----------+
    |   Frontend / Bot    |
    |  (React / Telegram) |
    +---------+-----------+
```

### 7.2 WebSocket Feed Implementation

```python
import asyncio
import json
import websockets
from collections import defaultdict

class CryptoDataPipeline:
    def __init__(self):
        self.subscribers = defaultdict(list)
        self.latest_prices = {}

    async def binance_stream(self, symbols):
        """Connect to Binance WebSocket for real-time price data."""
        streams = "/".join([f"{s.lower()}@kline_1m" for s in symbols])
        url = f"wss://stream.binance.com:9443/stream?streams={streams}"

        async with websockets.connect(url) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)

                if 'data' in data:
                    kline = data['data']['k']
                    event = {
                        'symbol': kline['s'],
                        'open': float(kline['o']),
                        'high': float(kline['h']),
                        'low': float(kline['l']),
                        'close': float(kline['c']),
                        'volume': float(kline['v']),
                        'timestamp': kline['t'],
                        'is_closed': kline['x'],  # Is this candle closed?
                    }

                    self.latest_prices[event['symbol']] = event
                    await self.notify_subscribers(event['symbol'], event)

    async def notify_subscribers(self, symbol, data):
        for callback in self.subscribers[symbol]:
            await callback(data)

    def subscribe(self, symbol, callback):
        self.subscribers[symbol].append(callback)

# Usage
pipeline = CryptoDataPipeline()

async def on_btc_update(data):
    print(f"BTC: ${data['close']:,.2f} | Vol: {data['volume']:,.2f}")
    if data['is_closed']:
        # Candle closed - run analysis
        await run_indicators(data)

pipeline.subscribe('BTCUSDT', on_btc_update)
asyncio.run(pipeline.binance_stream(['BTCUSDT', 'ETHUSDT', 'SOLUSDT']))
```

### 7.3 Kafka-Based Pipeline

```python
# Producer: Ingest exchange data into Kafka
pip install kafka-python

from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    compression_type='lz4',
    batch_size=16384,
    linger_ms=10,
)

# Send price updates to Kafka
def ingest_price(symbol, price_data):
    producer.send(
        topic='crypto-prices',
        key=symbol.encode('utf-8'),
        value={
            'symbol': symbol,
            'price': price_data['close'],
            'volume': price_data['volume'],
            'timestamp': price_data['timestamp'],
        }
    )

# Consumer: Process from Kafka
from kafka import KafkaConsumer

consumer = KafkaConsumer(
    'crypto-prices',
    bootstrap_servers=['localhost:9092'],
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    group_id='signal-generator',
    auto_offset_reset='latest',
)

for message in consumer:
    data = message.value
    # Run ML model, generate signals, store results
    signal = generate_trading_signal(data)
    if signal:
        execute_or_alert(signal)
```

### 7.4 Redis for Hot Data Cache

```python
pip install redis

import redis
import json

r = redis.Redis(host='localhost', port=6379, db=0)

class HotDataCache:
    def __init__(self, redis_client):
        self.r = redis_client

    def update_price(self, symbol, price_data):
        """Store latest price with 60s TTL."""
        self.r.setex(
            f"price:{symbol}",
            60,
            json.dumps(price_data)
        )

        # Store in sorted set for time series (last 24h)
        self.r.zadd(
            f"prices:{symbol}",
            {json.dumps(price_data): price_data['timestamp']}
        )
        # Trim to last 24 hours
        cutoff = price_data['timestamp'] - 86400000
        self.r.zremrangebyscore(f"prices:{symbol}", '-inf', cutoff)

    def get_latest_price(self, symbol):
        data = self.r.get(f"price:{symbol}")
        return json.loads(data) if data else None

    def get_price_history(self, symbol, minutes=60):
        cutoff = int(time.time() * 1000) - (minutes * 60 * 1000)
        data = self.r.zrangebyscore(f"prices:{symbol}", cutoff, '+inf')
        return [json.loads(d) for d in data]

    def publish_signal(self, signal):
        """Pub/Sub for real-time signal distribution."""
        self.r.publish('trading-signals', json.dumps(signal))
```

### 7.5 TimescaleDB for Time Series Storage

```sql
-- TimescaleDB (PostgreSQL extension) for OHLCV data

CREATE TABLE ohlcv (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      DOUBLE PRECISION
);

-- Convert to hypertable
SELECT create_hypertable('ohlcv', 'time');

-- Create continuous aggregates for different timeframes
CREATE MATERIALIZED VIEW ohlcv_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    first(open, time) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, time) AS close,
    sum(volume) AS volume
FROM ohlcv
GROUP BY bucket, symbol;

-- Efficient queries
SELECT * FROM ohlcv
WHERE symbol = 'BTCUSDT'
AND time > NOW() - INTERVAL '7 days'
ORDER BY time DESC;
```

### 7.6 Docker Compose for Development Stack

```yaml
version: '3.8'
services:
  # Message Queue
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    ports:
      - "2181:2181"

  # Hot Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # Time Series DB
  timescaledb:
    image: timescale/timescaledb:latest-pg15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: password
      POSTGRES_DB: crypto_data

  # Monitoring
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
```

### 7.7 Data Quality & Normalization

```python
class DataNormalizer:
    """Normalize data from different exchanges to a unified schema."""

    UNIFIED_SCHEMA = {
        'timestamp': int,      # Unix milliseconds
        'symbol': str,         # Unified format: BTC/USDT
        'exchange': str,       # binance, coinbase, etc.
        'open': float,
        'high': float,
        'low': float,
        'close': float,
        'volume': float,       # Base asset volume
        'quote_volume': float, # Quote asset volume
        'trades': int,         # Number of trades
    }

    SYMBOL_MAP = {
        # Binance format -> unified
        'BTCUSDT': 'BTC/USDT',
        'ETHUSDT': 'ETH/USDT',
        # Coinbase format -> unified
        'BTC-USD': 'BTC/USD',
        'ETH-USD': 'ETH/USD',
    }

    def normalize_binance(self, kline):
        return {
            'timestamp': kline[0],
            'symbol': self.SYMBOL_MAP.get(kline['s'], kline['s']),
            'exchange': 'binance',
            'open': float(kline[1]),
            'high': float(kline[2]),
            'low': float(kline[3]),
            'close': float(kline[4]),
            'volume': float(kline[5]),
            'quote_volume': float(kline[7]),
            'trades': int(kline[8]),
        }

    def validate(self, data):
        """Validate data quality."""
        checks = {
            'timestamp_valid': data['timestamp'] > 0,
            'price_positive': all(data[k] > 0 for k in ['open','high','low','close']),
            'hloc_consistent': data['high'] >= data['low'],
            'high_gte_open_close': data['high'] >= max(data['open'], data['close']),
            'low_lte_open_close': data['low'] <= min(data['open'], data['close']),
            'volume_positive': data['volume'] >= 0,
        }
        return all(checks.values()), checks
```

---

## Appendix A: Python Libraries Summary

```
# Core Data & ML
pip install pandas numpy scipy scikit-learn xgboost lightgbm

# Deep Learning
pip install torch pytorch-forecasting pytorch-lightning darts

# Technical Analysis
pip install ta-lib pandas-ta stockstats finta

# Exchange APIs
pip install python-binance ccxt pycoingecko

# Sentiment Analysis
pip install transformers nltk textblob vaderSentiment praw snscrape telethon

# Backtesting
pip install vectorbt backtrader backtesting zipline-reloaded

# Data Pipeline
pip install kafka-python redis websockets aiohttp asyncio

# Database
pip install psycopg2-binary sqlalchemy timescaledb

# Web Framework
pip install fastapi uvicorn celery

# Visualization
pip install plotly dash matplotlib mplfinance
```

## Appendix B: Free API Quick Reference

| API | Rate Limit (Free) | Auth | Endpoint |
|-----|-------------------|------|----------|
| Binance Market Data | 6000 weight/min | None for public | api.binance.com |
| CoinGecko Demo | 30/min | API key (free) | api.coingecko.com |
| CoinMarketCap Basic | 333/day | API key (free) | pro-api.coinmarketcap.com |
| DexScreener | ~300/min | None | api.dexscreener.com |
| Alternative.me F&G | 60/min | None | api.alternative.me |
| Etherscan | 5/sec | API key (free) | api.etherscan.io |
| CoinAPI | 100/day | API key (free) | rest.coinapi.io |
| DeFiLlama | Unlimited | None | api.llama.fi |
| Whale Alert | 10/min | API key (free) | api.whale-alert.io |
| CryptoCompare | 100K/mo | API key (free) | min-api.cryptocompare.com |
| Reddit (PRAW) | 60/min | OAuth | oauth.reddit.com |
| The Graph | 100K/mo | API key (free) | api.thegraph.com |

## Appendix C: Key Mathematical Models

### Sharpe Ratio
```
Sharpe = (R_p - R_f) / sigma_p
Where:
  R_p = portfolio return
  R_f = risk-free rate
  sigma_p = standard deviation of portfolio returns

Good: > 1.0, Great: > 2.0, Exceptional: > 3.0
```

### Sortino Ratio (better for crypto - only penalizes downside)
```
Sortino = (R_p - R_f) / sigma_d
Where sigma_d = standard deviation of negative returns only
```

### Maximum Drawdown
```
MDD = (Trough - Peak) / Peak
Track continuously: MDD_t = min(0, P_t / max(P_0...P_t) - 1)
```

### Calmar Ratio
```
Calmar = Annualized Return / Maximum Drawdown
Good: > 1.0
```

### Information Ratio
```
IR = (R_p - R_b) / Tracking Error
Where R_b = benchmark return (e.g., BTC buy-and-hold)
```

### Value at Risk (VaR)
```
Historical VaR (95%): Sort returns, take 5th percentile
Parametric VaR: VaR = mu - z * sigma
  (z = 1.645 for 95%, 2.326 for 99%)
```

---

*Last updated: February 17, 2026*
*Research compiled for BTC Seer platform development*

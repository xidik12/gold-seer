# DexScreener API Research
*Researched: 2026-02-18*

## Base URL
`https://api.dexscreener.com`

## All Known Endpoints

### Token/Pair Data (Free, ~300 req/min)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/latest/dex/search?q={query}` | GET | Search pairs/tokens across all DEXs and chains |
| `/latest/dex/pairs/{chainId}/{pairAddress}` | GET | Get pair data by chain and pair address |
| `/token-pairs/v1/{chainId}/{tokenAddress}` | GET | Get all trading pairs for a specific token |
| `/tokens/v1/{chainId}/{tokenAddresses}` | GET | Get token data (supports multiple, max 30) |

### Token Profiles & Boosts (~60 req/min)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/token-profiles/latest/v1` | GET | Get latest token profiles |
| `/token-boosts/latest/v1` | GET | Get latest boosted tokens |
| `/token-boosts/top/v1` | GET | Get top boosted tokens |
| `/community-takeovers/latest/v1` | GET | Get latest community takeovers |
| `/ads/latest/v1` | GET | Get latest ads |
| `/orders/v1/{chainId}/{tokenAddress}` | GET | Get orders for specific token |

## Search Endpoint Details

**URL:** `GET https://api.dexscreener.com/latest/dex/search?q={query}`

**Query parameter `q`:** Can be token symbol, pair (e.g., "SOL/USDC"), token name, or token address.

**Response format:**
```json
{
  "schemaVersion": "text",
  "pairs": [
    {
      "chainId": "solana",
      "dexId": "raydium",
      "url": "https://dexscreener.com/...",
      "pairAddress": "0x...",
      "labels": ["v3"],
      "baseToken": {
        "address": "0x...",
        "name": "Token Name",
        "symbol": "TKN"
      },
      "quoteToken": {
        "address": "0x...",
        "name": "USD Coin",
        "symbol": "USDC"
      },
      "priceNative": "1.234",
      "priceUsd": "1.23",
      "txns": {
        "h24": { "buys": 1500, "sells": 800 },
        "h6": { "buys": 400, "sells": 200 },
        "h1": { "buys": 50, "sells": 30 }
      },
      "volume": { "h24": 5000000, "h6": 1200000, "h1": 200000 },
      "priceChange": { "h24": 5.5, "h6": 2.1, "h1": 0.3 },
      "liquidity": { "usd": 1000000, "base": 500000, "quote": 500000 },
      "fdv": 50000000,
      "marketCap": 30000000,
      "pairCreatedAt": 1700000000000,
      "info": {
        "imageUrl": "https://...",
        "websites": [{ "url": "https://..." }],
        "socials": [{ "platform": "twitter", "handle": "token" }]
      },
      "boosts": { "active": 5 }
    }
  ]
}
```

## Trending: Organic vs Paid Boosts

### Organic Trending (Website Only - No Free API Endpoint)
DexScreener's trending on the website is **organic**, determined by a proprietary algorithm:
- **Market Activity:** Volume, Liquidity, Transactions, Unique makers, Holders
- **Community Engagement:** Visitor traffic, community reactions (emojis)
- **Trust & Credibility:** Verified info, security audits get boosts

**There is NO free API endpoint for organic trending.** The trending page on the website uses internal APIs.

### Plugin-Based Trending (via elizaos plugin)
The `plugin-dexscreener` ElizaOS plugin implements a `getTrending(params)` method with timeframe support (1h, 6h, 24h), but this may scrape/aggregate rather than use an official endpoint.

### Token Boosts (Paid Promotion - Has API)
- `/token-boosts/latest/v1` - Tokens that PAID to be boosted
- `/token-boosts/top/v1` - Top paid boosts
- These are NOT organic trending; they are paid promotions

## Rate Limits
- **Most endpoints:** 300 requests/minute
- **Profile/boost endpoints:** 60 requests/minute
- **No API key required** for basic endpoints

## Key Takeaway for BTC Seer
- Search endpoint is powerful and FREE - can search any token/pair
- No auth needed for basic data endpoints
- Organic trending is NOT available via API (only paid boosts)
- For "trending" features, we need to build our own scoring algorithm using volume/txns/price change data from the search/pairs endpoints
- Rate limits are generous (300/min) compared to CoinGecko (30/min)

## Sources
- https://docs.dexscreener.com/api/reference
- https://docs.dexscreener.com/trending
- https://github.com/elizaos-plugins/plugin-dexscreener
- https://github.com/nixonjoshua98/dexscreener

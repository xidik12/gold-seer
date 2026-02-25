# CoinGecko API Research
*Researched: 2026-02-18*

## Can You Get a Free Demo API Key?

**YES.** CoinGecko offers a free "Demo" plan at zero cost.

### How to Sign Up
1. Go to https://www.coingecko.com/en/api/pricing
2. Sign up for a CoinGecko account (free)
3. Access the Developer Dashboard
4. Create a Demo API key

## Rate Limits

### Demo Plan (FREE)
- **Rate Limit:** ~30 calls/minute (varies with traffic)
- **Monthly Cap:** 10,000 calls/month
- **Base URL:** `https://api.coingecko.com/api/v3/`
- **Header:** `x-cg-demo-api-key` (or query param `x_cg_demo_api_key`)

### Analyst Plan ($129/month)
- **Rate Limit:** 500 calls/minute
- **Monthly Cap:** 500,000 calls/month
- **Base URL:** `https://pro-api.coingecko.com/api/v3/`
- **Header:** `x-cg-pro-api-key`
- **Extras:** 60+ endpoints, historical/NFT/DeFi data

### Lite Plan ($499/month)
- **Rate Limit:** 500 calls/minute
- **Monthly Cap:** 2,000,000 calls/month

### Enterprise Plan (Custom)
- Custom credits, commercial use, higher rate limits

## Authentication

### Demo API (Free)
```
Header: x-cg-demo-api-key: YOUR_DEMO_KEY
OR
Query: ?x_cg_demo_api_key=YOUR_DEMO_KEY
Base URL: https://api.coingecko.com/api/v3/
```

### Pro API (Paid)
```
Header: x-cg-pro-api-key: YOUR_PRO_KEY
OR
Query: ?x_cg_pro_api_key=YOUR_PRO_KEY
Base URL: https://pro-api.coingecko.com/api/v3/
```

**IMPORTANT:** Using the wrong base URL for your key type causes auth failures:
- Demo key + pro-api.coingecko.com = Error 10011
- Pro key + api.coingecko.com = Error 10010

## Common Error Codes
| Code | Meaning |
|------|---------|
| 10002 | Missing API credentials |
| 10010 | Incorrect Pro API key (wrong base URL?) |
| 10011 | Incorrect Demo key (wrong base URL?) |
| 429 | Rate limit exceeded |
| 10005 | Endpoint restricted to paid plans |

## Key Takeaway for BTC Seer
- 10,000 calls/month = ~333 calls/day = ~14 calls/hour
- Enough for periodic price checks but NOT real-time polling
- Should cache aggressively and batch requests
- For real-time needs, consider WebSocket on paid plan or alternative free sources

## Sources
- https://docs.coingecko.com/docs/setting-up-your-api-key
- https://docs.coingecko.com/reference/common-errors-rate-limit
- https://support.coingecko.com/hc/en-us/articles/4538771776153
- https://www.coingecko.com/en/api/pricing

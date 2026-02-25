#!/usr/bin/env python3
"""Replace BTC/Bitcoin/crypto vocabulary with Gold equivalents across all locales."""
import json
import os
import re

LOCALES_DIR = os.path.dirname(os.path.abspath(__file__))

# Replacements that apply to string VALUES only (not keys)
# Order matters - longer/more specific patterns first
REPLACEMENTS = [
    # Specific phrases first
    ("BTC/USDT", "XAU/USD"),
    ("BTC / USD", "XAU / USD"),
    ("BTC/USD", "XAU/USD"),
    ("BTC/Gold", "Gold/USD"),
    ("BTC/M2", "Gold/M2"),
    ("BTC/SPX", "Gold/SPX"),
    ("BTC Price", "Gold Price"),
    ("BTC price", "Gold price"),
    ("BTC Chart", "Gold Chart"),
    ("BTC Dominance", "Gold Dominance"),
    ("BTC Needed", "Gold Needed"),
    ("BTC Season", "Gold Season"),
    ("BTC season", "Gold season"),
    ("BTC in Gold (oz)", "Gold Price (oz)"),
    ("btcPrice", "goldPrice"),  # This is a display value, not a key
    ("Total BTC", "Total Gold"),
    ("per BTC", "per oz"),
    ("0.1 BTC", "5 oz"),
    ("0.133 BTC", "6.5 oz"),
    ("1000+ BTC", "large reserves"),
    ("Reward drops from {{from}} to {{to}} BTC", "Rate changes from {{from}} to {{to}}"),
    ("Next Halving", "Next FOMC Meeting"),
    ("halvings precede significant bull runs", "rate decisions precede significant market moves"),
    ("Bitcoin Power Law model", "Gold Power Law model"),
    ("Bitcoin Milestones", "Gold Milestones"),
    ("Bitcoin wins", "Gold wins"),
    ("Bitcoin Market Share", "Gold Market Share"),
    ("Bitcoin event every ~4 years that cuts block rewards in half", "Federal Reserve meeting every 6 weeks that sets interest rates"),
    ("Bitcoin is heavily overbought", "Gold is heavily overbought"),
    ("Bitcoin is overbought", "Gold is overbought"),
    ("Bitcoin is oversold", "Gold is oversold"),
    ("Bitcoin is extremely oversold", "Gold is extremely oversold"),
    ("Bitcoin went UP", "Gold went UP"),
    ("Bitcoin went DOWN", "Gold went DOWN"),
    ("Bitcoin dominates the crypto market", "Gold dominates the precious metals market"),
    ("Bitcoin has a moderate market share", "Gold has a moderate market share"),
    ("Bitcoin's share is low", "Gold's share is low"),
    ("Bitcoin is MORE THAN", "Gold is MORE THAN"),
    ("Bitcoin is well above", "Gold is well above"),
    ("Bitcoin is above", "Gold is above"),
    ("Bitcoin is slightly below", "Gold is slightly below"),
    ("Bitcoin is significantly below", "Gold is significantly below"),
    ("Bitcoin still has significant room", "Gold still has significant room"),
    ("Bitcoin is extremely overbought", "Gold is extremely overbought"),
    ("Bitcoin is extremely oversold", "Gold is extremely oversold"),
    ("Bitcoin may struggle", "Gold may struggle"),
    ("Bitcoin should find buyers", "Gold should find buyers"),
    ("Bitcoin stops falling", "Gold stops falling"),
    ("Bitcoin price", "Gold price"),
    ("how much Bitcoin is being traded", "how much Gold is being traded"),
    ("Bitcoin's price trajectory", "Gold's price trajectory"),
    ("Bitcoin's long-term price trajectory", "Gold's long-term price trajectory"),
    ("BTC's price follows", "Gold's price follows"),
    ("BTC's price", "Gold's price"),
    ("whether Bitcoin is at a cycle top", "whether Gold is at a cycle top"),
    ("every major Bitcoin top", "every major Gold top"),
    ("What is Bitcoin?", "What is Gold?"),
    ("Bitcoin is a decentralized digital currency that operates without a central bank or single administrator. It was created in 2009 by an anonymous person/group known as Satoshi Nakamoto.", "Gold is a precious metal that has served as a store of value and medium of exchange for thousands of years. It is traded globally under the symbol XAU/USD."),
    ("buying and selling Bitcoin", "buying and selling Gold"),
    ("Buy/sell actual Bitcoin", "Buy/sell actual Gold"),
    ("track Bitcoin's price", "track Gold's price"),
    ("What Moves Bitcoin's Price?", "What Moves Gold's Price?"),
    ("new BTC created per block is cut in half. Reduces supply, historically bullish", "the Fed sets interest rates affecting dollar strength and Gold demand"),
    ("Large holders (1000+ BTC) moving coins to/from exchanges can signal buying or selling", "Central banks buying or selling gold reserves can signal major market shifts"),
    ("BTC at $97,000 with 19.8M coins = ~$1.92 trillion market cap", "Gold has a total market cap of approximately $13 trillion"),
    ("A crypto wallet stores your private keys — the passwords that prove you own your Bitcoin", "A broker account is your gateway to trading Gold in the global markets"),
    ("Hot wallet:", "Online broker:"),
    ("Connected to internet (exchange accounts, mobile apps). Convenient but less secure.", "Web-based trading platforms (MT4/MT5, TradingView). Convenient with instant access."),
    ("Cold wallet:", "Physical gold:"),
    ("Offline hardware devices (Ledger, Trezor). Most secure for large holdings.", "Physical bars and coins stored in secure vaults. Most secure for large holdings."),
    ("\"Not your keys, not your coins\" — if the exchange gets hacked, you lose your funds. Self-custody is safest for large amounts.", "Choose a regulated broker with proper licensing. For large holdings, consider allocated physical gold in secure vaults."),
    ("What is a Wallet?", "What is a Broker Account?"),
    ("Buy Bitcoin and hold", "Buy Gold and hold"),
    ("held BTC for 4+ years", "held Gold for 4+ years"),
    ("buy more BTC when cheap", "buy more Gold when cheap"),
    ("where BTC repeatedly bounces", "where Gold repeatedly bounces"),
    ("If price drops to $95K, it auto-sells. Max loss = $2,000 per BTC", "If price drops to $1,900/oz, it auto-sells. Max loss = $100 per oz"),
    ("Buy at $97,000, set take-profit at $103,000. Locks in $6,000 profit per BTC", "Buy at $2,000/oz, set take-profit at $2,060/oz. Locks in $60 profit per oz"),
    ("Buy at $97,000, set stop-loss at $95,000", "Buy at $2,000/oz, set stop-loss at $1,900/oz"),
    ("Price rises from $97K to $103K, stop follows to $99,910", "Price rises from $2,000 to $2,060, stop follows to $1,998"),
    ("$97,000", "$2,000/oz"),
    ("$96,000", "$1,950/oz"),
    ("$95,000", "$1,900/oz"),
    ("$95,500", "$1,920/oz"),
    ("$94,800", "$1,895/oz"),
    ("$95,200", "$1,905/oz"),
    ("$99,000", "$2,040/oz"),
    ("$103,000", "$2,060/oz"),
    ("$50K, $100K", "$1,500, $2,000"),
    ("$94,800-$95,200", "$1,895-$1,905"),
    ("$95,000 exactly", "$1,900 exactly"),
    ("Entry: $2,000/oz. Stop-loss: $1,950/oz. Risk per BTC = $1,000", "Entry: $2,000/oz. Stop-loss: $1,950/oz. Risk per oz = $50"),
    ("Position size: $100 / $1,000 =", "Position size: $100 / $50 ="),
    ("0.1 BTC", "2 oz"),
    ("($9,700 position)", "($4,000 position)"),
    ("Entry: $2,000/oz. Stop-loss: $1,920/oz. Distance = $1,500", "Entry: $2,000/oz. Stop-loss: $1,920/oz. Distance = $80"),
    ("$200 / $1,500 =", "$200 / $80 ="),
    ("0.133 BTC", "2.5 oz"),
    ("(~$12,933)", "(~$5,000)"),
    ("you're long BTC and long ETH, those aren't truly separate bets", "you're long Gold and long Silver, those aren't truly separate bets"),
    ("all crypto", "all precious metals"),
    ("BTC drops 50%", "Gold drops 50%"),
    ("BTC drops 20%", "Gold drops 20%"),
    ("BTC moves 10%", "Gold moves 10%"),
    ("You're long BTC", "You're long Gold"),
    ("long BTC", "long Gold"),
    ("crypto wallet", "broker account"),
    ("crypto influencers", "market influencers"),
    ("crypto enthusiast", "gold market enthusiast"),
    ("crypto education", "gold trading education"),
    ("crypto research", "gold market research"),
    ("crypto market grew", "precious metals market grew"),
    ("crypto market shrank", "precious metals market shrank"),
    ("crypto market belongs to Bitcoin", "precious metals market belongs to Gold"),
    ("crypto market", "precious metals market"),
    ("money flows FROM altcoins TO Bitcoin", "money flows FROM other metals TO Gold"),
    ("money flows TO altcoins", "money flows TO other metals"),
    ("Crypto News", "Gold News"),
    ("money is coming into crypto overall", "money is coming into precious metals overall"),
    ("money is leaving crypto", "money is leaving precious metals"),
    ("on-chain metrics", "fundamental analysis"),
    ("on-chain valuation metric", "fundamental valuation metric"),
    ("On-chain", "Fundamental"),
    ("on-chain", "fundamental"),
    ("blockchain miners/validators", "market participants"),
    ("blockchain without banks", "markets"),
    ("public blockchain", "global market"),
    ("Decentralized Finance — financial services on blockchain without banks", "Precious metals market — global trading of gold, silver, platinum"),
    ("Transaction fees paid to blockchain miners/validators", "Spread and commission costs in trading"),
    ("Smallest BTC unit (0.00000001 BTC). Named after creator.", "One troy ounce — standard unit for measuring gold weight (31.1 grams)."),
    ("Entity holding large amounts of crypto (1000+ BTC)", "Major institutional holder — central banks, ETFs, or funds holding large gold reserves"),
    ("Total Value Locked — money deposited in DeFi protocols", "Total assets under management in Gold ETFs and funds"),
    ("altcoins", "other metals"),
    ("altcoin season", "other metals rally"),
    ("Altcoin season", "Other metals rally"),
    ("altcoin", "other metal"),
    ("ETH Dominance", "Silver Dominance"),
    ("Ethereum's share of the crypto market. When ETH dominance rises, it often signals growing interest in DeFi and altcoins.", "Silver's share of the precious metals market. When Silver dominance rises, it often signals growing industrial demand."),
    ("DeFi", "ETFs"),
    ("Halving", "FOMC Meeting"),
    ("halving", "rate decision"),
    ("halvings", "rate decisions"),
    ("Halvings:", "FOMC Meetings:"),
    ("mining_pool", "institution"),
    ("Mining Pool", "Institution"),
    ("mining", "production"),
    ("Satoshi", "Troy Ounce"),
    ("satoshi", "troy ounce"),
    ("mempool.space", "goldprice.org"),
    ("View on mempool.space", "View on goldprice.org"),
    ("exchange netflows BTC", "ETF flows Gold"),
    ("Bitcoin Magazine Pro", "Kitco Gold"),
    ("Bitcoin", "Gold"),
    ("bitcoin", "gold"),
    ("BTC is in Wave", "Gold is in Wave"),
    ("BTC", "Gold"),
    ("Net Flow (BTC)", "Net Flow (oz)"),
    ("Avg Size (BTC)", "Avg Size (oz)"),
    ("OI (BTC)", "OI (oz)"),
]

# These JSON keys should NOT be renamed (they are code identifiers)
SKIP_KEYS = {
    "whatIsBitcoin",  # key name stays, value changes
    "btcPrice",
    "btcUsdt",
    "btcChart",
    "btcDominance",
    "btcSeason",
    "btcDominanceDescription",
    "totalBtc",
    "btcInGold",
    "btcM2Index",
    "btcSpxRatio",
    "oiBtc",
}


def replace_gold_vocab(value):
    """Apply all replacements to a string value."""
    if not isinstance(value, str):
        return value
    result = value
    for old, new in REPLACEMENTS:
        result = result.replace(old, new)
    return result


def process_obj(obj):
    """Recursively process all string values in a JSON object."""
    if isinstance(obj, dict):
        return {k: process_obj(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [process_obj(item) for item in obj]
    elif isinstance(obj, str):
        return replace_gold_vocab(obj)
    return obj


def process_locale(locale_dir):
    """Process all JSON files in a locale directory."""
    changes = 0
    for fname in sorted(os.listdir(locale_dir)):
        if not fname.endswith('.json'):
            continue
        fpath = os.path.join(locale_dir, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        original = json.dumps(data, ensure_ascii=False)
        processed = process_obj(data)
        updated = json.dumps(processed, ensure_ascii=False)

        if original != updated:
            with open(fpath, 'w', encoding='utf-8') as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)
                f.write('\n')
            changes += 1
            print(f"  Updated: {fname}")
        else:
            print(f"  No changes: {fname}")
    return changes


def main():
    total = 0
    for locale in ['en', 'ru', 'zh', 'km']:
        locale_dir = os.path.join(LOCALES_DIR, locale)
        if not os.path.isdir(locale_dir):
            print(f"Skipping {locale} (not found)")
            continue
        print(f"\n=== {locale.upper()} ===")
        total += process_locale(locale_dir)
    print(f"\nTotal files updated: {total}")


if __name__ == '__main__':
    main()

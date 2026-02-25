#!/usr/bin/env python3
"""Fix remaining BTC/crypto references missed by first pass."""
import json, os
from collections import defaultdict

D = os.path.dirname(os.path.abspath(__file__))

def set_nested(obj, path, value):
    keys = path.split('.')
    for k in keys[:-1]:
        obj = obj[k]
    obj[keys[-1]] = value

def fix_file(locale, fname, patches):
    fpath = os.path.join(D, locale, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for path, val in patches:
        try:
            set_nested(data, path, val)
        except (KeyError, TypeError) as e:
            print(f"  SKIP {locale}/{fname} {path}: {e}")
    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

FIXES = [
    # EN learn.json glossary
    ("en", "learn.json", "glossary.DeFi", "Precious metals market — global trading of gold, silver, platinum"),
    ("en", "learn.json", "glossary.Gas", "Spread — the cost difference between buy and sell prices in trading"),
    ("en", "learn.json", "glossary.MVRV", "Market Value to Realized Value — fundamental valuation metric"),
    ("en", "learn.json", "glossary.TVL", "Total assets under management in Gold ETFs and funds"),
    ("en", "learn.json", "glossary.Whale", "Major institutional holder — central banks, ETFs, or funds holding large gold reserves"),
    # EN about.json
    ("en", "about.json", "howToUse.onChain.desc", "Trading volume, market depth, institutional flows, active positions, large transaction count"),
    ("en", "about.json", "featuresCategories.whaleTracking.desc", "Institutional tracking, large transaction monitoring, and accumulation/distribution patterns"),
    # EN resources.json
    ("en", "resources.json", "sections.analytics.description", "Market data, institutional tracking, and smart money analysis."),
    ("en", "resources.json", "sections.data.platforms.coingecko.desc", "Go-to for market overview. Price tracking, market cap rankings, Fear & Greed index, market calendar."),
    ("en", "resources.json", "sections.data.platforms.debank.desc", "Best free portfolio tracker. Tracks all positions across markets. No signup required."),
    ("en", "resources.json", "sections.education.platforms.theBlock.desc", "Premium gold market news and data dashboards. Industry-leading reporting on institutional adoption and market structure."),
    ("en", "resources.json", "sections.education.platforms.reddit.desc", "Largest gold trading communities on Reddit. Real-time discussion, sentiment gauge, and community-vetted information."),
    ("en", "resources.json", "sections.education.platforms.messari.desc", "Institutional-grade gold market research. Industry reports, asset profiles, governance data, and fundraising news."),
    ("en", "resources.json", "sections.education.platforms.coinBureau.desc", "Trusted gold market research and reviews. Detailed analysis, asset reviews, and educational YouTube content."),
    ("en", "resources.json", "sections.education.platforms.binanceAcademy.desc", "Free structured gold trading education. Beginner to advanced courses on markets, trading, ETFs, and security."),
    # RU learn.json glossary
    ("ru", "learn.json", "glossary.DeFi", "Рынок драгоценных металлов — глобальная торговля золотом, серебром, платиной"),
    ("ru", "learn.json", "glossary.Halving", "Заседание FOMC — заседание ФРС каждые 6 недель для установления процентных ставок"),
    ("ru", "learn.json", "glossary.Satoshi", "Тройская унция — стандартная единица измерения веса золота (31,1 грамма)"),
    # ZH learn.json glossary
    ("zh", "learn.json", "glossary.DeFi", "贵金属市场——黄金、白银、铂金的全球交易"),
    ("zh", "learn.json", "glossary.Halving", "FOMC会议——美联储每6周召开一次的利率决策会议"),
    ("zh", "learn.json", "glossary.Satoshi", "金衡盎司——黄金重量的标准计量单位（31.1克）"),
]

groups = defaultdict(list)
for locale, fname, path, val in FIXES:
    groups[(locale, fname)].append((path, val))

for (locale, fname), patches in groups.items():
    print(f"Fixing {locale}/{fname} ({len(patches)} patches)")
    fix_file(locale, fname, patches)

# Also do string replacements for remaining crypto/blockchain/wallet/mempool in resources
for locale in ['en', 'km']:
    fpath = os.path.join(D, locale, 'resources.json')
    with open(fpath, 'r', encoding='utf-8') as f:
        text = f.read()
    text = text.replace('blockchain', 'market data')
    text = text.replace('Blockchain', 'Market data')
    text = text.replace('crypto ', 'gold market ')
    text = text.replace('Crypto ', 'Gold market ')
    text = text.replace('wallet intelligence', 'market intelligence')
    text = text.replace('Wallet intelligence', 'Market intelligence')
    text = text.replace('Wallet labels', 'Entity labels')
    text = text.replace('wallet positions', 'portfolio positions')
    text = text.replace('wallet', 'portfolio')
    text = text.replace('Web3 wallet', 'Trading tools')
    text = text.replace('Web3 portfolio', 'Trading tools')
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(text)
    # Verify it's valid JSON
    with open(fpath, 'r', encoding='utf-8') as f:
        json.load(f)
    print(f"Fixed remaining strings in {locale}/resources.json")

print("Done!")

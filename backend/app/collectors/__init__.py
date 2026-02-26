from app.collectors.market import GoldMarketCollector
from app.collectors.gold_price import GoldPriceCollector
from app.collectors.historical_gold import HistoricalGoldCollector
from app.collectors.fred_data import FREDCollector
from app.collectors.cot_data import COTCollector
from app.collectors.gold_etf_flows import GoldETFFlowCollector
from app.collectors.central_bank_gold import CentralBankGoldCollector
from app.collectors.gold_news import GoldNewsCollector
from app.collectors.session_tracker import SessionTracker
from app.collectors.gold_analysts import GoldAnalystCollector
from app.collectors.gold_miners import GoldMinersCollector
from app.collectors.physical_premium import PhysicalPremiumCollector
from app.collectors.news import NewsCollector
from app.collectors.macro import MacroCollector
from app.collectors.reddit import RedditCollector
from app.collectors.etf import ETFCollector

__all__ = [
    # Gold-specific collectors (new)
    "GoldMarketCollector",
    "GoldPriceCollector",
    "HistoricalGoldCollector",
    "FREDCollector",
    "COTCollector",
    "GoldETFFlowCollector",
    "CentralBankGoldCollector",
    "GoldNewsCollector",
    "SessionTracker",
    "GoldAnalystCollector",
    "GoldMinersCollector",
    "PhysicalPremiumCollector",
    # Retained from original (still useful for gold context)
    "NewsCollector",
    "MacroCollector",
    "RedditCollector",
    "ETFCollector",
]

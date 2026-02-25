"""Event Impact Memory — classifies news events and recalls historical price impact.

This module gives the prediction system a 'memory' of how past events
(war, politics, Fed decisions, ETF news, etc.) have affected gold price,
so it can anticipate the impact of similar new events.
"""
import logging
import re
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

# ── Event categories and their keyword mappings ──

EVENT_CATEGORIES = {
    "war_conflict": {
        "keywords": [
            # English
            "war", "invasion", "military", "missile", "strike", "bomb",
            "conflict", "troops", "army", "attack", "hostage", "ceasefire",
            "nato", "nuclear", "weapons", "sanctions military", "drone strike",
            "escalation", "tension", "geopolitical", "territorial",
            # Russian
            "война", "вторжение", "военный", "ракета", "удар", "бомба",
            "конфликт", "войска", "армия", "атака", "заложник", "перемирие",
            "ядерный", "оружие", "эскалация", "напряжённость", "геополитика",
            # Chinese
            "战争", "入侵", "军事", "导弹", "袭击", "炸弹", "冲突",
            "军队", "攻击", "人质", "停火", "核武器", "升级", "地缘政治",
            # Spanish
            "guerra", "invasión", "militar", "misil", "ataque", "bomba",
            "conflicto", "tropas", "ejército", "rehén", "alto el fuego",
            "escalada", "tensión", "geopolítica",
            # Arabic
            "حرب", "غزو", "عسكري", "صاروخ", "هجوم", "قنبلة",
            "صراع", "قوات", "جيش", "رهينة", "وقف إطلاق النار",
            "تصعيد", "توتر", "جيوسياسي",
        ],
        "severity_boost": 2,
    },
    "politics_regulation": {
        "keywords": [
            # English
            "regulation", "ban", "bans", "banned", "crackdown", "sec", "cftc", "congress",
            "senate", "legislation", "law", "executive order", "policy",
            "tax", "compliance", "kyc", "aml", "enforcement", "subpoena",
            "stablecoin bill", "framework", "gensler", "warren",
            "trump", "biden", "white house", "treasury department",
            # Russian
            "регулирование", "запрет", "закон", "законопроект",
            "центробанк", "минфин", "госдума", "налог", "путин",
            "цифровой рубль", "золото регулирование",
            # Chinese
            "监管", "禁令", "法律", "法规", "政策", "税收",
            "合规", "执法", "数字人民币", "央行",
            "国务院", "习近平",
            # Spanish
            "regulación", "prohibición", "ley", "legislación",
            "impuesto", "cumplimiento", "banco central",
            # Arabic
            "تنظيم", "حظر", "قانون", "تشريع", "ضريبة",
            "بنك مركزي", "سياسة",
            # Japanese/Korean (major regulatory markets)
            "規制", "禁止", "法律", "금지", "규제", "법률",
            # Turkish
            "düzenleme", "yasakla", "altın düzenleme",
            # Hindi
            "नीति", "विनियमन", "प्रतिबंध", "कानून",
        ],
        "severity_boost": 1,
    },
    "monetary_policy": {
        "keywords": [
            # English
            "federal reserve", "fed", "interest rate", "rate hike", "rate cut",
            "fomc", "powell", "inflation", "cpi", "ppi", "employment",
            "jobs report", "nonfarm", "gdp", "recession", "quantitative",
            "tightening", "easing", "dovish", "hawkish", "yield curve",
            "debt ceiling", "treasury", "bond", "basis points",
            # Russian (stem forms for case flexibility)
            "ставк", "инфляци", "ввп", "рецесси", "набиуллина",
            "ключев", "денежн полити", "центробанк",
            # Chinese
            "利率", "通胀", "降息", "加息", "货币政策",
            "量化宽松", "经济衰退", "央行",
            # Spanish
            "tasa de interés", "inflación", "recesión",
            "política monetaria", "banco central",
            # Arabic
            "سعر الفائدة", "تضخم", "ركود", "سياسة نقدية",
            # Japanese
            "金利", "インフレ", "利上げ", "利下げ", "日銀",
        ],
        "severity_boost": 2,
    },
    "tariff_trade": {
        "keywords": [
            # English
            "tariff", "trade war", "import duty", "export ban", "trade deal",
            "sanctions", "embargo", "trade deficit", "customs", "wto",
            "retaliatory", "trade policy", "protectionism", "free trade",
            # Russian
            "тариф", "торговая война", "санкции", "эмбарго",
            "пошлина", "импорт", "экспорт", "торговый дефицит",
            # Chinese
            "关税", "贸易战", "制裁", "禁运", "进口",
            "出口", "贸易逆差", "贸易协议",
            # Spanish
            "arancel", "guerra comercial", "sanciones", "embargo",
            # Arabic
            "تعرفة", "حرب تجارية", "عقوبات", "حصار",
        ],
        "severity_boost": 1,
    },
    "stock_market": {
        "keywords": [
            # English
            "s&p 500", "nasdaq", "dow jones", "stock market", "wall street",
            "equity", "stock crash", "correction", "bear market", "bull market",
            "earnings", "tech stocks", "magnificent 7", "ipo", "buyback",
            "market cap", "index", "futures", "options expiry",
            # Russian
            "фондовый рынок", "акции", "биржа", "мосбиржа",
            "обвал", "коррекция", "медвежий рынок", "бычий рынок",
            # Chinese
            "股市", "纳斯达克", "道琼斯", "标普500", "股票",
            "崩盘", "牛市", "熊市", "上证",
            # Japanese
            "株式市場", "日経", "暴落", "株価",
        ],
        "severity_boost": 0,
    },
    "etf_institutional": {
        "keywords": [
            # English
            "etf", "gold etf", "gld", "iau", "etf inflow", "etf outflow",
            "spdr gold", "ishares gold", "gold trust",
            "blackrock", "fidelity", "state street",
            "institutional", "custody", "asset manager",
            "fund", "investment vehicle", "gold fund",
            "comex", "lbma", "gold vault",
            # Russian
            "золотой etf", "институциональный", "фонд",
            # Chinese
            "黄金etf", "机构投资", "基金",
            "资产管理", "托管",
            # Spanish
            "fondo de oro", "institucional", "custodia",
            # Arabic
            "صندوق ذهب", "مؤسسي", "استثمار مؤسسي",
        ],
        "severity_boost": 2,
    },
    "exchange_hack": {
        "keywords": [
            # English — financial system / exchange security
            "hack", "exploit", "breach", "stolen", "drained", "vulnerability",
            "scam", "phishing", "fraud", "theft",
            "vault breach", "gold theft", "heist",
            "funds stolen", "security incident", "bank breach",
            # Russian
            "взлом", "украдено", "уязвимость", "мошенничество",
            "фишинг", "кража", "средства похищены",
            # Chinese
            "黑客", "漏洞", "被盗", "诈骗", "钓鱼",
            "资金被盗", "安全事件",
            # Spanish
            "hackeo", "robado", "estafa", "vulnerabilidad",
            # Arabic
            "اختراق", "سرقة", "احتيال", "ثغرة",
        ],
        "severity_boost": 2,
    },
    "company_announcement": {
        "keywords": [
            # English
            "partnership", "acquisition", "merger", "launch", "listing",
            "delisting", "bankruptcy", "insolvency", "layoff", "restructuring",
            "revenue", "profit", "loss", "quarterly", "annual report",
            "barrick gold", "newmont", "franco-nevada", "wheaton", "agnico eagle",
            # Russian
            "партнёрство", "приобретение", "слияние", "банкротство",
            "листинг", "делистинг", "увольнения",
            # Chinese
            "合作", "收购", "合并", "上市", "退市",
            "破产", "裁员", "特斯拉",
            # Spanish
            "asociación", "adquisición", "fusión", "quiebra",
        ],
        "severity_boost": 0,
    },
    "whale_movement": {
        "keywords": [
            # English
            "whale", "large transfer", "whale alert", "dormant", "moved",
            "exchange deposit", "exchange withdrawal", "accumulation",
            "distribution", "on-chain", "wallet", "cold storage",
            # Russian
            "кит", "крупный перевод", "накопление", "кошелёк",
            # Chinese
            "巨鲸", "大额转账", "链上", "钱包", "冷存储",
            # Spanish
            "ballena", "transferencia grande", "acumulación",
        ],
        "severity_boost": 1,
    },
    "technology": {
        "keywords": [
            # English — gold mining and market infrastructure
            "mining output", "gold mining", "refining", "smelting",
            "comex", "lbma", "london fix", "gold fix",
            "vault", "depository", "assay", "gold standard",
            "blockchain gold", "tokenized gold", "digital gold",
            # Russian
            "золотодобыча", "добыча золота", "аффинаж", "хранилище",
            # Chinese
            "金矿", "黄金开采", "冶炼", "金库",
            "伦敦金", "上海金",
            # Spanish
            "minería de oro", "refinería", "bóveda",
        ],
        "severity_boost": 1,
    },
    "macro_economic": {
        "keywords": [
            # English
            "dollar", "dxy", "gold", "oil", "commodity", "currency",
            "euro", "yen", "yuan", "emerging market", "sovereign debt",
            "banking crisis", "liquidity", "money supply", "m2",
            "real estate", "housing", "consumer confidence",
            # Russian
            "доллар", "золото", "нефть", "рубль", "валюта",
            "банковский кризис", "ликвидность", "денежная масса",
            # Chinese
            "美元", "黄金", "石油", "人民币", "大宗商品",
            "银行危机", "流动性", "货币供应",
            # Spanish
            "dólar", "oro", "petróleo", "crisis bancaria",
            # Arabic
            "دولار", "ذهب", "نفط", "أزمة مصرفية",
        ],
        "severity_boost": 0,
    },
    "country_adoption": {
        "keywords": [
            # English — sovereign/central bank gold events
            "gold reserve", "strategic reserve", "national reserve",
            "sovereign wealth fund", "sovereign fund", "country buys gold", "government gold",
            "central bank gold", "gold standard", "gold repatriation",
            "gold purchases", "central bank purchases",
            "gold treasury", "state gold", "national gold",
            "gold accumulation", "gold allocation",
            "digital gold", "gold backed",
            # Country-specific entities (gold context)
            "saudi arabia gold", "saudi gold",
            "uae gold", "dubai gold",
            "qatar gold", "bahrain gold", "kuwait gold",
            "israel gold",
            "russia gold", "russia reserves",
            "china gold", "hong kong gold", "pboc gold",
            "japan gold", "boj gold",
            "india gold", "rbi gold",
            "brazil gold",
            "turkey gold", "turkey reserves",
            "poland gold", "hungary gold",
            "singapore gold",
            # Russian
            "золотой резерв", "резерв золота", "золотые запасы",
            "стратегическ", "национальн резерв", "россия золот",
            "центробанк золот", "покупка золота",
            "суверенн фонд", "золотой стандарт",
            "саудовск", "эмират", "израиль золот",
            # Chinese
            "黄金储备", "国家储备", "战略储备", "主权基金",
            "央行购金", "国家黄金",
            # Spanish
            "reserva de oro", "reserva estratégica",
            "compra de oro", "reserva nacional",
            # Arabic
            "احتياطي", "ذهب احتياطي", "شراء ذهب",
            "صندوق سيادي", "السعودية", "الإمارات",
            "إسرائيل", "قطر", "البحرين", "الكويت",
            # Turkish
            "altın rezerv", "stratejik rezerv",
            # Hindi
            "सोना भंडार", "भारत सोना", "केंद्रीय बैंक सोना",
            # Japanese
            "金準備金", "国家準備金",
            # Korean
            "금 준비금", "국가 금",
        ],
        "severity_boost": 3,  # Sovereign gold accumulation is highest-impact
    },
}


class EventClassifier:
    """Classifies news headlines into event categories with severity scoring."""

    def classify(self, title: str, sentiment_score: float = 0.0) -> dict | None:
        """Classify a news headline into an event category.

        Returns None if the headline doesn't match any significant category.
        Returns dict with category, subcategory, keywords, severity.
        """
        title_lower = title.lower()

        best_category = None
        best_score = 0
        matched_keywords = []

        for category, config in EVENT_CATEGORIES.items():
            cat_keywords = []
            cat_score = 0

            for kw in config["keywords"]:
                # Use word boundary matching for short ASCII keywords to avoid
                # false positives like "war" in "rewards"
                # Non-ASCII keywords (CJK, Arabic, Cyrillic) use substring match
                if len(kw) <= 4 and kw.isascii():
                    if re.search(r'\b' + re.escape(kw) + r'\b', title_lower):
                        cat_keywords.append(kw)
                        cat_score += len(kw.split()) * 2
                else:
                    if kw in title_lower:
                        cat_keywords.append(kw)
                        cat_score += len(kw.split()) * 2

            if cat_score > best_score:
                best_score = cat_score
                best_category = category
                matched_keywords = cat_keywords

        if not best_category or best_score < 2:
            return None  # Not significant enough to track

        # Calculate severity (1-10)
        config = EVENT_CATEGORIES[best_category]
        severity = min(10, max(1,
            3  # base
            + config["severity_boost"]
            + len(matched_keywords)  # more keywords = more relevant
            + int(abs(sentiment_score) * 3)  # strong sentiment = more impactful
        ))

        return {
            "category": best_category,
            "subcategory": matched_keywords[0] if matched_keywords else None,
            "keywords": ",".join(matched_keywords),
            "severity": severity,
        }


class EventPatternMatcher:
    """Finds similar past events and returns their expected price impact.

    Uses category-specific impact models with:
    - Keyword similarity (Jaccard) weighting
    - Severity-band weighting (events of similar severity matter more)
    - Recency weighting (recent events matter more — markets change)
    - Directional consistency tracking per category
    """

    # Category-specific mechanisms: how each event type affects gold price
    CATEGORY_MECHANISMS = {
        "war_conflict": "Geopolitical instability → flight to safety → gold rallies as premier safe-haven asset",
        "politics_regulation": "Political uncertainty → risk aversion → drives demand for gold as store of value",
        "monetary_policy": "Rate decisions → affects dollar strength and real yields → gold inversely correlated with DXY and real rates",
        "tariff_trade": "Trade barriers → economic uncertainty → gold benefits as inflation hedge and safe haven",
        "stock_market": "Equity moves → risk sentiment → gold often inversely correlated with equities during crises",
        "etf_institutional": "Gold ETF flows (GLD, IAU) → direct demand/supply pressure → immediate price impact proportional to flow size",
        "exchange_hack": "Financial system instability → trust crisis → flight to physical gold",
        "company_announcement": "Mining company/central bank action → affects gold supply/demand outlook",
        "whale_movement": "Large institutional/central bank transfers → supply/demand shift in physical and paper gold markets",
        "technology": "Mining technology or market infrastructure changes → affects production costs and market access",
        "macro_economic": "Macro shifts → changes gold's relative attractiveness as inflation hedge and safe haven",
        "country_adoption": "Central bank gold purchases → massive demand signal → strongly bullish for gold reserves",
    }

    def find_similar_events(
        self,
        category: str,
        keywords: str,
        past_events: list[dict],
        severity: int = 5,
        min_similarity: float = 0.25,
    ) -> list[dict]:
        """Find past events in the same category with similar keywords.

        Enhanced with severity-band and recency weighting.
        """
        current_kw_set = set(keywords.lower().split(",")) if keywords else set()
        similar = []

        for event in past_events:
            if event.get("category") != category:
                continue

            past_kw_set = set(
                (event.get("keywords") or "").lower().split(",")
            )

            # Jaccard similarity on keywords
            intersection = current_kw_set & past_kw_set
            union = current_kw_set | past_kw_set
            if not union:
                continue

            keyword_sim = len(intersection) / len(union)

            # Severity similarity bonus: events with similar severity are more comparable
            past_severity = event.get("severity", 5)
            severity_diff = abs(severity - past_severity)
            severity_sim = max(0, 1.0 - severity_diff * 0.15)  # 0.85 for ±1, 0.7 for ±2, etc.

            # Combined similarity
            combined_sim = keyword_sim * 0.7 + severity_sim * 0.3

            if combined_sim >= min_similarity:
                event_copy = dict(event)
                event_copy["similarity"] = combined_sim
                event_copy["keyword_similarity"] = keyword_sim
                event_copy["severity_similarity"] = severity_sim
                similar.append(event_copy)

        # Sort by similarity (highest first)
        similar.sort(key=lambda x: -x.get("similarity", 0))
        return similar[:30]  # Top 30 most similar

    def get_expected_impact(
        self,
        similar_events: list[dict],
        current_severity: int = 5,
    ) -> dict:
        """Calculate expected price impact with severity and recency weighting.

        Recent events matter more (exponential decay over 30 days).
        Events with similar severity to current event get more weight.
        """
        from datetime import datetime, timedelta

        if not similar_events:
            return {
                "expected_1h": 0.0,
                "expected_4h": 0.0,
                "expected_24h": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "avg_sentiment_predictive": 0.5,
                "directional_consistency": 0.0,
                "mechanism": "",
            }

        now = datetime.utcnow()
        total_weight = 0.0
        weighted_1h = 0.0
        weighted_4h = 0.0
        weighted_24h = 0.0
        predictive_count = 0
        total_predictive = 0
        direction_counts = {"up": 0, "down": 0}

        for event in similar_events:
            sim = event.get("similarity", 0.5)

            # Recency weight: half-life of 30 days
            event_ts = event.get("timestamp")
            if event_ts:
                if isinstance(event_ts, str):
                    try:
                        event_ts = datetime.fromisoformat(event_ts)
                    except Exception:
                        event_ts = None
                if event_ts:
                    days_ago = (now - event_ts).total_seconds() / 86400
                    recency = 0.5 ** (days_ago / 30)  # Half-life 30 days
                else:
                    recency = 0.5
            else:
                recency = 0.5

            # Combined weight: similarity² × recency
            weight = sim * sim * recency

            c1h = event.get("change_pct_1h")
            c4h = event.get("change_pct_4h")
            c24h = event.get("change_pct_24h")

            if c1h is not None:
                weighted_1h += c1h * weight
                total_weight += weight
                if c1h > 0:
                    direction_counts["up"] += 1
                else:
                    direction_counts["down"] += 1

            if c4h is not None:
                weighted_4h += c4h * weight

            if c24h is not None:
                weighted_24h += c24h * weight

            if event.get("sentiment_was_predictive") is not None:
                total_predictive += 1
                if event["sentiment_was_predictive"]:
                    predictive_count += 1

        if total_weight == 0:
            return {
                "expected_1h": 0.0,
                "expected_4h": 0.0,
                "expected_24h": 0.0,
                "confidence": 0.0,
                "sample_size": 0,
                "avg_sentiment_predictive": 0.5,
                "directional_consistency": 0.0,
                "mechanism": "",
            }

        avg_1h = weighted_1h / total_weight
        avg_4h = weighted_4h / total_weight
        avg_24h = weighted_24h / total_weight

        # Directional consistency: how often do events in this category move the same way?
        total_dir = direction_counts["up"] + direction_counts["down"]
        if total_dir > 0:
            dominant = max(direction_counts.values())
            directional_consistency = dominant / total_dir  # 0.5 = random, 1.0 = always same direction
        else:
            directional_consistency = 0.5

        # Confidence: sample size + average similarity + directional consistency
        avg_sim = sum(e.get("similarity", 0) for e in similar_events) / len(similar_events)
        confidence = min(1.0,
            (len(similar_events) / 10) * avg_sim * (0.5 + directional_consistency * 0.5)
        )

        avg_predictive = (predictive_count / total_predictive) if total_predictive > 0 else 0.5

        # Get mechanism for this category
        category = similar_events[0].get("category", "") if similar_events else ""
        mechanism = self.CATEGORY_MECHANISMS.get(category, "")

        return {
            "expected_1h": round(avg_1h, 4),
            "expected_4h": round(avg_4h, 4),
            "expected_24h": round(avg_24h, 4),
            "confidence": round(confidence, 4),
            "sample_size": len(similar_events),
            "avg_sentiment_predictive": round(avg_predictive, 4),
            "directional_consistency": round(directional_consistency, 4),
            "mechanism": mechanism,
        }

    def combine_multiple_events(
        self,
        events_with_impacts: list[dict],
    ) -> dict:
        """Combine impacts from multiple concurrent events.

        Handles:
        - Reinforcing events (same direction): impacts compound
        - Conflicting events (opposite direction): partially cancel, increase uncertainty
        - Severity-weighted combination
        """
        if not events_with_impacts:
            return {
                "expected_1h": 0.0,
                "expected_4h": 0.0,
                "expected_24h": 0.0,
                "confidence": 0.0,
                "active_event_count": 0,
                "dominant_direction": "neutral",
                "mechanism_summary": "",
            }

        total_severity = sum(e.get("severity", 5) for e in events_with_impacts)
        if total_severity == 0:
            total_severity = 1

        combined_1h = 0.0
        combined_4h = 0.0
        combined_24h = 0.0
        mechanisms = []
        directions = []

        for event_data in events_with_impacts:
            sev_weight = event_data.get("severity", 5) / total_severity
            impact = event_data.get("expected_impact", {})

            combined_1h += impact.get("expected_1h", 0) * sev_weight
            combined_4h += impact.get("expected_4h", 0) * sev_weight
            combined_24h += impact.get("expected_24h", 0) * sev_weight

            mech = impact.get("mechanism", "")
            if mech:
                mechanisms.append(f"[{event_data.get('category', '?')}] {mech}")

            # Track direction
            if impact.get("expected_1h", 0) > 0:
                directions.append("bullish")
            elif impact.get("expected_1h", 0) < 0:
                directions.append("bearish")

        # Directional agreement among events
        bullish_count = directions.count("bullish")
        bearish_count = directions.count("bearish")
        total_dir = bullish_count + bearish_count

        if total_dir > 0:
            agreement = max(bullish_count, bearish_count) / total_dir
        else:
            agreement = 0.5

        # If events conflict, reduce confidence and dampen magnitude
        if agreement < 0.6:  # Mixed signals
            conflict_damper = 0.5
            combined_1h *= conflict_damper
            combined_4h *= conflict_damper
            combined_24h *= conflict_damper

        # Confidence from individual event confidences, adjusted for agreement
        avg_conf = sum(
            e.get("expected_impact", {}).get("confidence", 0)
            for e in events_with_impacts
        ) / len(events_with_impacts)
        combined_confidence = avg_conf * agreement

        dominant = "bullish" if bullish_count > bearish_count else ("bearish" if bearish_count > bullish_count else "neutral")

        return {
            "expected_1h": round(combined_1h, 4),
            "expected_4h": round(combined_4h, 4),
            "expected_24h": round(combined_24h, 4),
            "confidence": round(min(1.0, combined_confidence), 4),
            "active_event_count": len(events_with_impacts),
            "dominant_direction": dominant,
            "event_agreement": round(agreement, 4),
            "mechanism_summary": " | ".join(mechanisms[:3]),
        }

    def get_category_stats(self, past_events: list[dict]) -> dict:
        """Get detailed impact stats per event category including severity bands."""
        import statistics

        stats = {}

        for event in past_events:
            cat = event.get("category")
            if not cat:
                continue

            if cat not in stats:
                stats[cat] = {
                    "impacts_1h": [], "impacts_4h": [], "impacts_24h": [],
                    "high_sev_impacts": [], "low_sev_impacts": [],
                    "count": 0, "sentiment_predictive": [],
                }

            stats[cat]["count"] += 1
            sev = event.get("severity", 5)
            c1h = event.get("change_pct_1h")

            if c1h is not None:
                stats[cat]["impacts_1h"].append(c1h)
                if sev >= 7:
                    stats[cat]["high_sev_impacts"].append(c1h)
                elif sev <= 4:
                    stats[cat]["low_sev_impacts"].append(c1h)

            if event.get("change_pct_4h") is not None:
                stats[cat]["impacts_4h"].append(event["change_pct_4h"])
            if event.get("change_pct_24h") is not None:
                stats[cat]["impacts_24h"].append(event["change_pct_24h"])
            if event.get("sentiment_was_predictive") is not None:
                stats[cat]["sentiment_predictive"].append(event["sentiment_was_predictive"])

        result = {}
        for cat, data in stats.items():
            impacts_1h = data["impacts_1h"]
            avg_1h = sum(impacts_1h) / len(impacts_1h) if impacts_1h else 0.0
            std_1h = statistics.stdev(impacts_1h) if len(impacts_1h) >= 2 else 0.0
            bullish_1h = sum(1 for x in impacts_1h if x > 0) / len(impacts_1h) if impacts_1h else 0.5
            predictive_power = abs(bullish_1h - 0.5) * 2  # 0 = random, 1 = perfectly directional

            result[cat] = {
                "count": data["count"],
                "avg_1h": round(avg_1h, 4),
                "avg_4h": round(sum(data["impacts_4h"]) / len(data["impacts_4h"]), 4) if data["impacts_4h"] else 0.0,
                "avg_24h": round(sum(data["impacts_24h"]) / len(data["impacts_24h"]), 4) if data["impacts_24h"] else 0.0,
                "std_1h": round(std_1h, 4),
                "bullish_ratio": round(bullish_1h, 4),
                "predictive_power": round(predictive_power, 4),
                "high_severity_avg": round(sum(data["high_sev_impacts"]) / len(data["high_sev_impacts"]), 4) if data["high_sev_impacts"] else None,
                "low_severity_avg": round(sum(data["low_sev_impacts"]) / len(data["low_sev_impacts"]), 4) if data["low_sev_impacts"] else None,
                "sentiment_predictive": round(sum(data["sentiment_predictive"]) / len(data["sentiment_predictive"]), 4) if data["sentiment_predictive"] else 0.5,
            }
        return result

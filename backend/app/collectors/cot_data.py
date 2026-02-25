"""CFTC Commitments of Traders (COT) data collector for gold futures.

Fetches the weekly COT report for Gold (contract code 088691) from the
CFTC bulk CSV. Parses the "GOLD - COMMODITY EXCHANGE INC." row to extract
managed money, commercial, and non-commercial positioning data.

The report is published every Friday for the prior Tuesday's positions.
"""
import csv
import io
import logging

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.collectors.base import BaseCollector

logger = logging.getLogger(__name__)

# CFTC bulk disaggregated report (comma-delimited)
CFTC_DISAGGREGATED_URL = "https://www.cftc.gov/dea/newcot/deacom.txt"

# Gold futures contract code on COMEX
GOLD_CONTRACT_CODE = "088691"
GOLD_MARKET_NAME = "GOLD - COMMODITY EXCHANGE INC."


class COTCollector(BaseCollector):
    """Collects CFTC Commitments of Traders data for gold futures."""

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    async def collect(self) -> dict:
        """Fetch and parse the latest COT report for gold.

        Returns:
            Dict with positioning data:
            {report_date, mm_long, mm_short, mm_net,
             commercial_long, commercial_short, commercial_net,
             noncommercial_long, noncommercial_short, noncommercial_net,
             open_interest, oi_change}
        """
        cot_data = await self._fetch_cftc_csv()
        if cot_data:
            return cot_data

        logger.warning("CFTC COT data fetch failed, returning empty result")
        return {
            "report_date": None,
            "mm_long": None,
            "mm_short": None,
            "mm_net": None,
            "commercial_long": None,
            "commercial_short": None,
            "commercial_net": None,
            "noncommercial_long": None,
            "noncommercial_short": None,
            "noncommercial_net": None,
            "open_interest": None,
            "oi_change": None,
            "timestamp": self.now().isoformat(),
        }

    async def _fetch_cftc_csv(self) -> dict | None:
        """Download and parse the CFTC disaggregated CSV for the gold row."""
        try:
            session = await self.get_session()
            async with session.get(
                CFTC_DISAGGREGATED_URL,
                timeout=aiohttp.ClientTimeout(total=60),
                headers={"User-Agent": "Mozilla/5.0 (compatible; GoldSeer/1.0)"},
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"CFTC CSV returned HTTP {resp.status}")
                    return None

                text = await resp.text(encoding="utf-8", errors="replace")

            return self._parse_cot_csv(text)

        except Exception as e:
            logger.error(f"CFTC COT fetch error: {e}")
            return None

    def _parse_cot_csv(self, csv_text: str) -> dict | None:
        """Parse the comma-delimited COT report for the gold row."""
        try:
            reader = csv.DictReader(io.StringIO(csv_text))

            for row in reader:
                market_name = row.get("Market_and_Exchange_Names", "").strip()
                contract_code = row.get("CFTC_Contract_Market_Code", "").strip()

                # Match by contract code or market name
                if contract_code == GOLD_CONTRACT_CODE or GOLD_MARKET_NAME in market_name:
                    return self._extract_positioning(row)

            logger.warning("Gold row not found in CFTC COT data")
            return None

        except Exception as e:
            logger.error(f"COT CSV parse error: {e}")
            return None

    def _extract_positioning(self, row: dict) -> dict:
        """Extract positioning fields from a COT CSV row."""

        def safe_int(key: str) -> int | None:
            val = row.get(key, "").strip()
            try:
                return int(val) if val else None
            except (ValueError, TypeError):
                return None

        # Managed Money (Money Manager) positions
        mm_long = safe_int("M_Money_Positions_Long_All")
        mm_short = safe_int("M_Money_Positions_Short_All")

        # Commercial hedgers
        commercial_long = safe_int("Comm_Positions_Long_All")
        if commercial_long is None:
            commercial_long = safe_int("Prod_Merc_Positions_Long_All")
        commercial_short = safe_int("Comm_Positions_Short_All")
        if commercial_short is None:
            commercial_short = safe_int("Prod_Merc_Positions_Short_All")

        # Non-commercial (large speculators)
        noncommercial_long = safe_int("NonComm_Positions_Long_All")
        noncommercial_short = safe_int("NonComm_Positions_Short_All")

        # Open interest
        open_interest = safe_int("Open_Interest_All")
        oi_change = safe_int("Change_in_Open_Interest_All")

        # Compute net positions
        mm_net = None
        if mm_long is not None and mm_short is not None:
            mm_net = mm_long - mm_short

        commercial_net = None
        if commercial_long is not None and commercial_short is not None:
            commercial_net = commercial_long - commercial_short

        noncommercial_net = None
        if noncommercial_long is not None and noncommercial_short is not None:
            noncommercial_net = noncommercial_long - noncommercial_short

        report_date = row.get("As_of_Date_In_Form_YYMMDD", "").strip()
        if not report_date:
            report_date = row.get("Report_Date_as_YYYY-MM-DD", "").strip()

        return {
            "report_date": report_date,
            "mm_long": mm_long,
            "mm_short": mm_short,
            "mm_net": mm_net,
            "commercial_long": commercial_long,
            "commercial_short": commercial_short,
            "commercial_net": commercial_net,
            "noncommercial_long": noncommercial_long,
            "noncommercial_short": noncommercial_short,
            "noncommercial_net": noncommercial_net,
            "open_interest": open_interest,
            "oi_change": oi_change,
            "timestamp": self.now().isoformat(),
        }

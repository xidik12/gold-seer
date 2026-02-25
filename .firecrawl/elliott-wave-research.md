# Elliott Wave Detection Research
*Researched: 2026-02-18*

## What Makes a Good Elliott Wave Implementation

Elliott Wave theory identifies 5-wave impulse patterns (waves 1-5) and 3-wave corrections (A-B-C) using Fibonacci ratios to validate wave relationships.

### Core Rules (Must-Have for Valid Implementation)
1. **Wave 2** cannot retrace more than 100% of Wave 1
2. **Wave 3** cannot be the shortest of waves 1, 3, and 5
3. **Wave 4** cannot overlap the price territory of Wave 1
4. Fibonacci ratios validate wave proportions

### Key Fibonacci Ratios
- Wave 2 retraces 50%-61.8% of Wave 1
- Wave 3 extends 161.8%-261.8% of Wave 1
- Wave 4 retraces 38.2% of Wave 3
- Wave 5 extends 100%-161.8% of Wave 1

---

## Python Implementations

### 1. ElliottWaveAnalyzer (Best for BTC Seer)
- **GitHub:** https://github.com/btcorgtfo/ElliottWaveAnalyzer
- **Approach:** Brute-force validation - tries many combinations of wave patterns on OHLC data and validates each against rules
- **Key Concepts:**
  - **MonoWave:** Smallest building block (directional movement where each candle forms new extreme)
  - **Skip parameter:** Filters noise (skip=2 ignores next 2 local maxima)
  - **Detectable patterns:** 12345 Impulse, ABC Correction, Leading Triangle
  - **Rule validation:** Lambda expressions check conditions (e.g., "wave2.low > wave1.low")
  - Uses `.options_sorted` to examine shortest movements first

### 2. ElliottWaves (Pattern Recognition)
- **GitHub:** https://github.com/alessioricco/ElliottWaves
- **Main function:** `ElliottWaveFindPattern(df_source, measure, granularity, dateStart, dateEnd, extremes=True)`
- **Algorithm steps:**
  1. Data subsetting by date range
  2. Extrema identification (min/max Close values)
  3. Initial wave drawing via `draw_wave`
  4. Pattern discovery via `ElliottWaveDiscovery`
  5. Wave filtering via `filterWaveSet`
  6. Length-based segmentation
  7. Optimal pattern selection via `findBestFitWave`
  8. Chain construction via `buildWaveChainSet`
- **Requires:** pandas DataFrame with 'Close' column

### 3. TAEW Package (Academic, Fibonacci-Focused)
- **PyPI:** https://pypi.org/project/taew/
- **Based on paper:** "Profitability of Elliott Waves and Fibonacci Retracement Levels in the Foreign Exchange Market"
- **Functions:**
  - `Alternative_ElliottWave_label_upward/downward` - Uses both Fibonacci retracement AND timezone
  - `Traditional_ElliottWave_label_upward/downward` - Fibonacci retracement only
  - `Practical methods` - Partial waves (1-2, 1-3, 1-4) to predict next waves
- **Algorithm:** Iterative approach - finds all possible Wave 1, then valid Wave 2, etc.
- **Output:** Dictionary with `x` (price levels), `z` (index positions)
- **Python 3.7+**

### 4. PyBacktesting (Genetic Algorithm Optimization)
- **GitHub:** https://github.com/philippe-ostiguy/PyBacktesting
- **Approach:** Optimizes Elliott Wave Theory using genetic algorithms
- **Use case:** Financial market forecasting

### 5. Neural Network Approach
- **Paper:** "Elliott Waves Recognition Via Neural Networks" (Semantic Scholar)
- **Approach:** Backpropagation neural network for wave recognition in time series

---

## TradingView Indicators (Reference for UX/UI)

### 1. Elliott Wave [LuxAlgo] - Most Popular
- Auto-detects impulse and corrective segments
- Displays waves serially (track evolution)
- Includes Fibonacci retracements from detected impulses
- **FREE** on TradingView

### 2. TradingView Built-in Chart Pattern Elliott Wave
- Analyzes last 600 bars
- Two nesting levels (main waves + sub-waves)
- Validates impulse and zigzag rules
- Captures maximum amplitude price movements

### 3. Elliott Wave (STEEL CITY CREATORS)
- Rules-based: detects pivot highs/lows
- ZigZag line filtered by ATR or percentage change
- Labels waves 1-5 for bullish/bearish impulses
- Optional A-B-C corrective detection

### 4. ZigZag++ / ZigZag Channels
- Foundation for Elliott Wave counting
- Recommended settings for swing trading: Daily, Depth 12-15, Deviation 5, Backstep 2

---

## Key Takeaway for BTC Seer
- **ElliottWaveAnalyzer** is the most production-ready Python implementation
- **TAEW** is the most academically rigorous (Fibonacci-validated)
- The combination of ZigZag pivot detection + Fibonacci validation + rule checking is the proven approach
- For a premium feature, we should:
  1. Detect pivots using ZigZag/extrema detection
  2. Validate wave proportions against Fibonacci ratios
  3. Check Elliott Wave rules (Wave 3 not shortest, Wave 2 < 100% retrace, etc.)
  4. Display current wave count with confidence score
  5. Project next wave targets using Fibonacci extensions

## Sources
- https://github.com/btcorgtfo/ElliottWaveAnalyzer
- https://github.com/alessioricco/ElliottWaves
- https://pypi.org/project/taew/
- https://github.com/philippe-ostiguy/PyBacktesting
- https://www.tradingview.com/script/KvrhsPTp-Elliott-Wave-LuxAlgo/
- https://blackbull.com/en/education-hub/the-5-best-elliott-wave-indicators-on-tradingview-2/

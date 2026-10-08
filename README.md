# Stock Market Analysis in SQL

An end-to-end **SQL + Python + Streamlit** stock-market analytics project covering six NSE-listed companies from **January 2015 to July 2018**.

The project combines relational SQL analysis, window functions, moving-average crossover signals, corporate-action adjustments, data-quality checks, and an interactive Streamlit research dashboard.

## Project Overview

**Project:** Stock Market Analysis in SQL  
**Dashboard:** StockScope — Research Studio  
**Database:** MySQL for the SQL analysis; SQLite is used for the embedded dashboard SQL lab  
**Programming:** SQL, Python, Pandas, NumPy  
**Visualization:** Plotly, Streamlit  
**Coverage:** January 2015 – July 2018  
**Stocks:** Bajaj Auto, Eicher Motors, Hero Motocorp, Infosys, TCS, TVS Motors

The supplied student guide defines a structured SQL lab around moving averages and golden-cross signals. The completed SQL analysis extends that work to **22 analytical questions**, covering price behaviour, signals, corporate actions, data quality, turnover, volume, delivery activity, monthly returns, volatility, and signal reversals.

**[Explore the live dashboard](https://mainpy-ydzfqinjhwp8vx3zd4taxi.streamlit.app/)**

## Business / Analytical Objectives

1. Understand the historical structure of six stock datasets.
2. Calculate 20-day and 50-day moving averages.
3. Detect Buy, Sell and Hold crossover signals.
4. Compare stock price performance across the full historical period.
5. Identify unusual daily price movements and potential corporate-action effects.
6. Measure trading activity through volume, turnover and number of trades.
7. Examine delivery percentages and abnormal volume days.
8. Evaluate monthly returns and daily-return volatility.
9. Compare raw and corporate-action-adjusted prices.
10. Build an interactive research dashboard for exploratory analysis.

## Stocks Covered

| Stock | Dataset / SQL table |
|---|---|
| Bajaj Auto | `bajaj` |
| Eicher Motors | `eicher` |
| Hero Motocorp | `hero` |
| Infosys | `infosys` |
| TCS | `tcs` |
| TVS Motors | `tvs` |

Each dataset contains daily market fields such as date, OHLC prices, WAP, traded quantity, number of trades, turnover, deliverable quantity, delivery percentage and price-spread fields.

## SQL Analysis

The SQL file contains 22 analysis questions.

### Core SQL techniques

- `SELECT`, `WHERE`, `ORDER BY`, `GROUP BY`
- `COUNT`, `MIN`, `MAX`, `AVG`, `ROUND`
- `JOIN`
- `UNION ALL`
- Common Table Expressions (`WITH`)
- Window functions
- `ROW_NUMBER()`
- `LAG()`
- `FIRST_VALUE()` / `LAST_VALUE()`
- `PARTITION BY`
- `CASE`
- Date conversion and date arithmetic
- Views
- MySQL stored functions
- Data-quality validation

### Main analytical areas

**1–4 — Data understanding**
- Trading-day coverage
- Highest closing prices
- Annual average closing prices
- Missing deliverable quantities

**5–10 — Moving averages and trading signals**
- 20-day and 50-day moving averages
- Six-stock master table
- Golden-cross / death-cross signal detection
- Buy/Sell/Hold counts
- Signal lookup function
- Cross-stock signal summary

**11–14 — Returns, corporate actions and quality**
- Price-change comparison
- Worst daily percentage movements
- TCS and Infosys bonus adjustments
- Missing, nonpositive and inconsistent prices

**15–18 — Trading activity**
- Highest-activity trading days
- Monthly turnover and trade activity
- Abnormal-volume days
- Average delivery percentage

**19–22 — Risk and signal behaviour**
- Best and worst monthly returns
- Daily-return standard deviation
- Buy-to-Sell reversals
- TCS signal changes under an adjusted-price calculation

## Moving Average Method

The project uses trailing trading-day windows:

- **MA20:** current close + previous 19 trading observations
- **MA50:** current close + previous 49 trading observations

A signal is generated only when the relationship between MA20 and MA50 changes:

```text
Buy  = today MA20 > MA50 AND yesterday MA20 <= yesterday MA50
Sell = today MA20 < MA50 AND yesterday MA20 >= yesterday MA50
Hold = otherwise
```

This prevents every day inside an existing uptrend/downtrend from being incorrectly labelled as a new signal.

## Corporate-Action Adjustment

The dashboard implements bonus-adjusted OHLC prices for:

- **TCS:** prices before 31 May 2018 are divided by 2.
- **Infosys:** prices before 15 June 2015 are divided by 2.

The original raw prices remain available for traceability.

This is a share-basis adjustment, not a dividend-adjusted total-return series.

## Python / Streamlit Dashboard

The StockScope dashboard provides:

- Market Overview
- Risk & Distribution
- Trends & Signals
- Turnover & Activity
- Trade Simulator
- SQL Lab
- Data & Methodology

### Dashboard metrics

Depending on the selected stocks and period, the application calculates:

- Period return
- Annualised volatility
- Maximum drawdown
- CAGR
- Sharpe ratio with 0% risk-free rate
- RSI (14, simple rolling)
- Total turnover
- Trading volume
- Number of trades
- Buy/Sell signal counts

### Interactive charts

- Indexed price comparison
- Growth / decline bars
- Turnover allocation
- Growth vs volatility
- Daily-return distributions
- Indexed-price box plots
- Drawdown curves
- Return correlation
- Candlestick charts
- MA20 / MA50 overlays
- Buy/Sell markers
- Turnover trends
- Volume vs daily return
- Stock comparison radar
- Trade P&L radar

## Project Architecture

```text
CSV files
   │
   ▼
analytics.py
   ├── load_prices()
   ├── corporate-action adjustment
   ├── enrich()
   │     ├── daily returns
   │     ├── MA20 / MA50
   │     └── crossover signals
   ├── period_data()
   ├── summarize()
   ├── scorecard()
   └── simulate_trade()
   │
   ▼
main.py / Streamlit application
   ├── Market overview
   ├── Risk & distribution
   ├── Trends & signals
   ├── Turnover & activity
   ├── Trade simulator
   ├── SQL lab
   └── Data & methodology
```

## SQL Lab

The dashboard creates an in-memory SQLite database containing:

- `prices` — complete enriched dataset
- `selected_prices` — current filter selection

The SQL lab is intentionally read-only and limits query execution/output to protect the interactive application.

For MySQL submission work, review syntax differences such as date functions and reserved words.

## Data Quality Controls

The Python loader checks:

- Duplicate trading dates
- Missing closing prices
- Nonpositive closing prices
- Numeric conversion failures
- Missing deliverable observations
- Closing price consistency with daily low/high

The dashboard methodology page also documents how missing values and corporate actions are handled.

## Validation Checkpoints

The supplied SQL student guide provides useful implementation checkpoints, including:

- Each stock has **889 daily observations**.
- TCS's 2016 average closing price is **₹2,419.00**.
- The first complete Bajaj MA20 occurs on **29 January 2015** and is **2,415.53**.
- The first complete Bajaj MA50 occurs on **13 March 2015** and is **2,283.80**.
- Bajaj MA20 on **31 July 2018** is **2,918.51**.
- The first Bajaj Buy signal is **18 May 2015**.
- The first Bajaj Sell signal is **24 August 2015**.

These are guide/checkpoint values and should be reproduced against the original datasets before being presented as final analytical findings.

## Important SQL Review Notes

Before using the SQL file as a production-quality analysis, review these implementation details:

1. **Question 11:** the percentage-change query uses `MAX(close_price)` and `MIN(close_price)`. If the requirement is specifically first trading close to last trading close, the calculation should use the prices at the earliest and latest dates rather than numerical minimum/maximum prices.
2. **Question 15:** the question asks for highest turnover dates, while the current query selects `no. of trades`. Use the turnover field if turnover is the intended metric.
3. **Question 19:** the query is labelled as adjusted-price analysis but currently unions the `close price` field directly. Apply the same corporate-action adjustment logic used elsewhere if adjusted prices are required.
4. **Question 22:** the comparison labelled as adjusted-price signals should be checked so that the adjusted corporate-action series and the same crossover definition are used consistently.

These are analytical-quality observations, not blockers for the dashboard architecture.

## How to Run

### 1. Install dependencies

```bash
pip install pandas numpy plotly streamlit
```

### 2. Place the six CSV files

```text
stock-market-analysis-sql-streamlit/
│
├── main.py
├── analytics.py
├── visual.py
├── requirements.txt
├── README.md
│
└── Raw File/
    ├── Bajaj Auto.csv
    ├── Eicher Motors.csv
    ├── Hero Motocorp.csv
    ├── Infosys.csv
    ├── TCS.csv
    └── TVS Motors.csv
```

### 3. Run the dashboard

```bash
streamlit run main.py
```

## Suggested GitHub Repository Structure

```text
stock-market-analysis-sql/
│
├── data/
│   └── *.csv
├── sql/
│   └── stock_market_analysis.sql
├── main.py
├── analytics.py
├── visual.py
├── README.md
├── Stock_Market_Analysis_Project_Report.pdf
└── requirements.txt
```

## Learning Outcomes

This project demonstrates practical ability in:

- SQL data analysis
- Advanced SQL window functions
- Financial time-series analysis
- Moving-average indicators
- Crossover signal logic
- CTE-based query design
- Data-quality validation
- Corporate-action handling
- Python/Pandas analytics
- Streamlit application development
- Plotly visualisation
- Interactive SQL execution
- Translating analytical requirements into reusable workflows

## Limitations

- Historical data ends in July 2018 and is not a live market feed.
- Only six companies are analysed.
- Results are price-based and do not represent total shareholder return.
- Dividends, taxes, inflation and real-world execution effects are not included.
- Historical volatility is not a complete measure of investment risk.
- Crossover signals are historical analytical events, not guaranteed trading recommendations.
- Corporate-action adjustments are limited to the documented bonus events.

## Disclaimer

This project is for **educational and portfolio purposes**. The analysis is not financial advice, a recommendation to buy or sell securities, or a prediction of future returns.

## Author

**Ankan Chowdhury**

Built as a SQL + Python data analytics portfolio project.

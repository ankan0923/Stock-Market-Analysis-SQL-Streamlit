from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from visual import sql_result_chart,render_comparison,card,growth_bars,turnover_ring,pnl_radar,black_table,GREEN,RED
from analytics import load_prices,enrich,period_data,summarize,sql_run,simulate_trade,STOCKS

def render_methodology(raw,selected):
    st.subheader('Project objective')
    st.write('Compare six stocks using historical price growth, risk, trading activity and moving-average signals. The SQL lab lets you reproduce the analysis and test your own questions. This dataset covers January 2015 to July 2018; it is not a live market feed.')
    st.subheader('Data coverage and quality')
    rows=[]
    for stock,g in raw.groupby('stock'):
        rows.append({'Stock':stock,'Rows':len(g),'First date':g.date.min().date(),'Last date':g.date.max().date(),
          'Duplicate dates':int(g.date.duplicated().sum()),'Missing close':int(g.close.isna().sum()),
          'Missing delivery quantity':int(g.deliverable_qty.isna().sum()),
          'Missing delivery %':int(g.delivery_pct.isna().sum()),
          'Nonpositive close':int((g.close<=0).sum()),
          'Close outside low/high':int(((g.close<g.low)|(g.close>g.high)).sum())})
    black_table(pd.DataFrame(rows),hide_index=True)
    st.caption(f'Full dataset: {len(raw):,} stock-day records. Current selection: {len(selected):,} records across {selected.stock.nunique()} stocks and {selected.date.nunique()} trading dates.')
    with st.expander('Preparation and missing values',expanded=True):
        st.markdown('''1. Read the six supplied CSVs and keep their original financial fields.
2. Parse dates such as `31-July-2018` and sort by stock, then date.
3. Convert price, volume and turnover columns to numeric values. Unparseable numeric cells become missing values.
4. Stop loading if duplicate dates or missing/nonpositive closing prices are found.
5. Keep missing delivery observations as missing; do not turn them into zero or remove the associated price row.
6. Create separate bonus-adjusted OHLC columns; retain original prices, volume and turnover.
7. Calculate full-window moving averages before applying the date filter. Calculate period returns and drawdowns after filtering.

Missing delivery values are excluded from mean delivery percentage. Other numeric fields may still need investigation if you replace the supplied CSVs. The loader does not validate an exchange holiday calendar or automatically repair outliers.''')
    with st.expander('Data dictionary',expanded=True):
        dictionary=[('date','Trading date; one observation per stock per trading day'),('stock','Company name'),
        ('open / high / low / close','Original quoted daily prices in rupees per share'),('wap','Weighted average trading price supplied in the CSV'),
        ('volume','Reported number of shares traded'),('trades','Reported number of transactions'),('turnover','Reported trading value in rupees; not company revenue'),
        ('deliverable_qty','Shares marked for delivery'),('delivery_pct','Reported deliverable quantity as a percentage of traded quantity'),
        ('spread_high_low','Original daily high minus low, in rupees'),('spread_close_open','Original close minus open, in rupees'),
        ('adj_open / adj_high / adj_low / adj_close','Bonus-adjusted OHLC values'),('price','Active analysis close: adjusted by default, raw if selected'),
        ('daily_return_pct','Daily percentage change with full-history prior observations'),('period_return_pct','Daily percentage change inside the selected interval; first row is missing'),
        ('indexed','Active close rebased to 100 at the selected start'),('drawdown_pct','Percentage below the highest active close so far in the selection'),
        ('ma20 / ma50','Unrounded trailing averages over 20 / 50 trading observations'),('signal','Buy, Sell or Hold based on a two-day crossover comparison')]
        black_table(pd.DataFrame(dictionary,columns=['Field','Meaning']),hide_index=True)
    with st.expander('KPI formulas and units',expanded=True):
        formulas=[('Period growth (%)','100 × (last selected price / first selected price − 1)'),
        ('Indexed price','100 × current price / first selected price'),('Daily return (%)','100 × (price / previous trading close − 1)'),
        ('Annualised volatility (%)','Sample standard deviation of daily percentage returns × √252'),
        ('Maximum drawdown (%)','Minimum of 100 × (price / running highest price − 1)'),
        ('CAGR (%)','100 × ((last / first)^(365.25 / calendar days) − 1)'),
        ('Sharpe (0% risk-free)','Mean daily decimal return / sample daily standard deviation × √252; undefined at zero volatility'),
        ('RSI (14), simple rolling','100 − 100/(1 + average gain / average loss), using 14 price changes; differs from Wilder smoothing'),
        ('Total turnover (₹)','Sum of supplied turnover over selected stocks and dates; 1 crore = 10,000,000'),
        ('Turnover share (%)','100 × stock turnover / combined selected-stock turnover'),
        ('Latest share price (₹)','Original raw close on the final selected trading day')]
        black_table(pd.DataFrame(formulas,columns=['Metric','Calculation']),hide_index=True)
        st.caption('CAGR annualises the observed interval, not a forecast. Sharpe assumes a zero risk-free rate and excludes dividends and costs. Very short intervals are not reliable for annualised comparisons.')
    with st.expander('Corporate actions and moving-average signals'):
        st.markdown('''**Bonus adjustments:** divide TCS prices before 31 May 2018 and Infosys prices before 15 June 2015 by two. On/after each date, keep original prices. These 1:1 bonus adjustments put historical prices on a consistent share basis. This does not create a dividend-adjusted total-return series.

**Moving averages:** MA20 uses the current close plus the previous 19 trading closes; MA50 uses the current close plus the previous 49. Require a full window. Weekends are not counted as trading observations.

**Buy:** today MA20 > MA50 and yesterday MA20 ≤ MA50. **Sell:** today MA20 < MA50 and yesterday MA20 ≥ MA50. **Hold:** all other cases, including missing required averages.

Signals are known only after that day's close. The dashboard shows historical events, not evidence that trades could be filled at that close. The separate trade simulator is a user-selected entry/exit calculation, not a crossover backtest.''')
    with st.expander('How to read charts and filters'):
        st.markdown('''- Stock and date filters affect charts, KPIs and `selected_prices` in the SQL lab. `prices` retains all six stocks and full history.
- Adjusted/raw selection changes growth, risk, distributions and signals. Latest raw price, volume, turnover and trade execution prices retain their original meaning.
- A card's sparkline shows the selected price path. Its arrow and green/red direction indicate first-to-last growth, not every daily movement.
- Growth bars start at zero: losses extend left and gains right. All bars can be positive for some periods.
- The turnover ring shows contribution among selected stocks, not ownership or whole-exchange share.
- Return histograms show daily dispersion; indexed-price box plots show the distribution of price levels rebased to 100.
- The comparison radar uses per-metric min–max scaling across the compared stocks. Each spoke has its own scale; the adjacent black table shows actual units. A larger radar shape is not a better investment, since high volatility and large drawdowns reflect risk. Equal values are placed at 50, unavailable values are omitted.
- The P&L radar separately shows positive profit and positive loss magnitude; hover shows signed net P&L.
- Black tables are scrollable presentation tables; CSV downloads retain the underlying values.''')
    with st.expander('Trade simulator and SQL lab'):
        st.markdown('''**Trade simulator:** give each stock the same starting amount; buy only whole shares at the selected historical close and retain unused cash. Charge the entered basis-point fee on entry and exit. Double share holdings if the position spans one of the known bonus events. Ending value includes unused cash. Excludes dividends, taxes, slippage and cash interest.

**SQL lab:** an in-memory SQLite database with full and filtered tables, precomputed analysis columns and editable examples. Only read queries are permitted; one statement, 5,000 output rows and approximately three seconds of execution. For MySQL submissions, translate date functions and review dialect differences. No permanent database writes occur.''')
    with st.expander('Limitations and interpretation'):
        st.markdown('''- Six historical companies do not represent the whole stock market. There is no benchmark index or market-cap/ownership data.
- These are price-based results. Dividend reinvestment, inflation, taxes, execution costs and survivorship effects are not included in growth comparisons.
- Volatility measures historical variation, not every form of investment risk. Correlation is sample-dependent.
- Short intervals, corporate actions and missing observations can affect statistics. Never call a high nominal share price the largest company.
- Sources for the known bonus events are retained in the README. The dashboard preserves the original CSVs for traceability.''')
    with st.expander('Filtered data preview'):
        black_table(selected.head(100),hide_index=True)


st.set_page_config(page_title='StockScope | SQL & Market Lab',page_icon='◈',layout='wide')
st.markdown('''<style>
.stApp{background:#0a1020;color:#edf2ff} [data-testid="stSidebar"]{background:#101a30}
.block-container{padding-top:4.5rem} [data-testid="stMetric"]{background:#131f36;border:1px solid #263958;border-radius:14px;padding:16px}
h1{letter-spacing:-1.5px} .eyebrow{color:#54dec5;letter-spacing:3px;font-size:12px;font-weight:700}
.intro{color:#a8b9d2;max-width:900px;margin-bottom:24px}
.motion-card{display:flex;align-items:center;gap:12px;background:linear-gradient(135deg,#16263f,#0f192d);border:1px solid #30415c;border-top:2px solid var(--accent);border-radius:12px;padding:12px 14px;margin:4px 0 10px;min-height:90px;box-sizing:border-box;animation:arrive .55s ease-out;transition:transform .2s}
.motion-card:hover{transform:translateY(-2px)}.card-copy{flex:1;min-width:0}.card-label{font-size:11px;color:#b7c7df;line-height:1.4;margin-bottom:3px}.card-value{font-size:clamp(18px,1.6vw,24px);font-weight:750;color:#f1f5ff;line-height:1.3;overflow-wrap:anywhere}.card-arrow{color:var(--accent);font-size:19px;margin-right:5px}.card-detail{color:var(--accent);font-size:11px;margin-top:4px;line-height:1.4}.card-spark:empty{display:none}.card-spark{width:36%;flex-shrink:0}.card-spark svg{display:block;width:100%;height:48px}.spark{stroke-dasharray:1;stroke-dashoffset:0;animation:draw 1.3s ease-out}
[data-testid="stMetric"]{padding:10px 14px!important;border-radius:12px!important;min-height:0!important}[data-testid="stMetricValue"]{font-size:1.5rem!important}[data-testid="stMetricLabel"]{font-size:.75rem!important}
.black-table-wrap{background:#050505;border:1px solid #30343c;border-radius:12px;overflow:auto;max-height:460px;margin:8px 0 18px;color:#edf2ff}.black-table{width:100%;border-collapse:separate;border-spacing:0;font-size:12px;background:#050505!important;color:#edf2ff!important}.black-table th,.black-table td{background:#050505!important;color:#edf2ff!important;border-bottom:1px solid #252930;border-right:1px solid #252930;padding:10px 12px;white-space:nowrap;text-align:right}.black-table thead th{position:sticky;top:0;background:#111!important;color:#a8b9d2!important;z-index:1}.black-table tbody th,.black-table th:first-child,.black-table td:first-child{text-align:left}.black-table tbody tr:hover td{background:#151515!important}
@media(max-width:700px){.card-spark{width:30%}.card-value{font-size:19px}}
@keyframes draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}@keyframes arrive{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@media(prefers-reduced-motion:reduce){.motion-card,.spark{animation:none;transition:none}}
</style>''',unsafe_allow_html=True)
COLORS=['#54dec5','#75a7ff','#b49aff','#ffc477','#f383aa','#91d377']
px.defaults.color_discrete_sequence=COLORS
px.defaults.template='plotly_dark'

@st.cache_data
def get_data():
    root=Path(__file__).parent
    for folder in [root/'data',root]:
        if all((folder/f'{name}.csv').exists() for name in STOCKS):
            return load_prices(folder)
    raise FileNotFoundError('Place all six original CSVs together in data/ or beside app.py')

def chart(fig):
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',
                      margin=dict(l=15,r=15,t=55,b=25),legend_title_text='',font=dict(color='#cdd9ed'))
    st.plotly_chart(fig,width='stretch')

def money(n):
    return f'₹{n/1e7:,.2f} Cr' if abs(n)>=1e7 else f'₹{n:,.2f}'

try: raw=get_data()
except Exception as e:
    st.error(f'Unable to load data: {e}. Keep all six CSVs in the data folder.'); st.stop()

with st.sidebar:
    st.markdown('## ◈ StockScope')
    st.caption('HISTORICAL MARKET PLAYGROUND')
    page=st.radio('Workspace',['Market overview','Risk & distribution','Trends & signals','Turnover & activity','Trade simulator','SQL lab','Data & methodology'])
    stocks=st.multiselect('Compare stocks',STOCKS,default=STOCKS)
    dates=st.date_input('Analysis period',(raw.date.min().date(),raw.date.max().date()),
                       min_value=raw.date.min().date(),max_value=raw.date.max().date())
    basis=st.radio('Price basis',['Bonus-adjusted','Raw'],help='Return, risk and signals use this basis. Turnover and volume remain reported values.')
    st.caption('Dataset: Jan 2015 – Jul 2018. No live market feed.')

if not stocks or len(dates)!=2:
    st.info('Choose at least one stock and a complete date range.'); st.stop()
full=enrich(raw,basis=='Bonus-adjusted')
d=period_data(full,stocks,*dates)
if d.empty or d.date.nunique()<2:
    st.info('Choose a period containing at least two trading days.'); st.stop()
summary=summarize(d)
st.markdown('<div class="eyebrow">STOCKSCOPE / RESEARCH STUDIO</div>',unsafe_allow_html=True)
st.title(page)
st.markdown(f'<div class="intro">Six companies. One research workspace. Explore growth, price dispersion and trading activity.<br>{d.date.min():%d %b %Y} — {d.date.max():%d %b %Y} · {basis} analysis · {len(stocks)} selected stocks</div>',unsafe_allow_html=True)
if basis=='Raw': st.warning('Raw TCS and Infosys prices contain bonus-related discontinuities. Their raw returns and risk measures can be misleading.')

if page=='Market overview':
    best=summary.loc[summary.growth_pct.idxmax()]; high=summary.loc[summary.last_close.idxmax()]
    a,b,c,e=st.columns(4)
    card(a,'Growth leader',best.stock,f'{best.growth_pct:+.2f}% selected-period growth',positive=bool(best.growth_pct>=0))
    card(b,'Highest latest raw share price',high.stock,money(high.last_close))
    card(c,'Total reported turnover',money(summary.turnover.sum()),'Selected stocks and dates')
    card(e,'Stocks with positive growth',f'{(summary.growth_pct>0).sum()} / {len(summary)}','Above the selected starting close')
    st.caption('Highest share price is the price per share, not company value or market capitalisation.')
    cols=st.columns(3)
    for i,row in summary.iterrows():
        card(cols[i%3],row.stock,money(row.last_close),f'{row.growth_pct:+.2f}% period growth · {basis}',series=d.loc[d.stock==row.stock,'price'],positive=bool(row.growth_pct>=0))
    chart(px.line(d,x='date',y='indexed',color='stock',title='Growth comparison · first selected close = 100',labels={'indexed':'Indexed price','date':'Trading date'}))
    left,right=st.columns(2)
    with left: chart(growth_bars(summary))
    with right: chart(turnover_ring(summary,COLORS))
    black_table(summary.round(2),hide_index=True,width='stretch')

elif page=='Risk & distribution':
    safe=summary.loc[summary.annual_volatility_pct.idxmin()]
    a,b,c=st.columns(3)
    a.metric('Lowest realised volatility',safe.stock,f'{safe.annual_volatility_pct:.2f}% annualised',delta_color='off')
    b.metric('Largest observed drawdown',f'{summary.max_drawdown_pct.min():.2f}%')
    c.metric('Risk observations',f'{d.period_return_pct.notna().sum():,}')
    chart(px.scatter(summary,x='annual_volatility_pct',y='growth_pct',size='turnover',color='stock',hover_name='stock',size_max=55,
                     title='Growth versus volatility · bubble size = turnover',labels={'annual_volatility_pct':'Annualised daily volatility (%)','growth_pct':'Selected-period growth (%)'}))
    l,r=st.columns(2)
    with l: chart(px.histogram(d.dropna(subset=['period_return_pct']),x='period_return_pct',color='stock',nbins=70,barmode='overlay',opacity=.55,histnorm='probability density',title='Daily return distribution'))
    with r: chart(px.box(d,x='stock',y='indexed',color='stock',points=False,title='Price spread · indexed to 100 for comparability'))
    chart(px.line(d,x='date',y='drawdown_pct',color='stock',title='Drawdown from each stock’s selected-period peak (%)'))
    corr=d.pivot(index='date',columns='stock',values='period_return_pct').corr()
    chart(px.imshow(corr,zmin=-1,zmax=1,color_continuous_scale='RdBu_r',text_auto='.2f',title='Daily return correlation'))
    spread=d.groupby('stock').period_return_pct.agg(['mean','std','min','max',lambda x:x.quantile(.25),lambda x:x.quantile(.75)])
    spread.columns=['Mean daily %','Daily standard deviation %','Worst daily %','Best daily %','25th percentile %','75th percentile %']
    black_table(spread.round(3),width='stretch')
    st.caption('Volatility = sample standard deviation of daily returns × √252. Drawdown starts at the selected period’s first close. Dispersion describes variation, not a forecast.')

elif page=='Trends & signals':
    stock=st.selectbox('Inspect stock',stocks); s=d[d.stock==stock]
    prefix='adj_' if basis=='Bonus-adjusted' else ''
    fig=go.Figure(go.Candlestick(x=s.date,open=s[prefix+'open'],high=s[prefix+'high'],low=s[prefix+'low'],close=s[prefix+'close'],name=stock,increasing_line_color='#54dec5',decreasing_line_color='#f383aa'))
    for col,color in [('ma20','#ffc477'),('ma50','#75a7ff')]: fig.add_trace(go.Scatter(x=s.date,y=s[col],name=col.upper(),line=dict(color=color,width=2)))
    for signal,symbol,color in [('Buy','triangle-up',GREEN),('Sell','triangle-down',RED)]:
        hits=s[s.signal==signal]
        fig.add_trace(go.Scatter(x=hits.date,y=hits.price,mode='markers',name=signal,marker=dict(symbol=symbol,size=12,color=color)))
    fig.update_layout(title=f'{stock} · price, full-window averages and crossover signals',height=550,xaxis_rangeslider_visible=False)
    chart(fig)
    st.caption('20/50 trading-day averages use available history before your selected start date. Signals occur only on crossover days. Full windows are required; averages are not rounded before comparison.')
    counts=d.groupby(['stock','signal']).size().reset_index(name='days')
    chart(px.bar(counts,x='stock',y='days',color='signal',color_discrete_map={'Buy':GREEN,'Sell':RED,'Hold':'#64748b'},barmode='group',log_y=True,title='Signal counts · logarithmic axis'))
    black_table(s[s.signal!='Hold'][['date','close','price','ma20','ma50','signal']],hide_index=True,width='stretch')

elif page=='Turnover & activity':
    a,b,c=st.columns(3)
    a.metric('Total turnover',money(d.turnover.sum())); b.metric('Shares traded',f'{d.volume.sum():,.0f}'); c.metric('Trades executed',f'{d.trades.sum():,.0f}')
    frequency=st.selectbox('Trend granularity',['Daily','Weekly','Monthly'],index=2)
    rule={'Daily':'D','Weekly':'W','Monthly':'MS'}[frequency]
    trend=d.set_index('date').groupby('stock').resample(rule)[['turnover','volume','trades']].sum().reset_index()
    trend['turnover_crore']=trend.turnover/1e7
    chart(px.line(trend,x='date',y='turnover_crore',color='stock',title=f'{frequency} turnover (₹ crore)'))
    l,r=st.columns(2)
    with l: chart(px.bar(summary,x='stock',y='volume',color='stock',title='Total shares traded by stock'))
    with r: chart(px.scatter(d,x='volume',y='period_return_pct',color='stock',opacity=.4,log_x=True,title='Volume versus daily return (%)'))
    st.subheader('Top five turnover days per stock')
    black_table(d.sort_values(['turnover','date'],ascending=[False,True]).groupby('stock').head(5)[['stock','date','turnover','volume','trades']].sort_values(['stock','turnover'],ascending=[True,False]),hide_index=True,width='stretch')
    delivery=d.groupby('stock').delivery_pct.mean().reset_index()
    delivery_chart=px.bar(delivery,x='stock',y='delivery_pct',color='stock',text_auto='.2f',title='Average daily delivery percentage · missing values excluded')
    delivery_chart.add_trace(go.Scatter(x=delivery.stock,y=delivery.delivery_pct,mode='lines+markers',name='Stock comparison line',line=dict(color='#ffc477',width=3),marker=dict(size=8),hovertemplate='%{x}<br>Average delivery: %{y:.2f}%<extra></extra>'))
    chart(delivery_chart)
    st.caption('The line connects stock averages in the displayed order; it is not a trend over time.')
    st.caption('Turnover share refers only to these selected stocks and the supplied dataset, not the whole exchange. Volume is reported share count, not adjusted for bonus issues.')

elif page=='Trade simulator':
    st.info('Historical buy-and-sell calculator. Choose entry/exit closes for any stock; no orders are sent. This is not a crossover-strategy backtest.')
    capital=st.number_input('Starting amount per stock (₹)',min_value=1000.,value=100000.,step=10000.)
    fee=st.number_input('Cost per side (basis points; 10 = 0.10%)',min_value=0.,max_value=1000.,value=10.)
    available=sorted(d.date.unique())
    a,b=st.columns(2)
    buy=a.selectbox('Entry trading day',available,format_func=lambda x:pd.Timestamp(x).strftime('%d %b %Y'))
    sell=b.selectbox('Exit trading day',available,index=len(available)-1,format_func=lambda x:pd.Timestamp(x).strftime('%d %b %Y'))
    if pd.Timestamp(sell)<=pd.Timestamp(buy): st.warning('Choose an exit date after entry.')
    else:
        results=[]
        for stock in stocks:
            price=float(raw.loc[(raw.stock==stock)&(raw.date==buy),'close'].iloc[0])
            shares=int(capital//(price*(1+fee/10000)))
            if shares==0:
                results.append({'stock':stock,'entry_shares':0,'exit_shares':0,'pnl':0.,'ending_value':capital,'account_return_pct':0.,'fees':0.}); continue
            result=simulate_trade(raw,stock,buy,sell,shares,fee)
            results.append({'stock':stock,'entry_shares':shares,**result,'ending_value':capital+result['pnl'],'account_return_pct':100*result['pnl']/capital})
        trades=pd.DataFrame(results)
        a,b,c=st.columns(3)
        card(a,'Total starting capital',money(capital*len(stocks)),f'{len(stocks)} independent allocations')
        card(b,'Ending value including cash',money(trades.ending_value.sum()),'After entered transaction costs')
        card(c,'Net profit / loss',money(trades.pnl.sum()),f'{100*trades.pnl.sum()/(capital*len(stocks)):+.2f}% account return',positive=bool(trades.pnl.sum()>=0))
        render_comparison(d,full,stocks,COLORS)
        with st.expander('Net profit / loss radar',expanded=False):
            chart(pnl_radar(trades))
        st.caption('Green shows profit; red shows loss magnitude. Both use the same rupee scale from zero. Hover for signed net P&L. Select at least three stocks for a full radar polygon.')
        black_table(trades.round(2),hide_index=True,width='stretch')
        st.caption('Uses raw historical closes, whole shares, uninvested cash, and doubles holdings when a known 1:1 bonus occurs between entry and exit. Excludes dividends, taxes, slippage and interest on cash. Independent equal starting amounts; not a rebalanced portfolio.')
        st.download_button('Download trade comparison',trades.to_csv(index=False),'historical_trades.csv','text/csv')

elif page=='SQL lab':
    st.caption('Read-only SQLite playground. prices = full history for all stocks; selected_prices = current stock/date filters. Both use the selected price basis. MySQL uses YEAR(date); SQLite uses strftime. No database installation needed.')
    examples={
      'Growth by stock':"WITH r AS (SELECT *, ROW_NUMBER() OVER(PARTITION BY stock ORDER BY date) a, ROW_NUMBER() OVER(PARTITION BY stock ORDER BY date DESC) b FROM selected_prices) SELECT stock, ROUND(100.0*(MAX(CASE WHEN b=1 THEN price END)/MAX(CASE WHEN a=1 THEN price END)-1),2) growth_pct FROM r GROUP BY stock ORDER BY growth_pct DESC;",
      'Turnover leaders':"SELECT stock, ROUND(SUM(turnover)/10000000.0,2) turnover_crore, SUM(volume) shares_traded FROM selected_prices GROUP BY stock ORDER BY turnover_crore DESC;",
      'Signal counts':"SELECT stock, SUM(signal='Buy') buys, SUM(signal='Sell') sells, SUM(signal='Hold') holds FROM selected_prices GROUP BY stock;",
      'Top 5 turnover days':"WITH r AS (SELECT stock,date,turnover,ROW_NUMBER() OVER(PARTITION BY stock ORDER BY turnover DESC,date) rn FROM selected_prices) SELECT stock,date,turnover FROM r WHERE rn<=5 ORDER BY stock,rn;",
      'Monthly turnover':"SELECT stock,strftime('%Y-%m',date) month,ROUND(SUM(turnover),2) turnover FROM selected_prices GROUP BY stock,month ORDER BY stock,month;",
      'Missing delivery values':"SELECT stock,date,deliverable_qty FROM prices WHERE deliverable_qty IS NULL ORDER BY date,stock;",
      'Worst daily moves':"WITH r AS (SELECT stock,date,period_return_pct,ROW_NUMBER() OVER(PARTITION BY stock ORDER BY period_return_pct,date) rn FROM selected_prices WHERE period_return_pct IS NOT NULL) SELECT stock,date,ROUND(period_return_pct,2) daily_move_pct FROM r WHERE rn=1;",
      'Moving averages':"SELECT stock,date,price,ROUND(ma20,2) ma20,ROUND(ma50,2) ma50,signal FROM selected_prices ORDER BY stock,date;",
      'Highest latest share price':"WITH r AS (SELECT stock,date,close,ROW_NUMBER() OVER(PARTITION BY stock ORDER BY date DESC) rn FROM selected_prices) SELECT stock,date,close FROM r WHERE rn=1 ORDER BY close DESC;",
      'Volume spikes':"WITH r AS (SELECT stock,date,volume,AVG(volume) OVER w avg20,COUNT(volume) OVER w n FROM prices WINDOW w AS (PARTITION BY stock ORDER BY date ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING)) SELECT * FROM r WHERE n=20 AND volume>2*avg20 ORDER BY stock,date;"
    }
    choice=st.selectbox('Load a worked query',list(examples))
    query=st.text_area('Edit SQL',examples[choice],height=220,key='sql_'+choice)
    context=(query,tuple(stocks),str(dates[0]),str(dates[1]),basis)
    if st.button('Run SQL',type='primary'):
        for key in ['sql_chart_type','sql_x','sql_y','sql_group','sql_agg','sql_count_col']:
            st.session_state.pop(key,None)
        st.session_state.pop('sql_result',None)
        try:
            result,truncated=sql_run(full,d,query)
            st.session_state['sql_result']=(context,result,truncated)
        except Exception as e: st.error(f'Query could not run: {e}')
    saved=st.session_state.get('sql_result')
    if saved is not None and saved[0]==context:
        _,result,truncated=saved
        st.success(f'{len(result):,} rows returned'+(' (limited to 5,000)' if truncated else ''))
        black_table(result,width='stretch',hide_index=True)
        sql_result_chart(result)
        st.download_button('Download query results',result.to_csv(index=False),'sql_results.csv','text/csv')
        st.download_button('Download SQL',query,'analysis.sql','text/plain')
    elif saved is not None:
        st.info('Query or filters changed. Run SQL again to refresh the table and chart.')
    with st.expander('Tables and columns'):
        black_table(pd.DataFrame({'column':d.columns,'type':d.dtypes.astype(str).values}),hide_index=True)
    with st.expander('More challenges'):
        st.markdown('1. Find the latest non-Hold signal per stock.\n2. Calculate year-wise average closing prices.\n3. Compare raw and adjusted full-period growth.\n4. Find Buy-to-Sell reversals within 10 trading rows.\n5. Calculate monthly close-to-close returns.\n6. Compare raw and adjusted TCS crossover dates.')

else:
    render_methodology(raw,d)

st.divider()
st.download_button('Export filtered analysis CSV',d.to_csv(index=False),'stock_analysis_filtered.csv','text/csv',key='export_all')
st.caption('StockScope · Historical analysis and SQL practice · Prices are from the supplied project files')

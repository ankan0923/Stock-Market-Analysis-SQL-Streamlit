from pathlib import Path
import sqlite3
import time
import numpy as np
import pandas as pd

STOCKS = ['Bajaj Auto', 'Eicher Motors', 'Hero Motocorp', 'Infosys', 'TCS', 'TVS Motors']
EVENTS = {'Infosys': pd.Timestamp('2015-06-15'), 'TCS': pd.Timestamp('2018-05-31')}
RENAME = {'Date':'date','Open Price':'open','High Price':'high','Low Price':'low',
          'Close Price':'close','WAP':'wap','No.of Shares':'volume','No. of Trades':'trades',
          'Total Turnover (Rs.)':'turnover','Deliverable Quantity':'deliverable_qty',
          '% Deli. Qty to Traded Qty':'delivery_pct','Spread High-Low':'spread_high_low',
          'Spread Close-Open':'spread_close_open'}

def load_prices(folder):
    frames=[]
    for stock in STOCKS:
        f=Path(folder)/f'{stock}.csv'
        d=pd.read_csv(f).rename(columns=RENAME)
        d['date']=pd.to_datetime(d['date'],format='%d-%B-%Y',errors='raise')
        for c in RENAME.values():
            if c!='date': d[c]=pd.to_numeric(d[c],errors='coerce')
        d['stock']=stock
        if d['date'].duplicated().any(): raise ValueError(f'Duplicate dates in {stock}')
        if d['close'].isna().any() or (d['close']<=0).any():
            raise ValueError(f'Missing/nonpositive closing prices in {stock}')
        factor=np.where(d['date']<EVENTS[stock],2.,1.) if stock in EVENTS else np.ones(len(d))
        for c in ['open','high','low','close']: d['adj_'+c]=d[c]/factor
        frames.append(d)
    return pd.concat(frames,ignore_index=True).sort_values(['stock','date']).reset_index(drop=True)

def enrich(data, adjusted=True):
    d=data.copy()
    d['price']=d['adj_close'] if adjusted else d['close']
    g=d.groupby('stock')['price']
    d['daily_return_pct']=g.pct_change(fill_method=None)*100
    d['ma20']=g.transform(lambda s:s.rolling(20,min_periods=20).mean())
    d['ma50']=g.transform(lambda s:s.rolling(50,min_periods=50).mean())
    prev20=d.groupby('stock')['ma20'].shift()
    prev50=d.groupby('stock')['ma50'].shift()
    d['signal']=np.select([(d.ma20>d.ma50)&(prev20<=prev50),
                           (d.ma20<d.ma50)&(prev20>=prev50)],['Buy','Sell'],default='Hold')
    return d

def period_data(full, stocks, start, end):
    d=full[full.stock.isin(stocks)&full.date.between(pd.Timestamp(start),pd.Timestamp(end))].copy()
    # Period risk excludes the move from the day before the selected start.
    d['period_return_pct']=d.groupby('stock').price.pct_change(fill_method=None)*100
    d['indexed']=100*d.price/d.groupby('stock').price.transform('first')
    d['drawdown_pct']=100*(d.price/d.groupby('stock').price.cummax()-1)
    return d

def summarize(d):
    rows=[]
    for stock,g in d.groupby('stock',sort=True):
        returns=g.period_return_pct.dropna()
        rows.append({'stock':stock,'last_close':g.close.iloc[-1],'growth_pct':100*(g.price.iloc[-1]/g.price.iloc[0]-1),
          'daily_volatility_pct':returns.std(ddof=1),'annual_volatility_pct':returns.std(ddof=1)*np.sqrt(252),
          'max_drawdown_pct':g.drawdown_pct.min(),'turnover':g.turnover.sum(),'volume':g.volume.sum(),
          'trades':g.trades.sum(),'buy_signals':int((g.signal=='Buy').sum()),'sell_signals':int((g.signal=='Sell').sum()),
          'observations':len(g)})
    return pd.DataFrame(rows)

def sql_run(full,selected,query):
    conn=sqlite3.connect(':memory:')
    try:
        for name,frame in [('prices',full),('selected_prices',selected)]:
            frame=frame.copy(); frame['date']=frame.date.dt.strftime('%Y-%m-%d')
            frame.to_sql(name,conn,index=False)
        conn.execute('PRAGMA query_only=ON')
        permitted={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE}
        conn.set_authorizer(lambda action,*args:sqlite3.SQLITE_OK if action in permitted else sqlite3.SQLITE_DENY)
        deadline=time.monotonic()+3
        conn.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
        cur=conn.execute(query)
        result=cur.fetchmany(5001)
        return pd.DataFrame(result[:5000],columns=[c[0] for c in cur.description]),len(result)>5000
    finally: conn.close()

def simulate_trade(full,stock,buy_date,sell_date,shares,fee_bps):
    d=full[full.stock==stock].set_index('date')
    b=pd.Timestamp(buy_date); s=pd.Timestamp(sell_date)
    if s<=b: raise ValueError('Exit date must follow entry date.')
    multiplier=2 if stock in EVENTS and b<EVENTS[stock]<=s else 1
    buy=float(d.loc[b,'close']); sell=float(d.loc[s,'close'])
    cost=buy*shares; proceeds=sell*shares*multiplier
    fees=(cost+proceeds)*fee_bps/10000
    pnl=proceeds-cost-fees
    return dict(entry_price=buy,exit_price=sell,exit_shares=shares*multiplier,
                investment=cost+cost*fee_bps/10000,fees=fees,pnl=pnl,
                return_pct=100*pnl/(cost+cost*fee_bps/10000))


def scorecard(selected,full):
    out=summarize(selected).set_index('stock')[['growth_pct','annual_volatility_pct','max_drawdown_pct']]
    out.columns=['Total return %','Volatility %','Max drawdown %']
    for stock,g in selected.groupby('stock'):
        days=(g.date.iloc[-1]-g.date.iloc[0]).days
        out.loc[stock,'CAGR %']=100*((g.price.iloc[-1]/g.price.iloc[0])**(365.25/days)-1) if days>0 else np.nan
        returns=g.period_return_pct.dropna()/100
        sd=returns.std(ddof=1)
        out.loc[stock,'Sharpe (Rf=0%)']=returns.mean()/sd*np.sqrt(252) if pd.notna(sd) and sd>0 else np.nan
        prices=full.loc[(full.stock==stock)&(full.date<=g.date.max()),'price']
        diff=prices.diff();gain=diff.clip(lower=0).rolling(14,min_periods=14).mean().iloc[-1]
        loss=-diff.clip(upper=0).rolling(14,min_periods=14).mean().iloc[-1]
        out.loc[stock,'RSI (14, simple)']=np.nan if pd.isna(gain) or pd.isna(loss) else (50 if gain==loss==0 else 100 if loss==0 else 100-100/(1+gain/loss))
    return out[['Total return %','CAGR %','Volatility %','Max drawdown %','Sharpe (Rf=0%)','RSI (14, simple)']]


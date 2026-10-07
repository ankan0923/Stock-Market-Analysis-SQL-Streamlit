from html import escape
import numpy as np
import pandas as pd
from analytics import scorecard
import plotly.graph_objects as go
import streamlit as st
import plotly.express as px

def sql_result_chart(result):
    """Chart only returned values, with explicit aggregation choices."""
    st.subheader('Query result chart')
    if result.empty:
        st.info('The query returned no rows, so there is nothing to chart.')
        return
    data=result.copy()
    # Distinguish duplicate SQL output names for chart selection only.
    seen={}; names=[]
    for original in data.columns:
        name=str(original);seen[name]=seen.get(name,0)+1
        names.append(name if seen[name]==1 else f'{name} ({seen[name]})')
    data.columns=names
    numeric=data.select_dtypes(include='number').columns.tolist()
    dates=[]
    for col in data:
        if any(token in col.lower() for token in ['date','month','day']) and col not in numeric:
            parsed=pd.to_datetime(data[col],errors='coerce')
            if parsed.notna().all():data[col]=parsed;dates.append(col)
    categories=[c for c in data if c not in numeric and c not in dates]
    if not numeric:
        st.caption('No numeric measure was returned. This chart shows counts of returned rows by category.')
        col=st.selectbox('Count rows by',names,key='sql_count_col')
        freq=data[col].fillna('(missing)').astype(str).value_counts().rename_axis(col).reset_index(name='Returned rows')
        fig=px.bar(freq.head(50),x=col,y='Returned rows',text='Returned rows')
        if len(freq)>50:st.caption('Showing the 50 most frequent categories.')
    else:
        default_x=dates[0] if dates else categories[0] if categories else 'Row number'
        c1,c2,c3=st.columns(3)
        kind=c1.selectbox('Chart type',['Bar','Line','Scatter'],index=1 if dates else 0,key='sql_chart_type')
        x=c2.selectbox('X axis',['Row number']+names,index=names.index(default_x)+1 if default_x in names else 0,key='sql_x')
        ys=c3.multiselect('Values (Y)',numeric,default=[numeric[0]],key='sql_y')
        if not ys:st.info('Select at least one numeric value.');return
        groups=['None']+[c for c in categories if c!=x]
        group_default=next((i for i,c in enumerate(groups) if c in ['stock','stock_name'] and x in dates),0)
        grouping=st.selectbox('Group series by',groups,index=group_default,key='sql_group')
        if x=='Row number':data[x]=range(1,len(data)+1)
        ids=list(dict.fromkeys([x]+([grouping] if grouping!='None' else [])))
        if x in ys:
            st.info('Choose different columns for X and Y, or use Row number on X.');return
        agg=st.selectbox('For repeated X values',['Keep returned rows','Mean','Sum'],key='sql_agg')
        if agg!='Keep returned rows':data=data.groupby(ids,dropna=False)[ys].agg(agg.lower()).reset_index()
        data=data.head(2000)
        st.caption(f'Plotting up to 2,000 returned rows. Aggregation: {agg.lower()}. Use SQL ORDER BY / GROUP BY to control the result.')
        if kind=='Line' and data.duplicated(ids).any():
            st.info('Repeated X values exist within a series. Choose a grouping column, Mean/Sum, or Scatter for an unambiguous chart.');return
        long=data[ids+ys].melt(id_vars=ids,value_vars=ys,var_name='Measure',value_name='Value')
        if grouping!='None':long['Series']=long[grouping].astype(str)+' · '+long.Measure
        else:long['Series']=long.Measure
        long=long.dropna(subset=['Value'])
        if long.empty:st.info('Selected numeric columns contain no nonmissing values.');return
        if kind=='Line':
            long=long.sort_values(x)
            fig=px.line(long,x=x,y='Value',color='Series',markers=True)
        elif kind=='Scatter':fig=px.scatter(long,x=x,y='Value',color='Series')
        else:
            fig=px.bar(long,x=x,y='Value',color='Series',barmode='group',text_auto='.3~s')
        if len(ys)>1:st.caption('All selected measures share one Y axis. Compare measures with compatible units.')
    fig.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',height=420,margin=dict(l=25,r=25,t=30,b=35))
    st.plotly_chart(fig,width='stretch')

GREEN='#22c55e'
RED='#ef4444'

def card(container,label,value,detail='',series=None,positive=None):
    color=GREEN if positive is True else RED if positive is False else '#75a7ff'
    spark=''
    if series is not None:
        values=np.asarray(series,dtype=float)
        values=values[np.isfinite(values)]
        if len(values)>1:
            values=values[np.linspace(0,len(values)-1,min(100,len(values))).astype(int)]
            xx=np.linspace(0,300,len(values)); yy=52-44*(values-values.min())/(np.ptp(values) or 1)
            pts=' '.join(f'{x:.1f},{y:.1f}' for x,y in zip(xx,yy))
            spark=f'<svg viewBox="0 0 300 60" role="img" aria-label="Selected period trend"><polyline class="spark" points="{pts}" fill="none" stroke="{color}" stroke-width="2.5" pathLength="1"/></svg>'
    arrow='▲' if positive is True else '▼' if positive is False else ''
    container.markdown(f'<div class="motion-card" style="--accent:{color}"><div class="card-copy"><div class="card-label">{escape(str(label))}</div><div class="card-value"><span class="card-arrow">{arrow}</span>{escape(str(value))}</div><div class="card-detail">{escape(str(detail))}</div></div><div class="card-spark">{spark}</div></div>',unsafe_allow_html=True)

def black_table(data,hide_index=False,**kwargs):
    """Escaped, scrollable black table with actual values retained in downloads."""
    table=data.to_html(index=not hide_index,escape=True,border=0,classes='black-table',
                       na_rep='—',float_format=lambda x:f'{x:,.2f}')
    st.markdown('<div class="black-table-wrap">'+table+'</div>',unsafe_allow_html=True)

def growth_bars(summary):
    s=summary.sort_values('growth_pct')
    limit=max(float(s.growth_pct.abs().max())*1.35,1)
    f=go.Figure(go.Bar(x=s.growth_pct,y=s.stock,orientation='h',
        marker_color=[GREEN if n>=0 else RED for n in s.growth_pct],
        text=[f'{n:+.2f}%' for n in s.growth_pct],textposition='outside',cliponaxis=False,
        hovertemplate='%{y}<br>Period growth: %{x:+.2f}%<extra></extra>'))
    f.update_layout(title='Period growth / decline (%)',height=430,xaxis=dict(range=[-limit,limit],ticksuffix='%',zeroline=True,zerolinecolor='#acbad1',zerolinewidth=2))
    return f

def turnover_ring(summary,colors):
    s=summary.sort_values('turnover',ascending=False)
    f=go.Figure(go.Pie(labels=s.stock,values=s.turnover,hole=.76,sort=False,
        marker=dict(colors=colors,line=dict(color='#0a1020',width=4)),
        textinfo='percent',textposition='outside',pull=[.045]+[0]*(len(s)-1),
        hovertemplate='%{label}<br>₹%{value:,.0f}<br>%{percent}<extra></extra>'))
    f.update_layout(title='Turnover allocation',height=430,
        annotations=[dict(text=f'<b>₹{s.turnover.sum()/1e7:,.1f} Cr</b><br>Total turnover',x=.5,y=.5,showarrow=False,font=dict(size=17))],
        legend=dict(orientation='h',y=-.12,x=.5,xanchor='center'))
    return f

def pnl_radar(trades):
    names=trades.stock.tolist()
    f=go.Figure()
    for label,values,color,fill in [
        ('Profit (₹)',trades.pnl.clip(lower=0),GREEN,'rgba(34,197,94,.22)'),
        ('Loss magnitude (₹)',-trades.pnl.clip(upper=0),RED,'rgba(239,68,68,.18)')]:
        vals=values.tolist()
        f.add_trace(go.Scatterpolar(theta=names+[names[0]],r=vals+[vals[0]],
             name=label,fill='toself',mode='lines+markers',line=dict(color=color,width=3),fillcolor=fill,
             customdata=trades.pnl.tolist()+[float(trades.pnl.iloc[0])],
             hovertemplate='%{theta}<br>Net P&L: ₹%{customdata:,.2f}<extra></extra>'))
    f.update_layout(title='Net profit & loss · stock comparison',height=550,
        polar=dict(bgcolor='rgba(0,0,0,0)',radialaxis=dict(range=[0,max(1,float(trades.pnl.abs().max())*1.15)],tickprefix='₹',gridcolor='#293953'),
                   angularaxis=dict(gridcolor='#293953')),legend=dict(orientation='h'))
    return f


def render_comparison(selected,full,stocks,colors):
    st.subheader('Stock comparison scorecard')
    st.caption('Uses the sidebar analysis period and price basis. Radar scores are relative magnitudes, not investment ratings; actual values are in the black table.')
    chosen=st.multiselect('Compare up to 4 stocks',stocks,default=stocks[:4],max_selections=4,key='radar_compare')
    if not chosen:
        st.info('Choose at least one stock to view its scorecard.');return
    values=scorecard(selected[selected.stock.isin(chosen)],full).reindex(chosen)
    scores=values.copy();scores['Max drawdown %']=scores['Max drawdown %'].abs()
    for col in scores:
        lo=scores[col].min();hi=scores[col].max()
        scores[col]=100*(scores[col]-lo)/(hi-lo) if hi>lo else scores[col].where(scores[col].isna(),50)
    labels=['Return','CAGR','Volatility','Drawdown magnitude','Sharpe','RSI']
    fig=go.Figure()
    for i,stock in enumerate(chosen):
        points=[None if pd.isna(x) else float(x) for x in scores.loc[stock]]
        fig.add_trace(go.Scatterpolar(r=points+[points[0]],theta=labels+[labels[0]],name=stock,
            mode='lines+markers',fill='toself',opacity=.65,line=dict(color=colors[i%len(colors)],width=2),
            hovertemplate='%{theta}<br>Relative magnitude: %{r:.1f}/100<extra>%{fullData.name}</extra>'))
    fig.update_layout(template='plotly_dark',height=430,margin=dict(l=65,r=65,t=40,b=60),
        paper_bgcolor='rgba(0,0,0,0)',polar=dict(bgcolor='rgba(0,0,0,0)',radialaxis=dict(range=[0,100],gridcolor='#293953')),
        legend=dict(orientation='h',y=-.15,font=dict(size=11)))
    left,right=st.columns([1,1.2])
    with left:st.plotly_chart(fig,width='stretch')
    with right:black_table(values.T.round(2))
    st.download_button('Download scorecard (CSV)',values.to_csv(),'stock_scorecard.csv','text/csv')

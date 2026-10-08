# 1. how many trading days does bajaj auto contain, and what are its earliest and latest dates?
select count(*) 'trading days', 
       min(str_to_date(date,'%d-%m-%y')) as 'earliest date' , 
       max(str_to_date(date,'%d-%m-%y')) as 'latest date' from bajaj;

# 2. what are eicher motors’ five highest closing prices, and on which dates did they occur? 
select str_to_date(`date`, '%d-%m-%y') as trade_date,
       `close price` as 'top 5 closing price' 
from eicher order by 2 desc limit 5;

# 3. what was tcs’s average closing price in each year, rounded to two decimals?
select year(str_to_date(date, '%d-%m-%y')) as years ,
       round(avg(`close price`),2) as 'closing price' 
from tcs group by 1;

# 4. which dates have missing deliverable quantities across the six stocks? do the missing dates overlap?
select b.date as dates,
    b.`deliverable quantity` as bajaj_del_qnt,
    h.`deliverable quantity` as hero_del_qnt,
    e.`deliverable quantity` as eicher_del_qnt,
    i.`deliverable quantity` as infosys_del_qnt,
    t.`deliverable quantity` as tcs_del_qnt,
    tv.`deliverable quantity` as tvs_del_qnt
from bajaj b
join hero h   on b.date = h.date
join eicher e on h.date = e.date
join infosys i on e.date = i.date
join tcs t    on i.date = t.date
join tvs tv   on t.date = tv.date
where b.`deliverable quantity` is null
  or h.`deliverable quantity` is null
  or e.`deliverable quantity` is null
  or i.`deliverable quantity` is null
  or t.`deliverable quantity` is null
  or tv.`deliverable quantity` is null;

# 5. how can you calculate bajaj auto’s 20-day and 50-day moving averages, leaving incomplete windows as null?
select str_to_date(date, '%d-%m-%y') as trade_date,
       `close price`,
	   round(avg(`close price`) over (order by str_to_date(date, '%d-%m-%y')
            rows between 19 preceding and current row), 2) as ma20,
	   round(avg(`close price`) over (order by str_to_date(date, '%d-%m-%y')
            rows between 49 preceding and current row), 2) as ma50       
from bajaj;  

# 6. how can you create a master table containing all six closing prices on each trading date?
create view stock_master as
select 
    b.date as 'trade date',
    b.`close price` as 'bajaj close',
    h.`close price` as 'hero close',
    e.`close price` as 'eicher close',
    i.`close price` as 'infosys close',
    t.`close price` as 'tcs close',
    tv.`close price` as 'tvs close'
from bajaj b
join hero h   on b.date = h.date
join eicher e on h.date = e.date
join infosys i on e.date = i.date
join tcs t    on i.date = t.date
join tvs tv   on t.date = tv.date;
select * from stock_master;

# 7. on which dates does bajaj’s ma20 cross above or below ma50? assign buy, sell, or hold.
 create view sig as
 select trade_date,
    `close price`,
    ma20,
    ma50,
    case when ma20 > ma50 
             and lag(ma20) over (order by trade_date) <= lag(ma50) over (order by trade_date) then 'buy'
         when ma20 < ma50 
             and lag(ma20) over (order by trade_date) >= lag(ma50) over (order by trade_date) then 'sell' 
	     else 'hold' end as signals
from moving_avg order by trade_date;

# 8. how many buy, sell, and hold signals did bajaj generate?
select signals, 
       count(*) signals_count 
from sig group by 1 order by 2 desc;

# 9. how can you create a mysql function that returns bajaj’s signal for a supplied date, including 2018-06-21?
delimiter $$

create function get_bajaj_signal(p_date date)
returns varchar(10)
deterministic
begin
    declare v_signal varchar(10);

    select signals
    into v_signal
    from sig
    where trade_date = p_date
    limit 1;

    return v_signal;
end$$

delimiter ;
select get_bajaj_signal('2018-06-21') as bajaj_signal;

# 10. for each stock, how many buy and sell signals occurred, and what was the latest non-hold signal and its date? count buy/sell signals per stock
with signals_union as (
    select 'bajaj'   as stock_name, trade_date, signals from bajaj_sig
    union all
    select 'hero'    as stock_name, trade_date, signals from hero_sig
    union all
    select 'eicher'  as stock_name, trade_date, signals from eicher_sig
    union all
    select 'infosys' as stock_name, trade_date, signals from infosys_sig
    union all
    select 'tcs'     as stock_name, trade_date, signals from tcs_sig
    union all
    select 'tvs'     as stock_name, trade_date, signals from tvs_sig),
counts as (
    select stock_name,
           sum(signals = 'buy')  as buy_count,
           sum(signals = 'sell') as sell_count
    from signals_union group by stock_name),
latest as (
    select stock_name,
           signals as latest_signal,
           trade_date as latest_signal_date
    from signals_union s where signals <> 'hold'
      and trade_date = (
          select max(trade_date)
          from signals_union where stock_name = s.stock_name and signals <> 'hold'))
select 
    c.stock_name,
    c.buy_count,
    c.sell_count,
    l.latest_signal,
    l.latest_signal_date
from counts c
join latest l on c.stock_name = l.stock_name
order by c.stock_name;

# 11. what was each stock’s percentage price change between the first and last trading dates?
with stock_changes as (
    select 'bajaj' as stock_name,
        round(((max(`close price`) - min(`close price`)) * 100.0 / min(`close price`)), 2) as pct_change from bajaj
    union all
    select 'hero', round(((max(`close price`) - min(`close price`)) * 100.0 / min(`close price`)), 2) from hero
    union all
    select 'eicher', round(((max(`close price`) - min(`close price`)) * 100.0 / min(`close price`)), 2) from eicher
    union all
    select 'infosys', round(((max(`close price`) - min(`close price`)) * 100.0 / min(`close price`)), 2) from infosys
    union all
    select 'tcs', round(((max(`close price`) - min(`close price`)) * 100.0 / min(`close price`)), 2) from tcs
    union all
    select 'tvs', round(((max(`close price`) - min(`close price`)) * 100.0 / min(`close price`)), 2) from tvs)
select * from stock_changes;

# 12. what was each stock’s worst daily percentage change, and which unusual drops need investigation for corporate actions?
with worst_stock as (
    select 'bajaj' as stock_name, str_to_date(date, '%d-%m-%y') as trade_date,
        round(((`close price` - lag(`close price`)over(order by str_to_date(date, '%d-%m-%y')))
        *100/lag(`close price`)over(order by str_to_date(date, '%d-%m-%y'))),2) as daily_pct_change
    from bajaj
    union all
    select 'hero'as stock_name, str_to_date(date, '%d-%m-%y') as trade_date,
        round(((`close price` - lag(`close price`)over(order by str_to_date(date, '%d-%m-%y')))
        *100/lag(`close price`)over(order by str_to_date(date, '%d-%m-%y'))),2)
    from hero
    union all
    select 'eicher'as stock_name, str_to_date(date, '%d-%m-%y') as trade_date,
        round(((`close price` - lag(`close price`)over(order by str_to_date(date, '%d-%m-%y')))
        *100/lag(`close price`)over(order by str_to_date(date, '%d-%m-%y'))),2)
    from eicher
    union all
    select 'infosys' as stock_name, str_to_date(date, '%d-%m-%y') as trade_date,
        round(((`close price` - lag(`close price`)over(order by str_to_date(date, '%d-%m-%y')))
        *100/lag(`close price`)over(order by str_to_date(date, '%d-%m-%y'))),2)
    from infosys
    union all
    select 'tcs' as stock_name, str_to_date(date, '%d-%m-%y') as trade_date,
        round(((`close price` - lag(`close price`)over(order by str_to_date(date, '%d-%m-%y')))
        *100/lag(`close price`)over(order by str_to_date(date, '%d-%m-%y'))),2)
    from tcs
    union all
    select 'tvs' as stock_name, str_to_date(date, '%d-%m-%y') as trade_date,
        round(((`close price` - lag(`close price`)over(order by str_to_date(date, '%d-%m-%y')))
        *100/lag(`close price`)over(order by str_to_date(date, '%d-%m-%y'))),2)
    from tvs)
select stock_name, trade_date, daily_pct_change from (
select stock_name, trade_date, daily_pct_change,
       row_number() over(partition by stock_name order by daily_pct_change asc)as rn from worst_stock
       where daily_pct_change is not null) t where rn=1 order by daily_pct_change asc;

# 13. after applying the guide’s corporate-action adjustments to tcs and infosys, how do their full-period price changes differ from the raw results?
with prices as (
    select
        'tcs' as stock_name,
        str_to_date(`date`, '%d-%m-%y') as trade_date,
        `close price` as close_price
    from tcs
    union all
    select
        'infosys',
        str_to_date(`date`, '%d-%m-%y'),
        `close price`
    from infosys
),
adjusted as (
    select
        stock_name,
        trade_date,
        close_price,
        case
            when stock_name = 'tcs'
                 and trade_date < '2018-05-31'
                then close_price / 2.0

            when stock_name = 'infosys'
                 and trade_date < '2015-06-15'
                then close_price / 2.0

            else close_price
        end as adjusted_close
    from prices
),
endpoints as (
    select
        stock_name,

        max(case when trade_date = '2015-01-01'
                 then close_price end) as first_close,

        max(case when trade_date = '2018-07-31'
                 then close_price end) as last_close,

        max(case when trade_date = '2015-01-01'
                 then adjusted_close end) as first_adjusted_close,

        max(case when trade_date = '2018-07-31'
                 then adjusted_close end) as last_adjusted_close

    from adjusted
    group by stock_name),
changes as (
    select
        stock_name,
        100.0 * (
            last_close / nullif(first_close, 0) - 1) as raw_pct_change,
        100.0 * (
            last_adjusted_close
            / nullif(first_adjusted_close, 0) - 1) as adjusted_pct_change
    from endpoints)
select
    stock_name,
    round(raw_pct_change, 2) as raw_pct_change,
    round(adjusted_pct_change, 2) as adjusted_pct_change,
    round(
        adjusted_pct_change - raw_pct_change, 2) as difference_percentage_points
from changes
order by stock_name;

# 14. are there missing or nonpositive prices, negative trading volumes, or closing prices outside the daily low–high range?
with someis as (
    select 'bajaj' as stock_name, date, `open price`, `high price`, `low price`, `close price` from bajaj
    union all
    select 'hero', date, `open price`, `high price`, `low price`, `close price` from hero
    union all
    select 'eicher', date, `open price`, `high price`, `low price`, `close price` from eicher
    union all
    select 'infosys', date, `open price`, `high price`, `low price`, `close price`from infosys
    union all
    select 'tcs', date, `open price`, `high price`, `low price`, `close price` from tcs
    union all
    select 'tvs', date, `open price`, `high price`, `low price`, `close price` from tvs)
select stock_name, date, `close price`, `low price`, `high price`
from someis
where `close price` is null
   or `close price` <= 0
   or `close price` < `low price`
   or `close price` > `high price`;

# 15. which five dates had the highest trading turnover for each stock?
with someis as (
    select 'bajaj' as stock_name, date, `no. of trades` from bajaj
    union all
    select 'hero', date,`no. of trades` from hero
    union all
    select 'eicher', date, `no. of trades`from eicher
    union all
    select 'infosys', date, `no. of trades` from infosys
    union all
    select 'tcs', date, `no. of trades` from tcs
    union all
    select 'tvs', date, `no. of trades` from tvs)
select stock_name, date, `no. of trades`
from (select stock_name, date, `no. of trades`, row_number() over(partition by stock_name order by `no. of trades` desc) as rnk
from someis) t where rnk<=5 order by stock_name, `no. of trades` desc;

# 16. what was each stock’s monthly total turnover and average daily number of trades?
with someis as (
    select 'bajaj' as stock_name, monthname(str_to_date(date, '%d-%m-%y')) as month_name,
					              year(str_to_date(date, '%d-%m-%y')) as year_num,
								 `total turnover (rs.)`, `no. of trades` from bajaj
    union all
    select 'hero', monthname(str_to_date(date, '%d-%m-%y')) as month_name,
					              year(str_to_date(date, '%d-%m-%y')) as year_num,
								 `total turnover (rs.)`, `no. of trades` from hero
    union all
    select 'eicher', monthname(str_to_date(date, '%d-%m-%y')) as month_name,
					              year(str_to_date(date, '%d-%m-%y')) as year_num,
								 `total turnover (rs.)`, `no. of trades` from eicher
    union all
    select 'infosys', monthname(str_to_date(date, '%d-%m-%y')) as month_name,
					              year(str_to_date(date, '%d-%m-%y')) as year_num,
								 `total turnover (rs.)`, `no. of trades`
    from infosys
    union all
    select 'tcs', monthname(str_to_date(date, '%d-%m-%y')) as month_name,
					              year(str_to_date(date, '%d-%m-%y')) as year_num,
								 `total turnover (rs.)`, `no. of trades` from tcs
    union all
    select 'tvs', monthname(str_to_date(date, '%d-%m-%y')) as month_name,
					              year(str_to_date(date, '%d-%m-%y')) as year_num,
								 `total turnover (rs.)`, `no. of trades` from tvs)
select stock_name, 
       concat(year_num,'-',month_name) as year_months,
       sum(`total turnover (rs.)`) as monthly_total_turnover,
       round(avg(`no. of trades`),2) avg_daily_trades 
from someis group by stock_name, year_num, month_name order by stock_name, year_num, month_name;

# 17. on which dates did volume exceed twice the stock’s average volume over the previous 20 trading days?
with cte as (
 select 'bajaj' as stock_name, str_to_date(date,'%d-%m-%y') as trade_date,`no.of shares` as volume from bajaj
    union all
    select 'hero', str_to_date(date,'%d-%m-%y') ,`no.of shares` from hero
    union all
    select 'eicher', str_to_date(date,'%d-%m-%y'),`no.of shares` from eicher
    union all
    select 'infosys', str_to_date(date,'%d-%m-%y') ,`no.of shares` from infosys
    union all
    select 'tcs', str_to_date(date,'%d-%m-%y') ,`no.of shares` from tcs
    union all
    select 'tvs',str_to_date(date,'%d-%m-%y') ,`no.of shares` from tvs)
select stock_name,trade_date,volume,avg_vol_20 from (
select stock_name, trade_date, volume,
       round(avg(volume) over(partition by stock_name order by trade_date
       rows between 20 preceding and 1 preceding),2) as avg_vol_20 from cte) t
where avg_vol_20 is not null and volume >2* avg_vol_20    
order by 1,2; 

# 18. which stock had the highest average delivery percentage, excluding missing observations?
with cte as (
    select 'bajaj' as stock_name, round(avg(`% deli. qty to traded qty`),2) as avg_del_pct from bajaj
    union all
    select 'hero', round(avg(`% deli. qty to traded qty`),2) as avg_del_pct from hero
    union all
    select 'eicher', round(avg(`% deli. qty to traded qty`),2) as avg_del_pct from eicher
    union all
	select 'infosys', round(avg(`% deli. qty to traded qty`),2) as avg_del_pct from infosys
    union all
    select 'tcs', round(avg(`% deli. qty to traded qty`),2) as avg_del_pct from tcs
    union all
    select 'tvs', round(avg(`% deli. qty to traded qty`),2) as avg_del_pct from tvs)
select stock_name, avg_del_pct from cte order by 2 desc;

# 19. using adjusted prices, what were each stock’s best and worst monthly returns?
with monthly as (
    select 'bajaj' as stock_name,
           str_to_date(date, '%d-%m-%y') as trade_date,
           `close price` as adj_close from bajaj
    union all
    select 'hero', str_to_date(date, '%d-%m-%y'), `close price` from hero
    union all
    select 'eicher', str_to_date(date, '%d-%m-%y'), `close price` from eicher
    union all
    select 'infosys', str_to_date(date, '%d-%m-%y'), `close price` from infosys
    union all
    select 'tcs', str_to_date(date, '%d-%m-%y'), `close price` from tcs
    union all
    select 'tvs', str_to_date(date, '%d-%m-%y'), `close price` from tvs),
returns as (
    select stock_name,
           year(trade_date) as yr,
           monthname(trade_date) as mn,
           first_value(adj_close) over (
               partition by stock_name, year(trade_date), month(trade_date) order by trade_date) as first_price,
           last_value(adj_close) over (
               partition by stock_name, year(trade_date), month(trade_date) order by trade_date
               rows between unbounded preceding and unbounded following) as last_price from monthly)
select stock_name,
       round(max((last_price - first_price) * 100.0 / first_price), 2) as best_monthly_return,
       round(min((last_price - first_price) * 100.0 / first_price), 2) as worst_monthly_return
from returns group by stock_name order by best_monthly_return desc;

# 20. using adjusted daily returns, which stock had the highest standard deviation?
with prices as (
    select 'bajaj' as stock_name,
           str_to_date(date, '%d-%m-%y') as trade_date,
           `close price` as adj_close
    from bajaj
    union all
    select 'hero', str_to_date(date, '%d-%m-%y'), `close price` from hero
    union all
    select 'eicher', str_to_date(date, '%d-%m-%y'), `close price` from eicher
    union all
    select 'infosys', str_to_date(date, '%d-%m-%y'), `close price` from infosys
    union all
    select 'tcs', str_to_date(date, '%d-%m-%y'), `close price` from tcs
    union all
    select 'tvs', str_to_date(date, '%d-%m-%y'), `close price` from tvs),
returns as (
    select stock_name,
           trade_date,
           round(
             (adj_close - lag(adj_close) over (partition by stock_name order by trade_date))
             * 100.0 / lag(adj_close) over (partition by stock_name order by trade_date), 4) as daily_return
    from prices)
select stock_name,
       round(stddev_samp(daily_return), 2) as std_dev_returns
from returns
where daily_return is not null
group by stock_name order by std_dev_returns desc;

# 21. how often did a buy signal reverse into a sell within 10 trading days?
with signals as (
    select 'bajaj' as stock_name,
           trade_date,
           signals
    from bajaj_sig
    union all
    select 'hero', trade_date, signals from hero_sig
    union all
    select 'eicher', trade_date, signals from eicher_sig
    union all
    select 'infosys', trade_date, signals from infosys_sig
    union all
    select 'tcs', trade_date, signals from tcs_sig
    union all
    select 'tvs', trade_date, signals from tvs_sig)
select s1.stock_name,
       count(*) as buy_to_sell_reversals
from signals s1
join signals s2
  on s1.stock_name = s2.stock_name
 and s1.signals = 'buy'
 and s2.signals = 'sell'
 and s2.trade_date > s1.trade_date
 and s2.trade_date <= date_add(s1.trade_date, interval 10 day)
group by s1.stock_name order by buy_to_sell_reversals desc;

# 22. how many tcs signals change when moving averages are recalculated using adjusted prices?
with raw_signals as (
    select trade_date, signals
    from tcs_sig),  
adjusted as (
    select date as trade_date,
           `close price` as adj_close,
           round(avg(`close price`) over (
               order by date
               rows between 19 preceding and current row), 2) as ma20,
           round(avg(`close price`) over (
               order by date
               rows between 49 preceding and current row), 2) as ma50
    from tcs),
tcs_adj_sig as (
    select trade_date,
           case when ma20 > ma50 then 'buy'
                when ma20 < ma50 then 'sell'
                else 'hold' end as signals
    from adjusted)
select count(*) as changed_signals
from raw_signals r
join tcs_adj_sig a
  on r.trade_date = a.trade_date
where r.signals <> a.signals;
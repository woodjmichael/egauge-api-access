import datetime as dt
from pytz import timezone as tz
import requests
import pandas as pd

# Versions
# 1.0 - first stable

def fetch(device, interval, start, end, raw=False):
    """Get data from egauge api for stored data

    Args:

        device (int) :   egauge ID (see it's url)
        
        interval (str) : 'm' for minute, 'h' for hour (no seconds)
        
        start (str) :    datetime WITH timezone, ISO formatted (e.g. '2022-08-20 00:00-06:00')
        
        end (str) :      datetime WITH timezone, ISO formatted

        raw (bin) :      (Optional) True = dump raw data, False (default) = don't

    
    Returns:
    
        pandas.DataFrame full of your data

   """      

    timezone = int(start[16:19])
    if   timezone < 0:
        timezone = f'Etc/GMT+{abs(timezone)}' # this looks backwards but is right
    elif timezone > 0:
        timezone = f'Etc/GMT-{abs(timezone)}' # this looks backwards but is right        
    elif timezone == 0:
        timezone = f'Etc/GMT' # hope this works

    start = dt.datetime.fromisoformat(start)
    end = dt.datetime.fromisoformat(end)        
    df = pd.DataFrame()
    
    next = start # just get in the loop
    while next <= end:                     
        next = min(start + dt.timedelta(days=28), end)
        df_new = single_fetch(device, timezone, interval, start, next, raw)
        df = pd.concat((df,df_new))
        start = next
        if next >= end: 
            break                  
    
    return df
    

def single_fetch(device, timezone, interval, start, end, raw=False):
    """Single GET request to the egauge api for stored data given 
    a time period (max return rows about 40,000)

    Args:

        device (int) :   egauge ID (see it's url)
        
        timezone (str) : of the device (e.g. 'Etc/GMT+6')
        
        interval (str) : 'm' for minute, 'h' for hour (no seconds)
        
        start (dt obj) : datetime WITH timezone, ISO formatted (e.g. '2022-08-20 00:00-06:00')
        
        end (dt obj) :   datetime WITH timezone, ISO formatted

        raw (bin) :      (Optional) True = dump raw data, False (default) = don't

    
    Returns:
    
        pandas.DataFrame full of your data

   """
    
    # useful
    if   interval == 'm': interval_s = 60
    elif interval == 'h': interval_s = 3600

    # calculate inputs
    start_unix = int( dt.datetime.timestamp(start) ) - interval_s
    end_unix   = int( dt.datetime.timestamp(end)   )
    delta = end_unix - start_unix    
    n = int(delta / interval_s) # how many accumulator samples at given interval
    f = start_unix + interval_s * n        
    if n > 45000: 
        print(f'Single quests larger than 40000 rows often fail (n={n})')
    
    # info
    print('Get: ','Start',start,'- End',end,'(n =',n,')')

    # build url    
    options = { 'n':n, 'f':f }
    format = 'c' # csv    
    url = f'http://egauge{device}.egaug.es/5F049/cgi-bin/egauge-show?{format}&{interval}'
    for key in options:
        value = options[key]
        url = url + f'&{key}={value}'       

    # request data
    data = requests.get(url).text

    # buld df
    df = pd.DataFrame([x.split(',') for x in data.split('\r\n')[1:-1]], 
                    columns=[x.strip(' ').replace('"','').replace(' ','_') for x in data.split('\r\n')[0].split(',')])
    df = df.rename(columns={'Date_&_Time':'Unix time'})

    if raw: df.to_csv(f'egauge_raw_{device}_{interval}_{start_unix}_{end_unix}.csv')
    
    # fix timezone    
    df['Datetime'] = pd.to_datetime(df['Unix time'],unit='s')
    df = df.set_index('Datetime')
    df = df.tz_localize('UTC').tz_convert(timezone)   
    
    # get to kw
    df = df.apply(pd.to_numeric)
    df = df.sort_index()
    df['Load [kW]'] = df['Usage_[kWh]'].diff(-1) * 3600/interval_s * -1 # .diff(-1) * -1 for beginning of period convention
    df = df.dropna()
    df = df[['Load [kW]']]   
    
    return df       
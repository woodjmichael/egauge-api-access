import datetime as dt
from pytz import timezone as tz
import requests
import pandas as pd
from configparser import ConfigParser

# Versions
# 1.1 - add egauge number config file, small changes
# 1.0 - first stable

"""Relatively simple package for pulling stored egauge data

Usage:

import egauge_api_access as api

df = api.get_data(  site=           'bayfield_jail',
                    interval=       'h',
                    start=          '2022-08-19 00:00+01:00',
                    end=            '2022-08-20 00:00+01:00',
                    output_file=    True                        )  

# or

df = api.get_data(  device=         30304,
                    interval=       'h',
                    start=          '2022-08-19 00:00+01:00',
                    end=            '2022-08-20 00:00+01:00',
                    output_file=    True                        )  


""" 

def get_data(interval, start, end, device=None, site=None, raw=False, output_file=False):
    """Get data from egauge api for stored data

    Args:
        
        interval (str) : 'm' for minute, 'h' for hour (no seconds)
        
        start (str) :    datetime WITH timezone, ISO formatted (e.g. '2022-08-20 00:00-06:00')
        
        end (str) :      datetime WITH timezone, ISO formatted
        
        device (int) :   (Optional) egauge ID (see it's url)
        
        site (str) :     (Optional) customer and site name to lookup egauge number
        
        raw (bool) :     (Optional) True = dump raw data, False (default) = don't
        
        output_file(bool):  (Optional) True = save df to csv, False (default) = don't                

    
    Returns:
    
        pandas.DataFrame full of your data

   """    
   
    if site:
        device = lookup_egauge_number(site)
        print(site, device)

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
        df_new = single_api_call(device, timezone, interval, start, next, raw)
        df = pd.concat((df,df_new))
        start = next
        if next >= end: 
            break                  
    
    if output_file:
        dtnow = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        df.to_csv(f'egauge_{site}_{interval}_{dtnow}.csv')
    
    return df
    

def single_api_call(device, timezone, interval, start, end, raw=False):
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

def lookup_egauge_number(site):
    """Give a site name get an egauge ID from config.ini 

    Args:

        site (str)  :   customer and site separted by underscore (e.g. bayfield_courthouse)
    
    Returns:
    
        egauge ID as int

   """    
    config = ConfigParser()
    config.read('egauge_IDs.ini')    
    
    if site in config['DEFAULT']:
        return int(config['DEFAULT'][site])
    else:
        print('error: site not found in .ini file')
        quit()
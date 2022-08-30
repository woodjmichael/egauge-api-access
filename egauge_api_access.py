import datetime as dt
from pytz import timezone as tz
import requests
import pandas as pd
from configparser import ConfigParser

# Versions
# 1.3 - custom column name (for bad river wwtp)
# 1.2 - output file name
# 1.1 - add egauge number config file, small changes
# 1.0 - first stable

"""Relatively simple package for pulling stored egauge data (py v3.9)

Usage:

    import egauge_api_access as api

    df = api.get_data(  site=           'badriver_clinic',
                        interval=       'h',
                        start=          '2022-08-19 00:00+01:00', # egauge timezone
                        end=            '2022-08-20 00:00+01:00', # exclusive
                        feature=        'Load', # or 'Solar'
                        output_file=    True                        ) 

    # or

    df = api.get_data(  device=         53489,
                        interval=       'h',
                        start=          '2022-08-19 00:00+01:00', # egauge timezone
                        end=            '2022-08-20 00:00+01:00', # exclusive
                        feature=        'Load', # or 'Solar'
                        output_file=    True                        ) 

    print(df) # beginning of period convention  


""" 

def get_data(interval, start, end, feature='Load', device=None, site=None, raw=False, output_file=False):
    """Get data from egauge api for stored data

    Args:
        
        interval (str) : 'm' for minute, 'h' for hour (no seconds)
        
        start (str) :    datetime w/ egauge timezone, ISO formatted (e.g. '2022-08-20 00:00-06:00')
        
        end (str) :      datetime w/ egauge timezone, ISO formatted
        
        feature(str):   (Optional)  'Load' (default) gets you Usage_[kWh] as Load kW
                                    'Solar' gets Generation_[kWh] as Solar kW
                                    Or any other valid column, as itself
        
        device (int) :   (Optional) egauge ID (see it's url)
        
        site (str) :     (Optional) customer and site name to lookup egauge number
        
        raw (bool) :     (Optional) True = dump raw data, False (default) = don't
        
        output_file(bool):  (Optional) True = save df to csv, False (default) = don't


    
    Returns:
    
        pandas.DataFrame full of your data

   """    
   
    if site:
        device = lookup_egauge_number(site)
        print('')
        print(site, device, feature)

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
        df_new = single_api_call(device, timezone, interval, start, next, raw, feature)
        df = pd.concat((df,df_new))
        start = next
        if next >= end: 
            break                  
    
    if output_file:
        dtnow = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if site:
            df.to_csv(f'egauge_{site}_{interval}_{dtnow}.csv')
        elif device:
            df.to_csv(f'egauge_{device}_{interval}_{dtnow}.csv')
    
    return df
    

def single_api_call(device, timezone, interval, start, end, raw, feature):
    """Single GET request to the egauge api for stored data given 
    a time period (max return rows about 40,000)

    Args:

        device (int) :   egauge ID (see it's url)
        
        timezone (str) : of the device (e.g. 'Etc/GMT+6')
        
        interval (str) : 'm' for minute, 'h' for hour (no seconds)
        
        start (dt obj) : datetime WITH timezone, ISO formatted (e.g. '2022-08-20 00:00-06:00')
        
        end (dt obj) :   datetime WITH timezone, ISO formatted

        raw (bin) :      (Optional) True = dump raw data, False (default) = don't
        
        feature(str):   (Optional)  'Load' (default) gets you Usage_[kWh] as Load kW
                                    'Solar' gets Generation_[kWh] as Solar kW
                                    Or any other valid column, as itself

    
    Returns:
    
        pandas.DataFrame full of your data

   """
   
    # what columns to get
    if feature == 'Load':
        col_name = 'Usage_[kWh]'
    elif feature == 'Solar':     
        col_name = 'Generation_[kWh]'
    else:
        print(f'\nCustom column selected: {feature}')
        col_name = feature
    
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
        print(f'Single api calls larger than 40000 rows often fail (n={n})')
    
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
    response = requests.get(url) 
    if response:
        data = response.text
    else:
        print(f'\nHTTP error code: {response.status_code} ')
        quit()

    # build df
    df = pd.DataFrame([x.split(',') for x in data.split('\r\n')[1:-1]], 
                    columns=[x.strip(' ').replace('"','').replace(' ','_') for x in data.split('\r\n')[0].split(',')])
    df = df.rename(columns={'Date_&_Time':'Unix time'})

    if raw:
        df.to_csv(f'egauge_raw_{device}_{interval}_{start_unix}_{end_unix}.csv')
    
    # fix timezone    
    df['Datetime'] = pd.to_datetime(df['Unix time'],unit='s')
    df = df.set_index('Datetime')
    df = df.tz_localize('UTC').tz_convert(timezone)   
    
    # unaccumulate
    df = df.apply(pd.to_numeric)
    df = df.sort_index()        
    if feature=='Load' or feature =='Solar':
        # convert to average (not kWH, Vh, Ah, etc)
        feature = feature + ' kW'
        df[feature] = df[col_name].diff(-1) * 3600/interval_s * -1 # .diff(-1) * -1 for beginning of period convention
    else:
        df[feature] = df[col_name].diff(-1) * -1 # .diff(-1) * -1 for beginning of period convention        
    df = df.dropna()   
    
    return df[[feature]]

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
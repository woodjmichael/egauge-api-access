# eGauge API Access
_MJW 2022-8-26_

- Python v3.9
- The other egauge API codes were confusing and didn't really work for me
- Note this does not work for second-resolution data
- Egauge energy (produced or consumed) is saved every 1 sec as an accumulator value
- Therefore if you give interval 'm' then this code:
    1. Pulls the acumulator value for every 1 minute interval
    2. Calculates and returns the average power in kW over that 1 minute interval
- eGauge accumulator values are stored like this (as of gen 4):
  - 1 second interval values for 1 hour
  - 1 minute interval values for 1 year
  - 15 minute interval values for 10 years
  - 1 day interval values for the device lifetime
- So if you ask for 2 years of 1 minute values.. you're going to get something weird and it may break this code
- The timezone accuracy has been confirmed, no matter from what timezone you're making the API request
- "end" datetime is exclusive.. the data just before that datetime will be included, but not that datetime
  - e.g. `start='2021-01-01 00:00-5:00'` and `end='2022-01-01 00:00-5:00'` gets exactly 1 year of data
- Dat is returned with beginning of period convention
  - e.g. `2021-01-01 00:00-5:00` and `interval='h'` gives you the average power for that datetime and the _next_ 1 hour
- The code here or API doesn't know where the egauge is _at_ the site, or how its configured
  - e.g. you might get "Load" but that could be what the grid sees, not the gross load

# Usage

```python
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
```

# Troubleshooting

- start and end must be in iso format WITH timezone and padded zeros
- timezone should be standard time
- may need to install dependencies
- API doesn't like to return more than ~40,000 rows (n), probably this depends on how many columns there are
- try just a single_fetch()
- could be the hex code in the url needs to change sometime?
- try h instead of m, or a shorter duration (long ones take time and may break something)
- try whatever you're doing again (sometimes api doesn't respond)
- make sure you're not asking for data that doesn't exist (e.g. 1 min values from longer than 1 year ago)
- if you get an HTTP error code 404 or anything else 4xx or 5xx check:
  - if device is online (go to url)
  - if the device ID is correct (or site is right according to the config file)


# To Do

1. Gracefully fail if user asks for data that doesn't exist (e.g. 1 min values form longer than 1 year ago)
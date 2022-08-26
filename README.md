# eGauge API Access
_MJW 2022-8-26_

- The other egauge APIs were confusing and didn't really work for me
- Note this does not work for second-resolution data

# Usage

```python
import egauge_api_access as api

device = 55303 # bayfield courthouse 
interval = 'h' # m = minutes, h = hours (no seconds)
start = '2022-08-19 00:00-06:00'   # inclusive, iso format
end   = '2022-08-20 00:00-06:00'   # exclusive, iso format

df = api.fetch(device,interval,start,end)

df.to_csv(f'egauge_{device}_{interval}_{start[:10]}_{end[:10]}.csv')  
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
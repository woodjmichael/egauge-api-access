import egauge_api_access as api

device = 55303 # courthouse = 55303, jail = 30304

interval = 'h' # m = minutes, h = hours (no seconds)
start = '2022-08-19 00:00+01:00'   # inclusive, iso format
end   = '2022-08-20 00:00+01:00'   # exclusive, iso format

df = api.fetch(device,interval,start,end)

df.to_csv(f'egauge_{device}_{interval}_{start[:10]}_{end[:10]}.csv')  

print(df)
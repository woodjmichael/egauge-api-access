import egauge_api_access as api

df = api.get_data(  site=           'bailey_greenhouse',
                    interval=       'h',
                    start=          '2022-08-19 00:00+01:00', # time zone of egauge
                    end=            '2022-08-20 00:00+01:00', # exclusive
                    feature=        'Load', # or 'Solar'
                    output_file=    True                        )  

print(df)
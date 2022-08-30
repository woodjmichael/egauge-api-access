import egauge_api_access as api

df = api.get_data(  site=           'bayfield_jail',
                    interval=       'h',
                    start=          '2022-08-19 00:00+01:00',
                    end=            '2022-08-20 00:00+01:00',
                    output_file=    True                        )  

print(df)
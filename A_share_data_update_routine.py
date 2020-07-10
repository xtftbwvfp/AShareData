import datetime as dt
import json
import logging

from AShareData import constants, MySQLInterface, prepare_engine, TushareData, WindData

logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)

if __name__ == '__main__':
    config_loc = './tests/config.json'
    with open(config_loc, 'r') as f:
        config = json.load(f)

    tushare_token = config['tushare_token']
    engine = prepare_engine(config_loc)
    db_interface = MySQLInterface(engine)

    # downloader = TushareData(tushare_token, db_interface=db_interface, init=True)
    # downloader = TushareData(tushare_token, db_interface=db_interface, init=False)
    # downloader.update_routine()

    # update industry
    # needed_update_provider = []
    # for provider in constants.INDUSTRY_DATA_PROVIDER:
    #     timestamp = db_interface.get_latest_timestamp(f'{provider}行业')
    #     if timestamp < dt.datetime.now() - dt.timedelta(days=30):
    #         needed_update_provider.append(provider)
    #
    wind_data = WindData(db_interface)
    # if needed_update_provider:
    #     for provider in needed_update_provider:
    #         wind_data.update_industry(provider)
    #
    # wind_data.update_minutes_data()
    # wind_data.update_stock_daily_data()
    wind_data.update_routine()

import logging
from typing import Sequence, List, Callable

import pandas as pd
import sqlalchemy as sa

from utils import DateType, select_dates


class SQLDBReader(object):
    def __init__(self, engine: sa.engine.Engine) -> None:
        """
        SQL Database Reader

        :param engine: sqlalchemy engine
        """
        self.engine = engine

        calendar_df = pd.read_sql_table('交易日历', self.engine)
        self._calendar = calendar_df['交易日期'].dt.to_pydatetime().tolist()
        stock_list_df = pd.read_sql_table('股票列表', self.engine)
        self._stock_list = stock_list_df['证券代码'].values.tolist()

    def get_factor(self, table_name: str, factor_name: str, ffill: bool = False,
                   start_date: DateType = '2008-01-01', end_date: DateType = None,
                   stock_list: Sequence[str] = None) -> pd.DataFrame:
        primary_keys = self._check_args_and_get_primary_keys(table_name, factor_name)

        query_columns = primary_keys + [factor_name]
        logging.debug('开始读取数据.')
        # todo: this takes way too long for a large db
        series = pd.read_sql_table(table_name, self.engine, index_col=primary_keys, columns=query_columns)
        logging.debug('数据读取完成.')
        series.sort_index()
        df = series.unstack().droplevel(None, axis=1)
        if ffill:
            df.ffill(inplace=True)
        df = self._conform_df(df, start_date, end_date, stock_list)
        # name may not survive pickling
        df.name = factor_name
        return df

    def get_financial_factor(self, table_name: str, factor_name: str, agg_func: Callable,
                             start_date: DateType = None, end_date: DateType = None,
                             stock_list: Sequence[str] = None, yearly: bool = True) -> pd.DataFrame:
        primary_keys = self._check_args_and_get_primary_keys(table_name, factor_name)
        query_columns = primary_keys + [factor_name]

        data = pd.read_sql_table(table_name, self.engine, columns=query_columns)
        if yearly:
            data = data.loc[lambda x: x['报告期'].dt.month == 12, :]

        storage = []
        all_secs = set(data.ID.unique().tolist())
        if stock_list:
            all_secs = all_secs & set(stock_list)
        for sec_id in all_secs:
            id_data = data.loc[data.ID == sec_id, :]
            dates = id_data.DateTime.dt.to_pydatetime().tolist()
            dates = sorted(list(set(dates)))
            for date in dates:
                date_id_data = id_data.loc[data.DateTime <= date, :]
                each_date_data = date_id_data.groupby('报告期', as_index=False).last()
                each_date_data.set_index(['DateTime', 'ID', '报告期'], inplace=True)
                output_data = each_date_data.apply({factor_name: agg_func})
                output_data.index = pd.MultiIndex.from_tuples([(date, sec_id)], names=['DateTime', 'ID'])
                storage.append(output_data)

        df = pd.concat(storage)
        df = df.unstack().droplevel(None, axis=1)
        df = self._conform_df(df, start_date, end_date, stock_list)
        # name may not survive pickling
        df.name = factor_name
        return df

    # helper functions
    def _check_args_and_get_primary_keys(self, table_name: str, factor_name: str) -> List[str]:
        meta = sa.MetaData(bind=self.engine)
        meta.reflect()

        assert table_name.lower() in meta.tables.keys(), f'数据库中不存在表 {table_name}'

        columns = [it.name for it in meta.tables[table_name].c]
        assert factor_name in columns, f'表 {table_name} 中不存在 {factor_name} 列'

        primary_keys = [it for it in ['DateTime', 'ID', '报告期'] if it in columns]
        return primary_keys

    def _conform_df(self, df, start_date: DateType = None, end_date: DateType = None,
                    stock_list: Sequence[str] = None) -> pd.DataFrame:
        date_list = select_dates(self._calendar, start_date, end_date)
        df = df.reindex(date_list[:-1])

        if not stock_list:
            stock_list = self._stock_list
        df = df.reindex(stock_list, axis=1)
        return df

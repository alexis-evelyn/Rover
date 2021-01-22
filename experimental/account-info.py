#!/bin/python3
import json
import logging
import pandas as pd

from typing import List
from doltpy.core import Dolt, DoltException, system_helpers
from doltpy.etl import get_df_table_writer


def format_account_ids() -> pd.DataFrame:
    accounts_path: str = "working/presidential-tweets/handles.csv"
    accounts: pd.DataFrame = pd.read_csv(accounts_path)

    return accounts


accounts: pd.DataFrame = format_account_ids()

handles: str = ""
count: int = 1
for handle in accounts["twitter_user_id"].unique():
    # if count > 100:
    #     break
    count += 1

    if count <= 100:
        continue

    handles += str(handle) + ","
handles = handles[:-1]

print(handles)

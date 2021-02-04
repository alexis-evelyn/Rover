#!/usr/bin/python

import pandas as pd

matches_file: str = "working/wayback-matches.csv"
matches_file_clean: str = "working/wayback-matches-clean.csv"

matches: pd.DataFrame = pd.read_csv(matches_file, index_col=["id"])
matches = matches.groupby(matches.index).first()

print(matches)
matches.to_csv(matches_file_clean)

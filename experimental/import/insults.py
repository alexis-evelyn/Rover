#!/bin/python3
# DELETE ME LATER

import os
import pandas as pd


WORKING_DIRECTORY: str = "working/insults"
INSULTS_CSV: str = os.path.join(WORKING_DIRECTORY, "tweets-full.csv")
ALL_TWEETS_CSV: str = os.path.join(WORKING_DIRECTORY, "tweets.csv")
OUTPUT_CSV: str = os.path.join(WORKING_DIRECTORY, "tweets-missing.csv")

INSULTS: pd.DataFrame = pd.read_csv(INSULTS_CSV, usecols=['text'])
TWEETS: pd.DataFrame = pd.read_csv(ALL_TWEETS_CSV, usecols=['text'])

# Drop Exact Matches
MISSING = INSULTS[~INSULTS["text"].isin(TWEETS["text"])].dropna()

# Copy Original Text
MISSING['original'] = MISSING['text']
TWEETS['original'] = TWEETS['text']

# Replace Handles
replace_handles_regex: str = "@[A-Za-z0-9_]+"
MISSING['text'] = MISSING['text'].str.replace(replace_handles_regex, '', regex=True)
TWEETS['text'] = TWEETS['text'].str.replace(replace_handles_regex, '', regex=True)

# Replace &amp
replace_html_regex: str = r'&amp'
MISSING['text'] = MISSING['text'].str.replace(replace_html_regex, '', regex=True)
TWEETS['text'] = TWEETS['text'].str.replace(replace_html_regex, '', regex=True)

# Replace Characters
# replace_char_regex: str = r'[”"\'’‘ !$%^&*()_+|~\-=`{}[\]:;<>?,./@â€“–¦]'
replace_char_regex: str = r'[\W]*'
MISSING['text'] = MISSING['text'].str.replace(replace_char_regex, '', regex=True)
TWEETS['text'] = TWEETS['text'].str.replace(replace_char_regex, '', regex=True)

# Replace Characters 2
replace_char_two_regex: str = r'[”"\'’‘ !$%^&*()_+|~\-=`{}[\]:;<>?,./@â€“–¦]'
MISSING['text'] = MISSING['text'].str.replace(replace_char_two_regex, '', regex=True)
TWEETS['text'] = TWEETS['text'].str.replace(replace_char_two_regex, '', regex=True)

# Drop Exact Matches Without Quotes
MISSING = MISSING[~MISSING["text"].isin(TWEETS["text"])].dropna()

# Prepare For Export Of Missing Tweets
MISSING.drop(columns=["text"], inplace=True)
MISSING.rename(columns={"original": "text"}, inplace=True)

MISSING.reset_index(inplace=True, drop=True)
MISSING.to_csv(OUTPUT_CSV, index=None)
# TWEETS.to_csv(os.path.join(WORKING_DIRECTORY, "tweets-debug.csv"))

print("Missing Tweets:")
print(MISSING)

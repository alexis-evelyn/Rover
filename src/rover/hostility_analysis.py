#!/usr/bin/python
# Tutorial: https://www.analyticsvidhya.com/blog/2018/02/the-different-methods-deal-text-data-predictive-python/
# Stop Words Explanation: https://www.geeksforgeeks.org/removing-stop-words-nltk-python/

import json
import logging
from typing import List

import nltk
import pandas as pd
from nltk.corpus import stopwords
from textblob import TextBlob, Word


def avg_word(sentence) -> float:
    words = sentence.split()
    return sum(len(word) for word in words) / len(words)


class HostilityAnalysis:
    def __init__(self, logger_param: logging.Logger, verbose_level: int):
        # Download Commonly Used Words List (Words To Ignore)
        try:
            nltk.data.find('corpora/stopwords')
        except LookupError:
            nltk.download('stopwords')

        # Download Lemmatizer
        try:
            nltk.data.find('corpora/wordnet')
        except LookupError:
            nltk.download('wordnet')

        # Download Tokenizer Data
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            nltk.download('punkt')

        # Logging
        self.logger = logger_param
        self.VERBOSE = verbose_level

        # Setup Variables
        self.stop_words: List[str] = stopwords.words('english')
        # self.stop_words_set: frozenset = frozenset(stopwords)
        self.tweets: pd.DataFrame = pd.DataFrame()

    def add_tweet_to_process(self, tweet: json):
        text: str = tweet[
            "text"]  # Test String For Spelling Correction - 'helli wurld coool nicce thic enuf therre juuke lipp'

        # self.tweet: json = tweet
        analysis_data: json = {
            "id": str(tweet["id"]),
            "text": text,
            "word_count": len(text.split(" ")),
            "character_count": len(text),
            "average_word_count": avg_word(text),
            "stop_words_count": len([text for text in text.split() if text in self.stop_words]),
            "hashtag_count": len([text for text in text.split() if text.startswith('#')]),
            "numeric_count": len([text for text in text.split() if text.isdigit()]),
            "uppercase_word_count": len([text for text in text.split() if text.isupper()]),
            "lowercase_word_count": len([text for text in text.split() if text.islower()])
        }

        # Append Tweet To DataFrame
        self.tweets = self.tweets.append(analysis_data, ignore_index=True)

        # Debug Logging
        self.logger.log(self.VERBOSE, self.tweets)
        self.logger.log(self.VERBOSE, text)

    def remove_stop_words(self, text):
        try:
            " ".join(text for x in text.split() if x not in self.stop_words)
        except AttributeError as e:
            print(f"{text} - {e}")

    def preprocess_tweets(self):
        # Debug DataFrame
        # self.tweets["text"].apply(lambda x: print(f"X: {x}"))

        # Convert To Lowercase
        # self.tweets["text"] = self.tweets["text"].apply(lambda x: " ".join(x.lower() for x in x.split()))  # Convert To Lowercase To Avoid Duplicate Words
        self.logger.info("Lower-Casing Whole DataFrame")
        self.tweets["text"] = self.tweets["text"].str.lower()
        self.tweets["text"].head()

        # Remove Retweet Markers
        self.logger.info("Removing Retweet Markers")
        self.tweets["text"] = self.tweets["text"].replace(r'RT @\w{0,20}: ', '', regex=True)  # Remove Retweet Markers

        # Remove Mentions
        self.logger.info("Removing Mentions")
        self.tweets["text"] = self.tweets["text"].replace(r'@\w{0,20}', '', regex=True)  # Remove Retweet Markers

        # Remove Links
        self.logger.info("Removing Links")
        self.tweets["text"] = self.tweets["text"].replace(r'http[s]*://[^ ]+', ' ', regex=True)  # Remove Links

        # Remove Commas
        self.logger.info("Removing Commas")
        self.tweets["text"] = self.tweets["text"].replace(r'[,]', ' ', regex=True)  # Remove Commas

        # Remove Other Punctuation
        self.logger.info("Removing Other Punctuation")
        self.tweets["text"] = self.tweets["text"].replace(r'[^\w\s]', '', regex=True)  # Remove Other Punctuation
        self.tweets["text"].head()

        # Debug DataFrame
        # self.logger.error("Debugging NoneType in Text")
        # self.tweets: pd.DataFrame = self.tweets[~self.tweets["word_count"].notnull()]
        # print(self.tweets)
        # exit(0)

        self.logger.info("Removing Invalid Rows")
        self.tweets: pd.DataFrame = self.tweets[self.tweets["word_count"].notnull()]

        self.logger.info("Casting Row Types To Proper DataTypes")
        self.tweets["character_count"] = pd.to_numeric(self.tweets["character_count"], downcast='integer')
        self.tweets["hashtag_count"] = pd.to_numeric(self.tweets["hashtag_count"], downcast='integer')
        self.tweets["lowercase_word_count"] = pd.to_numeric(self.tweets["lowercase_word_count"], downcast='integer')
        self.tweets["numeric_count"] = pd.to_numeric(self.tweets["numeric_count"], downcast='integer')
        self.tweets["stop_words_count"] = pd.to_numeric(self.tweets["stop_words_count"], downcast='integer')
        self.tweets["uppercase_word_count"] = pd.to_numeric(self.tweets["uppercase_word_count"], downcast='integer')
        self.tweets["word_count"] = pd.to_numeric(self.tweets["word_count"], downcast='integer')

        # print(
        #     self.tweets["text"].apply(
        #         lambda x:
        #             self.remove_stop_words(text=x)
        #     )
        # )

        # Remove Stop Words
        self.logger.info("Removing Stop Words")
        self.tweets["text"] = self.tweets["text"].apply(lambda x: " ".join(x for x in x.split() if x not in self.stop_words))  # Remove Stop Words
        # self.tweets["text"] = self.tweets["text"]  # Remove Stop Words - https://codereview.stackexchange.com/a/232550/121665
        self.tweets["text"].head()

        # Filter Out Most Common Words - TODO: No Idea Why I Need This, Plus It Causes All Words To Be Removed Anyway (When Text Is Short Enough)
        # most_common_words = pd.Series(' '.join(self.tweets["text"]).split()).value_counts()[:10]  # Prepare To Remove 10 Most Common Words
        # freq: List[int] = list(most_common_words.index)  # Create List of 10 Most Common Words
        # self.tweets["text"] = self.tweets["text"].apply(lambda x: " ".join(x for x in x.split() if x not in freq))  # Apply List of 10 Most Common Words
        # self.tweets["text"].head()
        # print(self.tweets["text"]); exit(0)

        # Filter Out Least Common Words - TODO: No Idea Why I Need This, Plus It Causes All Words To Be Removed Anyway (When Text Is Short Enough)
        # least_common_words = pd.Series(' '.join(self.tweets["text"]).split()).value_counts()[-10:]  # Prepare To Remove 10 Most Common Words  # Prepare To Remove 10 Least Common Words
        # freq: List[int] = list(least_common_words.index)  # Create List of 10 Least Common Words
        # self.tweets["text"] = pd.Series(' '.join(self.tweets["text"]).split()).value_counts()[-10:]  # Apply List of 10 Most Common Words
        # self.tweets["text"].head()
        # print(self.tweets["text"]); exit(0)

        # Correct Common Spelling Mistakes
        # self.logger.info("Fixing Common Spelling Mistakes")
        # self.tweets["text"] = self.tweets["text"].apply(lambda x: print(str(TextBlob(x).correct())))  # Correct Spelling For Mistyped Words - drama favorite looks

        # Tokenize Words
        # print(TextBlob(self.tweets["text"].to_string()).words)

        # Stem Words - Article Claims Lemmatization is Better
        # self.tweets["text"][:5].apply(lambda x: " ".join([nltk.PorterStemmer().stem(word_s) for word_s in x.split()]))

        # Lemmatize Words
        self.logger.info("Lemmatizing Words")
        self.tweets["text"] = self.tweets["text"].apply(lambda x: " ".join([Word(word_l).lemmatize() for word_l in x.split()]))
        self.tweets["text"].head()

        self.logger.info("Resetting Index")
        self.tweets.reset_index(drop=True, inplace=True)

        # Test Output of Preprocessing
        self.logger.info("Test Pre-Processed Words")
        self.logger.info(self.tweets["text"])
        # for word in self.tweets["text"]:
        #     logging.log(self.VERBOSE, word)

        return self.tweets

    def process_tweets(self):
        # Perform Bigram Analysis On Every Tweet Added
        for tweet in self.tweets["text"]:
            self.logger.log(self.VERBOSE, TextBlob(tweet).ngrams(2))

        # Process Sentiment of Tweets
        results: List[dict] = []
        sentiment: pd.DataFrame = self.tweets["text"].apply(lambda x: TextBlob(x).sentiment)
        for row in range(0, len(sentiment.index)):
            polarity, subjectivity = sentiment[row]
            processed_text: str = self.tweets["text"][row]
            tweet_id: str = self.tweets["id"][row]

            result: dict = {
                "polarity": polarity,
                "subjectivity": subjectivity,
                "id": tweet_id,
                "text": processed_text
            }
            results.append(result)

            self.logger.warning(f"Polarity: {polarity}, Subjectivity: {subjectivity}, Tweet ID: {tweet_id}, Text: {processed_text}")

        # TODO: Output Polarity and Subjectivity As Well As Try To Understand The Article More
        # TODO: Make Sure To Pull Tweet(s) From User Request
        # WTF are Word Embeddings? https://www.analyticsvidhya.com/blog/2018/02/the-different-methods-deal-text-data-predictive-python/
        # https://www.analyticsvidhya.com/blog/2017/06/word-embeddings-count-word2veec/
        return results

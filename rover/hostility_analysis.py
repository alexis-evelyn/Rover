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

    def preprocess_tweets(self):
        # Convert To Lowercase
        self.tweets["text"] = self.tweets["text"].apply(
            lambda x: " ".join(x.lower() for x in x.split()))  # Convert To Lowercase To Avoid Duplicate Words
        self.tweets["text"].head()

        # Remove Punctuation - TODO: This doesn't seem to work
        self.tweets["text"] = self.tweets["text"].replace(r'[^\w\s]', '')  # Remove Punctuation
        self.tweets["text"].head()

        # Remove Stop Words
        self.tweets["text"] = self.tweets["text"].apply(
            lambda x: " ".join(x for x in x.split() if x not in self.stop_words))  # Remove Stop Words
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
        self.tweets["text"] = self.tweets["text"].apply(
            lambda x: str(TextBlob(x).correct()))  # Correct Spelling For Mistyped Words

        # Tokenize Words
        # print(TextBlob(self.tweets["text"].to_string()).words)

        # Stem Words - Article Claims Lemmatization is Better
        # self.tweets["text"][:5].apply(lambda x: " ".join([nltk.PorterStemmer().stem(word_s) for word_s in x.split()]))

        # Lemmatize Words
        self.tweets["text"] = self.tweets["text"].apply(
            lambda x: " ".join([Word(word_l).lemmatize() for word_l in x.split()]))
        self.tweets["text"].head()

        # Test Output of Preprocessing
        for word in self.tweets["text"]:
            logging.log(self.VERBOSE, word)

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
                "tweet_id": tweet_id,
                "processed_text": processed_text
            }
            results.append(result)

            self.logger.warning(f"Polarity: {polarity}, Subjectivity: {subjectivity}, Tweet ID: {tweet_id}, Text: {processed_text}")

        # TODO: Output Polarity and Subjectivity As Well As Try To Understand The Article More
        # TODO: Make Sure To Pull Tweet(s) From User Request
        # WTF are Word Embeddings? https://www.analyticsvidhya.com/blog/2018/02/the-different-methods-deal-text-data-predictive-python/
        # https://www.analyticsvidhya.com/blog/2017/06/word-embeddings-count-word2veec/
        return results

import logging

VERBOSE = logging.DEBUG - 1
logging.addLevelName(VERBOSE, "VERBOSE")

INFO_QUIET = logging.INFO + 1
logging.addLevelName(INFO_QUIET, "INFO_QUIET")
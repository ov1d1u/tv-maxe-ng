import logging

# This module just configures the Python's logger, nothing else

def set_logging_level(level=logging.INFO):
	logging.basicConfig(level=level)
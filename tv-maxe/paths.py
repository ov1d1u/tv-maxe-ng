import os
from pathlib import Path

HOME_DIR = str(Path.home())
CACHE_DIR = os.path.join(HOME_DIR, *['.tv-maxe-ng', 'cache'])
LOCAL_CHANNEL_DB = os.path.join(CACHE_DIR, 'user.db')

if not os.path.exists(CACHE_DIR):
	os.makedirs(CACHE_DIR)
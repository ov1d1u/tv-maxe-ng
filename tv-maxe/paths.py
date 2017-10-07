import os
from pathlib import Path

HOME_DIR = str(Path.home())
CACHE_DIR = os.path.join(HOME_DIR, *['.tv-maxe-ng', 'cache'])
LOCAL_CHANNEL_DB = os.path.join(CACHE_DIR, 'user.db')
EPG_CACHE = os.path.join(CACHE_DIR, 'epg_cache.db')

if not os.path.exists(CACHE_DIR):
	os.makedirs(CACHE_DIR)
import os
from pathlib import Path

home_dir = str(Path.home())
cache_dir = os.path.join(home_dir, *['.tv-maxe-ng', 'cache'])

if not os.path.exists(cache_dir):
	os.makedirs(cache_dir)
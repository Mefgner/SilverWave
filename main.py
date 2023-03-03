from pathlib import Path
from json import load
from _tagging import tager
from pybot import TelegramBot
import sys

if __name__ == '__main__':
	if sys.argv[-1] == 'tg':
		with open(Path('./config.json'), encoding='utf-8') as f:
			config = load(f)
			name, bot_hash, api_id, api_hash, temp_file = config.values()
			TelegramBot(name, bot_hash, api_id, api_hash, Path(temp_file)).run()
	else:
		tager.converter_wrapper(Path('./temp/01. Dr. West (Skit).flac'), Path('./temp/01. Dr. West (Skit).aac'), 'adts')

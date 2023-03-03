from _tagging import tager
from pyrogram import filters, types, Client, handlers
from pathlib import Path

button = types.InlineKeyboardButton
markup = types.InlineKeyboardMarkup


class TelegramBot(Client):
	_temp_path: Path
	_messages: list[dict[str, types.Message | str]] = []

	def __init__(self, name: str, bot_token: str, api_id: str, api_hash: str, temp_path: Path = Path('temp/')):
		super().__init__(name, bot_token=bot_token, api_id=api_id, api_hash=api_hash)
		self._temp_path = temp_path
		self.add_handler(handlers.message_handler.MessageHandler(
				self.help_msg,
				filters=filters.command('help', '/') | filters.command('start', '/'))
		)
		self.add_handler(handlers.message_handler.MessageHandler(
				self.audio_getter,
				filters=filters.reply & (filters.command('Convert', '') | filters.command('Conv', ''))
		))
		self.add_handler(handlers.callback_query_handler.CallbackQueryHandler(
				self.audio_processor)
		)

	@staticmethod
	async def help_msg(client: Client, message: types.Message):
		await client.send_message(message.chat.id,
		                          'Just send an audiofile and reply it with message: `convert` or `conv`')

	async def audio_getter(self, client: Client, message: types.Message):
		if message.reply_to_message.audio is not None:
			message = message.reply_to_message
			path = await client.download_media(message, str(self._temp_path) + '/' + message.audio.file_name)
			layout = markup(
					[
							[button('FLAC', 'flac'), button('WAV', 'wav')],
							[button('MP3', 'mp3'), button('AAC', 'adts'), button('OGG', 'ogg')]
					]
			)

			self._messages.append({'message': message, 'path': path})
			await message.reply('Choose type to convert:', quote=True, reply_markup=layout)

	async def audio_processor(self, _: Client, callback: types.CallbackQuery):
		await callback.message.edit('Processing...', reply_markup=None)
		export_format: str = callback.data
		current_message = self._messages.pop()
		try:
			converted_path = \
				tager.converter_wrapper(
						Path(current_message['path']),
						Path(current_message['path'].replace(
								current_message['path'].rsplit('.')[-1],
								export_format if export_format != 'adts' else 'aac'
						)), export_format)
		except Exception as e:
			raise e
		# await current_message['message'].reply(e.__str__())
		else:
			await current_message['message'].reply_audio(str(converted_path), quote=True)
			await callback.message.delete()

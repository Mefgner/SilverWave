from typing import Any
from mutagen import flac, id3
from abc import ABC, abstractmethod
from tags_table import translate_dictionary as td


def _interpolate_int(from_, to_, value):
	return int(from_ / to_ * value)


class _CommonTag(ABC):
	_value: Any
	_key: Any

	@property
	@abstractmethod
	def get_as_id3(self):
		pass

	@property
	@abstractmethod
	def get_as_ogg(self):
		pass


class _OggCommentTag(_CommonTag):
	_value: list[str]
	_key: str

	def __init__(self, key: str, value: list[str]):
		self._value = value
		self._key = key

	def __str__(self):
		return ', '.join([self._key, str(self._value)])

	@property
	def get_as_id3(self):
		frame = td.get(self._key.lower())
		if isinstance(frame, id3.Frames['POPM']):
			return frame(rating=_interpolate_int(100, 255, int(self._value[0])))
		elif isinstance(frame, id3.Frames['TXXX']):
			return frame(text=self._value, desc=self._key)
		elif frame:
			return frame(text=self._value, encoding=3)

	@property
	def get_as_ogg(self):
		return self._value

	@property
	def value(self):
		return self._value

	@property
	def key(self):
		return self._key


class _Id3Tag(_CommonTag):
	_value: id3.Frame | id3.TextFrame | id3.PairedTextFrame
	_key: str

	def __init__(self, value: id3.Frame | id3.TextFrame | id3.PairedTextFrame):
		self._value = value
		self._key = value.FrameID

	def __str__(self):
		return str(self._value)

	@property
	def value(self):
		return self._value

	@property
	def key(self):
		return self._value

	@property
	def get_as_id3(self):
		return self._value

	@property
	def get_as_ogg(self):
		if self._key == 'TXXX':
			return {self._value.desc: [self._value.text]}
		ogg_key = td.get(self._key)
		if ogg_key:
			return {ogg_key: self._value.text}
		elif ogg_key == 'rating':
			return {ogg_key: [str(_interpolate_int(255, 100, self._value.rating))]}


class _DoubledOggTag(_CommonTag):
	__raw_tags: list[_OggCommentTag]
	_value: list[list[str]]  # 0: total track/disc, 1: current
	_key: list[str]

	def __init__(self, tags: list[_OggCommentTag]):
		self._value = []
		self._key = []
		self.__raw_tags = tags
		for tag in self.__raw_tags:
			self._value.append(tag.value)
			self._key.append(tag.key)

	def __str__(self):
		return ', '.join([str(self._key), str(self._value)])

	@property
	def get_as_id3(self):
		frame = td.get(self._key[0])
		print(self.__raw_tags, self._value, self._key)
		if frame:
			return frame(text=f'{self._value[1][0]}/{self._value[0][0]}', encoding=3)

	@property
	def get_as_ogg(self):
		return self.__raw_tags


class _OggPictureTag(_CommonTag):
	_pic: flac.Picture

	def __init__(self, pic: flac.Picture):
		self._key = pic.type
		self._pic = pic

	def __repr__(self):
		return ', '.join([self._pic.mime, str(self._pic.type)])

	@property
	def get_as_id3(self):
		type_ = self._pic.type
		data = self._pic.data
		desc = self._pic.desc
		mime = self._pic.mime

		return id3.APIC(type=type_, data=data, desc=desc, mime=mime)

	@property
	def get_as_ogg(self):
		return self._pic


class _Id3PictureTag(_CommonTag):
	_pic: id3.APIC

	def __init__(self, pic: id3.APIC):
		self._key = pic.type
		self._pic = pic

	def __str__(self):
		return ', '.join([self._pic.mime, str(self._pic.type)])

	@property
	def get_as_id3(self):
		return self._pic

	@property
	def get_as_ogg(self):
		type_ = self._pic.type
		data = self._pic.data
		desc = self._pic.desc
		mime = self._pic.mime

		flac_pic = flac.Picture()
		flac_pic.data = data
		flac_pic.type = type_
		flac_pic.mime = mime
		flac_pic.desc = desc

		return flac_pic


class TagCollection:
	_tags = list()
	_pictures = list()

	def __init__(self):
		pass

	def __str__(self):
		return str('\n'.join([str(self._tags), str(self._pictures)]))

	def append(self, *args):  # 0:key, 1:value; 0:value; 0:key, 1:value, 2:description
		if len(args) == 2:
			key = args[0]
			value: list = args[1]
			if isinstance(key, list):
				self._tags.append(_DoubledOggTag([
						_OggCommentTag(key.pop(), value.pop()),
						_OggCommentTag(key.pop(), value.pop())
				]))
			else:
				self._tags.append(_OggCommentTag(key, value))
		elif len(args) == 1:
			value: flac.Picture | id3.Frame | id3.APIC = args[0]
			if isinstance(value, flac.Picture):
				self._pictures.append(_OggPictureTag(value))
			elif isinstance(value, id3.APIC):
				self._pictures.append(_Id3PictureTag(value))
			elif isinstance(value, tuple(id3.Frames.values())):
				self._tags.append(_Id3Tag(value))
			else:
				raise ValueError()
		else:
			raise ValueError()

	@property
	def get_tags(self):
		return self._tags

	@property
	def get_pictures(self):
		return self._pictures

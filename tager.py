from typing import Any
from abc import ABC, abstractmethod
from pathlib import Path
import base64
from mutagen import aac, wave, mp3, id3, flac, oggvorbis, File, FileType
from pydub import AudioSegment



class _DoubleSideDict(dict):
	def __init__(self, mappable: dict):
		super().__init__()
		for key in mappable.keys():
			self.__setitem__(key, mappable[key])

	def __getitem__(self, key):
		for _key in self.keys():
			if _key == key:
				return self[key]
		for _value in self.values():
			if _value == self[key]:
				return _value
		raise KeyError()


translate_dictionary = _DoubleSideDict(
		{
				'discnumber': id3.Frames['TPOS'],
				'disctotal': id3.Frames['TPOS'],
				'tracknumber': id3.Frames['TRCK'],
				'tracktotal': id3.Frames['TRCK'],
				'date': id3.Frames['TYER'],
				'title': id3.Frames['TIT2'],
				'artist': id3.Frames['TPE1'],
				'albumartist': id3.Frames['TPE2'],
				'album': id3.Frames['TALB'],
				'genre': id3.Frames['TCON'],
				'rating': id3.Frames['POPM'],
				'replaygain_album_gain': id3.Frames['TXXX'],
				'replaygain_track_gain': id3.Frames['TXXX'],
				'replaygain_album_peak': id3.Frames['TXXX'],
				'replaygain_track_peak': id3.Frames['TXXX'],
				'copyright': id3.Frames['TCOP'],
				'isrc': id3.Frames['TSRC'],
				'wwwpublisher': id3.Frames['WPUB'],
				'organization': id3.Frames['TPUB'],
				'publisher': id3.Frames['TPUB']
		}
)


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
		frame = translate_dictionary.get(self._key.lower())
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
		ogg_key = translate_dictionary.get(self._key)
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
		frame = translate_dictionary.get(self._key[0])
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


def _id3_extractor(f: Path) -> TagCollection:
	values: list
	try:
		audio = File(f)
		values = list(audio.tags.values)
	except mp3.HeaderNotFoundError:
		audio = id3.ID3(f)
		values = list(audio.values())
	except AttributeError:
		return TagCollection()
	tags = TagCollection()
	for tag in values:
		tags.append(tag)

	print([x.__str__() for x in tags.get_tags])
	return tags


def _ogg_comment_extractor(f: Path) -> TagCollection:
	tags = TagCollection()
	audio = File(f)
	type_ = type(audio)

	try:
		disc_num = audio.pop('discnumber')
		disc_total = audio.pop('disctotal')
		tags.append(['discnumber', 'disctotal'], [disc_num, disc_total])
	except KeyError:
		pass
	try:
		track_num = audio.pop('tracknumber')
		track_total = audio.pop('tracktotal')
		tags.append(['discnumber', 'disctotal'], [track_num, track_total])
	except KeyError:
		pass

	for tag in audio.tags:
		tags.append(tag[0], [tag[-1]])

	pictures = None
	if type_ == flac.FLAC:
		audio = flac.FLAC(f)
		pictures = audio.pictures
	elif type_ == oggvorbis.OggVorbis:
		audio = oggvorbis.OggVorbis(f)
		pictures = audio['metadata_block_picture']
	if pictures:
		for picture in pictures:
			tags.append(picture)

	print([x.__str__() for x in tags.get_tags])
	return tags


def tag_extractor(f: Path) -> TagCollection:
	extension = f.suffix.replace('.', '')
	if extension in ['flac', 'ogg']:
		return _ogg_comment_extractor(f)
	elif extension in ['mp3', 'aac', 'wav']:
		return _id3_extractor(f)


def tag_inserter(tags: TagCollection, export_file: Path) -> Path:
	file_to_paste: flac.FLAC | aac.AAC | mp3.MP3 | wave.WAVE | oggvorbis.OggVorbis | FileType = File(export_file)
	all_tags = list()
	if isinstance(file_to_paste, flac.FLAC) or isinstance(file_to_paste, oggvorbis.OggVorbis):
		for tag in tags.get_tags:
			ogg_tags = tag.get_as_ogg
			file_to_paste: flac.FLAC | oggvorbis.OggVorbis
			if len(ogg_tags) >= 2:
				for included_tag in ogg_tags:
					file_to_paste.tags.update(included_tag.get_as_ogg)
			else:
				file_to_paste.tags.update(tag.get_as_ogg)
		for picture in tags.get_pictures:
			ogg_tags = picture.get_as_ogg
			if isinstance(ogg_tags, flac.Picture):
				if isinstance(file_to_paste, oggvorbis.OggVorbis):
					picture = base64.b64encode(ogg_tags.write()).decode('ascii')
					if not file_to_paste.get('metadata_block_picture'):
						file_to_paste['metadata_block_picture'] = [picture]
					else:
						file_to_paste['metadata_block_picture'].append(picture)
				else:
					file_to_paste.add_picture(ogg_tags)
		file_to_paste.save()
		return export_file
	elif isinstance(file_to_paste, aac.AAC):
		file_to_paste.tags = id3.ID3()
		all_tags = tags.get_tags
		all_tags.extend(tags.get_pictures)
	if isinstance(file_to_paste, wave.WAVE):
		file_to_paste.add_tags()
		all_tags = tags.get_tags
		all_tags.extend(tags.get_pictures)
	elif isinstance(file_to_paste, mp3.MP3):
		all_tags = tags.get_tags
		all_tags.extend(tags.get_pictures)
	for tag in all_tags:
		try:
			file_to_paste.tags.add(tag.get_as_id3)
		except TypeError:
			print(f'Tag: {str(tag)} was skipped')
	file_to_paste.save()
	return export_file


def converter(input_path: Path, export_path: Path, export_format: str) -> Path:
	bitrates = {'mp3': '320k', 'adts': '128k', 'ogg': '96k'}
	with open(input_path, 'rb') as f:
		audio = AudioSegment.from_file(file=f)
		audio.export(
				export_path, format=export_format, bitrate=bitrates.get(export_format), parameters=('-q:a', '0')
		)
	tags = tag_extractor(input_path)
	tag_inserter(tags, export_path)
	return export_path

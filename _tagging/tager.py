from pathlib import Path
import base64
from .tags import TagCollection
# from .tags_table import translate_dictionary as td
from mutagen import aac, wave, mp3, id3, flac, oggvorbis, File, FileType
from pydub import AudioSegment


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
	return export_path


def converter_wrapper(input_path: Path, export_path: Path, export_format: str) -> Path:
	converter(input_path, export_path, export_format)
	tags = tag_extractor(input_path)
	tag_inserter(tags, export_path)
	return export_path

from mutagen import id3


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

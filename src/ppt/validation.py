"""Reject malformed or oversized presentations before scheduling audio inference."""
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree
from lxml.etree import XMLSyntaxError


def validate_pptx(path):
    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 20000 or sum(entry.file_size for entry in entries) > 512 * 1024 ** 2:
                raise ValueError('Presentation is too large after decompression')
            for name in ('[Content_Types].xml', 'ppt/presentation.xml'):
                info = archive.getinfo(name)
                if info.file_size > 8 * 1024 ** 2 or info.flag_bits & 1:
                    raise ValueError('Invalid presentation metadata')
                contents = archive.read(name)
                if b'<!DOCTYPE' in contents.upper() or b'<!ENTITY' in contents.upper():
                    raise ValueError('Presentation XML entities are not supported')
                ElementTree.fromstring(contents)
        from pptx import Presentation
        Presentation(path)  # Check package relationships and content types too.
    except (BadZipFile, KeyError, ElementTree.ParseError, XMLSyntaxError, RuntimeError,
            OSError, AttributeError, TypeError, ValueError) as exc:
        raise ValueError('Invalid PPTX presentation; export as .pptx and upload again') from exc

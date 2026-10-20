"""Extract ordered presentations into one slide sequence with source provenance."""
from pathlib import Path

from src.ppt.extract import PPTXExtractor, PresentationData


def extract_presentations(paths, meeting_id):
    if isinstance(paths, (str, Path)):
        paths = [paths]
    slides = []
    sources = []
    for index, path in enumerate(paths, 1):
        path = Path(path)
        deck = PPTXExtractor(path, meeting_id=meeting_id).extract()
        sources.append(str(path))
        for slide in deck.slides:
            slide.metadata.update(source_file=path.name, source_presentation=index,
                                  source_slide_number=slide.slide_number)
            slide.slide_number = len(slides) + 1
            slide.slide_id = f'slide_{slide.slide_number:02d}'
            slides.append(slide)
    return PresentationData(meeting_id, '; '.join(sources), len(slides), slides)

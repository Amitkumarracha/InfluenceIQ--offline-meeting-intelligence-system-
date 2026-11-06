"""Build the evaluator deck and printable script from the reviewed Markdown."""
from pathlib import Path
import re

from markdown_it import MarkdownIt
from PIL import ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches, Pt


HERE = Path(__file__).resolve().parent
SOURCE = HERE / 'EVALUATOR_PRESENTATION_SCRIPT_20261026.md'
text = SOURCE.read_text()
slide_text = text.split('## Appendix A', 1)[0]
sections = re.split(r'^## Slide (\d+) — (.+)$', slide_text, flags=re.MULTILINE)
slides = []
for offset in range(1, len(sections), 3):
    number, title, body = sections[offset:offset + 3]
    bullets = re.findall(r'^- (.+)$', body, flags=re.MULTILINE)
    notes = '\n\n'.join(re.findall(r'^> (.+)$', body, flags=re.MULTILINE))
    assert 3 <= len(bullets) <= 5 and notes, title
    slides.append((int(number), title, bullets, notes))
assert len(slides) == 26 and [s[0] for s in slides] == list(range(1, 27))

deck = Presentation()
deck.slide_width, deck.slide_height = Inches(13.333), Inches(7.5)
ink, teal, muted = '17324D', '087F8C', '526675'


def textbox(slide, value, x, y, width, height, size, color=ink, bold=False):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(width), Inches(height))
    frame = shape.text_frame
    frame.word_wrap = False
    frame.margin_left = frame.margin_right = Inches(0)
    frame.margin_top = frame.margin_bottom = Inches(0)
    for index, line in enumerate(value.split('\n')):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = line
        paragraph.font.name = 'Noto Sans'
        paragraph.font.size = Pt(size)
        paragraph.font.bold = bold
        paragraph.font.color.rgb = RGBColor.from_string(color)
        paragraph.space_after = Pt(0)
        paragraph.line_spacing = 1.08
    return shape


def wrap(value, size, width):
    font = ImageFont.truetype('/usr/share/fonts/noto/NotoSans-Regular.ttf', round(size * 96 / 72))
    lines, current = [], ''
    for word in value.split():
        candidate = (current + ' ' + word).strip()
        if current and font.getlength(candidate) > width * 96:
            lines.append(current)
            current = word
        else:
            current = candidate
    return lines + [current]


for number, title, bullets, notes in slides:
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor.from_string('FFFFFF')
    textbox(slide, 'INFLUENCEIQ  /  MEET IQ', .65, .35, 12, .3, 12, teal, True)
    title_size = 29 if len(title) > 56 else 32
    textbox(slide, title, .65, .95, 12, .65, title_size, bold=True)
    rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(.65), Inches(1.68), Inches(12), Inches(.045))
    rule.fill.solid()
    rule.fill.fore_color.rgb = RGBColor.from_string(teal)
    rule.line.fill.background()
    size = 23
    while True:
        wrapped = [wrap(value, size, 11.55) for value in bullets]
        heights = [len(lines) * size * 1.20 / 72 + .17 for lines in wrapped]
        if sum(heights) <= 4.65:
            break
        size -= .5
        assert size >= 20, title
    y = 2.02
    for lines, height in zip(wrapped, heights):
        textbox(slide, '•', .70, y, .25, .45, size, teal, True)
        textbox(slide, '\n'.join(lines), 1.08, y, 11.55, height, size)
        y += height
    assert y < 6.8, title
    textbox(slide, 'Project explanation · 26 October 2026 · See speaker notes for the script', .65, 7.06, 11, .22, 10, muted)
    textbox(slide, f'{number:02d} / {len(slides)}', 11.75, 7.02, 1, .3, 12, teal, True)
    slide.notes_slide.notes_text_frame.text = notes + '\n\nFull methods, equations, caveats and 50 viva answers: ' + SOURCE.name
    for shape in slide.shapes:
        assert shape.left >= 0 and shape.top >= 0
        assert shape.left + shape.width <= deck.slide_width
        assert shape.top + shape.height <= deck.slide_height

output = HERE / 'EVALUATOR_PRESENTATION_20261026.pptx'
deck.save(output)
assert len(Presentation(output).slides) == 26

body = MarkdownIt('commonmark', {'html': False}).enable('table').render(text)
html = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>InfluenceIQ — presentation script and viva</title><style>
@page { size: A4; margin: 18mm; }
body { font: 10.5pt/1.45 "Noto Sans", Arial, sans-serif; color: #17324d; max-width: 760px; margin: auto; }
h1 { font-size: 25pt; line-height: 1.15; color: #087f8c; }
h2 { font-size: 18pt; line-height: 1.2; break-before: page; }
h3 { font-size: 13pt; }
h1, h2, h3 { break-after: avoid; }
p, li { orphans: 3; widows: 3; }
blockquote { margin: 12px 0; padding: 8px 15px; border-left: 3px solid #087f8c; background: #eff7f8; }
table { width: 100%; border-collapse: collapse; font-size: 9pt; table-layout: fixed; }
th, td { border: 1px solid #cad8df; padding: 6px; text-align: left; overflow-wrap: anywhere; }
tr { break-inside: avoid; } th { background: #e5f1f3; }
code { font-size: 9pt; overflow-wrap: anywhere; }
a { color: #087f8c; overflow-wrap: anywhere; }
</style></head><body>''' + body + '</body></html>'
handout = SOURCE.with_suffix('.html')
handout.write_text(html)
print('Slides:', len(slides))
print('Editable deck:', output)
print('Printable script:', handout)

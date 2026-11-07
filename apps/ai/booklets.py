"""
The PhilRice and PalayCheck booklets GeoRice AI reads before it answers (Gemini File Search).

`python manage.py load_booklets` uploads them to a Gemini File Search store; the chat
then asks Gemini to search that store, and every answer comes back with the parts of the
booklets it used. Each document is stored under its key below (its display name), so a
citation maps back to the booklet's title and link (apps/advice/knowledge.SOURCES) and to
the page a farmer would find in the printed booklet: Gemini counts PDF pages, and most
booklets start their printed numbering a few pages in.
"""

# key -> the file in the booklets folder, how to name its parts, and
# printed page = PDF page + offset
BOOKLETS = {
    'palaycheck':  {'file': 'PalayCheck System 2022 Revised Edition (PhilRice).pdf', 'unit': 'p.', 'offset': -4},
    'field_guide': {'file': 'Field Guide - Harmful and Useful Organisms in Philippine Rice Fields (PhilRice).pdf',
                    'unit': 'p.', 'offset': -8},
    'harmful':     {'file': 'Harmful Organisms in Philippine Rice Fields (PhilRice).pdf', 'unit': 'chart', 'offset': 0},
    'keycheck7':   {'file': 'PalayCheck KeyCheck 7 - Pest Management (PinoyRice).pptx', 'unit': 'slide', 'offset': 0},
    'snail':       {'file': 'Golden Apple Snail Management (PinoyRice).pptx', 'unit': 'slide', 'offset': 0},
    'diseases':    {'file': 'Diseases of Rice and Their Management (PinoyRice).pptx', 'unit': 'slide', 'offset': 0},
    'blb':         {'file': 'Handout - bacterial-leaf-blight (PinoyRice).pdf', 'unit': 'p.', 'offset': 0},
    'blast_shb':   {'file': 'Handout - pamamahala-ng-sheath-blight-at-rice-blast (PinoyRice).pdf',
                    'unit': 'p.', 'offset': 0},
    'hopper':      {'file': 'Handout - pamamahala-ng-armyworm-at-planthopper (PinoyRice).pdf', 'unit': 'p.', 'offset': 0},
    'sheath_rot':  {'file': 'Handout - sheath-rot (PinoyRice).pdf', 'unit': 'p.', 'offset': 0},
}

MAX_SOURCES = 4


def _where(key, page):
    """'p. 48', 'slide 15', 'chart', or '' when the page is unknown."""
    book = BOOKLETS[key]
    if book['unit'] == 'chart':
        return 'chart'
    try:
        page = int(page)
    except (TypeError, ValueError):
        return ''
    printed = page + book['offset']
    return f"{book['unit']} {printed}" if printed > 0 else ''


def sources_from(grounding: dict) -> list[dict]:
    """The booklet parts an answer used, from Gemini's groundingMetadata, as the same
    source objects the problem cards use: {title, publisher, pages, url}. Parts the
    answer's sentences point to come first; unknown documents are left out."""
    from apps.advice.knowledge import SOURCES

    chunks = grounding.get('groundingChunks') or []
    used = []
    for support in grounding.get('groundingSupports') or []:
        for i in support.get('groundingChunkIndices') or []:
            if i not in used:
                used.append(i)
    if not used:                       # no sentence links: every part it was given
        used = list(range(len(chunks)))

    out = []
    for i in used:
        if not 0 <= i < len(chunks):
            continue
        ctx = chunks[i].get('retrievedContext') or {}
        key = (ctx.get('title') or '').strip()
        if key not in BOOKLETS or key not in SOURCES:
            continue
        info = SOURCES[key]
        source = {'title': info['title'], 'publisher': info['publisher'],
                  'pages': _where(key, ctx.get('pageNumber')), 'url': info['url']}
        if source not in out:
            out.append(source)
        if len(out) == MAX_SOURCES:
            break
    return out

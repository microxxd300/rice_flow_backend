"""
python manage.py load_booklets [--dir PATH] [--replace]

Uploads the PhilRice / PalayCheck booklets (apps/ai/booklets.py) to a Gemini File Search
store, so GeoRice AI can search them before it answers. Uses GEMINI_FILE_SEARCH_STORE
when set; otherwise makes a new store and prints the line to add to .env. A booklet
already in the store is skipped unless --replace. The PDFs are not in git: put them in
BOOKLETS_DIR (or pass --dir).

Indexing is charged at Gemini Embedding rates (all the booklets: about $0.02, once);
storage and searching are free.
"""
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ai.booklets import BOOKLETS

CHUNKING = {'white_space_config': {'max_tokens_per_chunk': 300, 'max_overlap_tokens': 30}}


class Command(BaseCommand):
    help = "Upload the PhilRice / PalayCheck booklets to GeoRice AI's Gemini File Search store"

    def add_arguments(self, parser):
        parser.add_argument('--dir', default=settings.BOOKLETS_DIR, help='Folder with the booklet files')
        parser.add_argument('--replace', action='store_true', help='Upload again booklets already in the store')

    def handle(self, *args, **opts):
        key = settings.GEMINI_API_KEY
        if not key:
            raise CommandError('GEMINI_API_KEY is not set.')
        try:
            from google import genai
        except ImportError as exc:
            raise CommandError('Install google-genai (pip install -r requirements.txt).') from exc

        client = genai.Client(api_key=key)
        store = settings.GEMINI_FILE_SEARCH_STORE
        if not store:
            store = client.file_search_stores.create(config={'display_name': 'riceflow-booklets'}).name
            self.stdout.write(self.style.WARNING(f'New store. Add this line to .env:\nGEMINI_FILE_SEARCH_STORE={store}'))

        existing = {d.display_name: d for d in client.file_search_stores.documents.list(parent=store)}
        uploaded = 0
        for name, book in BOOKLETS.items():
            path = os.path.join(opts['dir'], book['file'])
            if not os.path.exists(path):
                self.stdout.write(f'  missing  {name}: {book["file"]}')
                continue
            if name in existing:
                if not opts['replace']:
                    self.stdout.write(f'  have     {name}')
                    continue
                client.file_search_stores.documents.delete(name=existing[name].name, config={'force': True})
            op = client.file_search_stores.upload_to_file_search_store(
                file=path, file_search_store_name=store,
                config={'display_name': name, 'chunking_config': CHUNKING},
            )
            while not op.done:
                time.sleep(3)
                op = client.operations.get(op)
            if getattr(op, 'error', None):
                self.stdout.write(self.style.ERROR(f'  failed   {name}: {op.error}'))
                continue
            uploaded += 1
            self.stdout.write(f'  uploaded {name}')
        self.stdout.write(self.style.SUCCESS(f'{uploaded} booklet(s) uploaded to {store}.'))

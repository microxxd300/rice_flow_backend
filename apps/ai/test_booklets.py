"""GeoRice AI reads the PhilRice / PalayCheck booklets (Gemini File Search) before answering."""
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User

from . import views
from .booklets import sources_from
from .tests import WEATHER, gemini_reply

STORE = 'fileSearchStores/riceflow-test'


def chunk(title, page=None):
    ctx = {'title': title, 'text': '...', 'fileSearchStore': STORE}
    if page is not None:
        ctx['pageNumber'] = page
    return {'retrievedContext': ctx}


def grounded_reply(text, chunks, supports=None, status_code=200):
    resp = MagicMock(status_code=status_code)
    resp.json.return_value = {'candidates': [{
        'content': {'parts': [{'text': text}]},
        'groundingMetadata': {'groundingChunks': chunks, 'groundingSupports': supports or []},
    }]}
    return resp


class SourcesTests(TestCase):
    def test_pdf_pages_become_the_printed_page(self):
        found = sources_from({'groundingChunks': [chunk('palaycheck', 52), chunk('field_guide', 40),
                                                  chunk('snail', 15), chunk('harmful', 1)]})
        self.assertEqual([s['pages'] for s in found], ['p. 48', 'p. 32', 'slide 15', 'chart'])
        self.assertIn('PalayCheck', found[0]['title'])
        self.assertTrue(found[0]['url'].startswith('https://'))

    def test_the_parts_the_answer_points_to_come_first_and_unknown_files_are_dropped(self):
        found = sources_from({
            'groundingChunks': [chunk('palaycheck', 44), chunk('someones-notes', 3), chunk('palaycheck', 53)],
            'groundingSupports': [{'segment': {'text': 'a'}, 'groundingChunkIndices': [2, 1]},
                                  {'segment': {'text': 'b'}, 'groundingChunkIndices': [2]}],
        })
        self.assertEqual([s['pages'] for s in found], ['p. 49'])      # chunk 0 was never pointed to

    def test_repeats_merge_and_at_most_four_are_kept(self):
        chunks = [chunk('palaycheck', 52)] * 3 + [chunk('palaycheck', p) for p in (40, 41, 42, 43, 44)]
        found = sources_from({'groundingChunks': chunks})
        self.assertEqual(len(found), 4)
        self.assertEqual(found[0]['pages'], 'p. 48')

    def test_no_grounding_means_no_sources(self):
        self.assertEqual(sources_from({}), [])


@patch('apps.ai.context.get_current_weather', return_value=WEATHER)
@patch.object(views, 'GEMINI_API_KEY', 'test-key')
@override_settings(GEMINI_FILE_SEARCH_STORE=STORE)
class BookletChatTests(TestCase):
    def setUp(self):
        cache.clear()
        user = User.objects.create_user(username='grower', password='pass12345')
        self.client = APIClient()
        self.client.force_authenticate(user)

    def chat(self, message, language='en'):
        return self.client.post(reverse('ai-chat'), {'message': message, 'language': language}, format='json')

    def test_the_chat_searches_the_booklets_and_shows_the_pages(self, _weather):
        reply = grounded_reply('Check for egg masses early in the morning.', [chunk('palaycheck', 52)],
                               [{'segment': {'text': 'Check'}, 'groundingChunkIndices': [0]}])
        with patch.object(views.requests, 'post', return_value=reply) as post:
            res = self.chat('Stem borer?')
        sent = post.call_args.kwargs['json']
        self.assertEqual(sent['tools'], [{'fileSearch': {'fileSearchStoreNames': [STORE]}}])
        self.assertIn(post.call_args.args[0].split('/models/')[1].split(':')[0], views.BOOKLET_MODELS)
        self.assertIn('search them first', sent['systemInstruction']['parts'][0]['text'])
        self.assertTrue(sent['contents'][-1]['parts'][0]['text'].startswith('Stem borer?'))
        self.assertTrue(sent['contents'][-1]['parts'][0]['text'].endswith(views.BOOKLET_NUDGE))
        self.assertEqual(res.data['reply'], 'Check for egg masses early in the morning.')
        self.assertTrue(res.data['grounded'])
        self.assertEqual(res.data['sources'][0]['pages'], 'p. 48')

    def test_when_the_booklet_search_fails_the_plain_chat_still_answers(self, _weather):
        calls = []

        def post(url, **kwargs):
            calls.append(('tools' in kwargs['json'], url.split('/models/')[1].split(':')[0]))
            return gemini_reply('', status_code=400) if 'tools' in kwargs['json'] else gemini_reply('Use urea.')

        with patch.object(views.requests, 'post', side_effect=post):
            res = self.chat('Fertilizer?')
        self.assertEqual(res.data['reply'], 'Use urea.')
        self.assertEqual((res.data['grounded'], res.data['sources']), (False, []))
        self.assertEqual([c[0] for c in calls][:len(views.BOOKLET_MODELS)], [True] * len(views.BOOKLET_MODELS))
        self.assertFalse(calls[-1][0])
        self.assertIn(calls[-1][1], views.GEMINI_MODELS)

    def test_when_the_booklet_search_times_out_the_plain_chat_still_answers(self, _weather):
        def post(url, **kwargs):
            if 'tools' in kwargs['json']:
                raise views.requests.exceptions.Timeout()
            return gemini_reply('Use urea.')

        with patch.object(views.requests, 'post', side_effect=post):
            res = self.chat('Fertilizer?')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['reply'], 'Use urea.')

    def test_the_booklet_search_gets_one_long_try_and_the_plain_chat_short_ones(self, _weather):
        timeouts = []

        def post(url, **kwargs):
            timeouts.append(('tools' in kwargs['json'], kwargs['timeout']))
            if 'tools' in kwargs['json']:
                raise views.requests.exceptions.Timeout()
            return gemini_reply('Use urea.')

        with patch.object(views.requests, 'post', side_effect=post):
            self.chat('Fertilizer?')
        booklet = [t for grounded, t in timeouts if grounded]
        plain = [t for grounded, t in timeouts if not grounded]
        self.assertGreater(booklet[0], views.GEMINI_TRY_SECONDS)       # longer than a plain try
        self.assertLessEqual(booklet[0], views.GEMINI_BOOKLET_SECONDS)
        self.assertLessEqual(plain[0], views.GEMINI_TRY_SECONDS)
        # Both together stay inside the time the app waits (35 s)
        self.assertLess(views.GEMINI_DEADLINE_SECONDS, 35)

    def test_a_reply_naming_a_pesticide_is_replaced(self, _weather):
        reply = grounded_reply('Spray cypermethrin today.', [chunk('palaycheck', 52)])
        with patch.object(views.requests, 'post', return_value=reply):
            res = self.chat('What do I spray?', language='ceb')
        self.assertEqual(res.data['reply'], views.CHEMICAL_REPLY['ceb'])
        self.assertEqual(res.data['sources'], [])

    def test_an_answer_saved_before_sources_still_works(self, _weather):
        old = lambda key: 'Old answer.' if key.startswith('ai:reply:') else None   # noqa: E731
        with patch.object(views, '_cache_get', side_effect=old), patch.object(views.requests, 'post') as post:
            res = self.chat('Same question')
        post.assert_not_called()
        self.assertEqual((res.data['reply'], res.data['sources'], res.data['grounded']), ('Old answer.', [], False))

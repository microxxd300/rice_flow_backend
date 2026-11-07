from datetime import date
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.farms.models import Farm
from apps.progress.models import FarmCycle, ProgressLog

from . import services
from .knowledge import GET_HELP, LANGS, PROBLEMS, SOURCES, URGENT

GEMINI = 'apps.advice.services._gemini_json'


def all_lines():
    for key, p in PROBLEMS.items():
        for section in ('identify', 'do_now', 'dont', 'next_season'):
            for item in p[section]:
                yield key, section, item
        if p['serious_when']:
            yield key, 'serious_when', p['serious_when']
    yield 'all', 'get_help', GET_HELP


class KnowledgeTests(TestCase):
    def test_every_line_is_in_three_languages_and_cites_a_booklet(self):
        for key, section, item in all_lines():
            for lang in LANGS:
                self.assertTrue(item[lang].strip(), f'{key}.{section} has no {lang} text')
            if section != 'get_help':
                self.assertTrue(item['src'], f'{key}.{section} cites no booklet')
            for source, where in item['src']:
                self.assertIn(source, SOURCES)
                self.assertTrue(where)
        for lang in LANGS:
            self.assertTrue(URGENT[lang].strip())

    def test_the_cards_themselves_name_no_chemical_or_dose(self):
        for key, section, item in all_lines():
            for lang in LANGS:
                self.assertEqual(services.unsafe(item[lang]), '', f'{key}.{section} ({lang})')

    def test_every_problem_says_how_to_tell_and_what_to_do(self):
        for key, p in PROBLEMS.items():
            self.assertTrue(p['identify'], key)
            self.assertTrue(p['do_now'], key)
            self.assertIn(p['category'], ('pest', 'disease', 'weather', 'nutrient', 'other'))

    def test_local_words_find_the_problem(self):
        self.assertEqual(services.keyword_match('naay mga puti nga uhay, walay sulod')[0], 'stem_borer')
        self.assertEqual(services.keyword_match('Daghang kuhol sa akong uma')[0], 'golden_apple_snail')
        self.assertEqual(services.keyword_match('gikaon sa ilaga')[0], 'rats')
        self.assertEqual(services.keyword_match('mata-mata sa dahon')[0], 'blast')
        self.assertEqual(services.keyword_match('wala koy nakita'), [])


class AdviceApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='farmer', password='pass12345')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_problem_list_has_not_sure_last_in_the_farmers_language(self):
        res = self.client.get('/api/advice/problems/?language=ceb')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json()), len(PROBLEMS))
        self.assertEqual(res.json()[-1]['key'], 'unknown')
        rats = next(p for p in res.json() if p['key'] == 'rats')
        self.assertEqual(rats['name'], 'Ilaga')

    def test_the_booklet_card_shows_its_sources_without_any_ai(self):
        with mock.patch(GEMINI) as gemini:
            res = self.client.get('/api/advice/problems/stem_borer/?language=fil')
        gemini.assert_not_called()
        card = res.json()
        self.assertEqual(card['name'], 'Aksip (stem borer)')
        self.assertEqual(card['serious_when']['sources'][0]['pages'], 'p. 48')
        self.assertIn('PalayCheck', card['do_now'][0]['sources'][0]['title'])
        self.assertTrue(card['dont'])
        self.assertIn('0917', card['get_help']['text'])
        self.assertFalse(card['checked_by_validator'])
        self.assertEqual(self.client.get('/api/advice/problems/aliens/').status_code, 404)

    def test_match_without_ai_uses_the_local_words(self):
        with mock.patch(GEMINI, return_value=None):
            res = self.client.post('/api/advice/match/', {'text': 'naay kuhol', 'language': 'ceb'}, format='json')
        self.assertEqual(res.json()['matches'][0]['key'], 'golden_apple_snail')
        self.assertFalse(res.json()['ai_used'])

    def test_match_keeps_only_problems_on_the_list(self):
        answer = {'matches': [{'key': 'stem_borer', 'why': 'white empty heads'},
                              {'key': 'alien_bug', 'why': 'made up'},
                              {'key': 'blast', 'why': 'use 5 ml benomyl'}]}
        with mock.patch(GEMINI, return_value=answer):
            res = self.client.post('/api/advice/match/', {'text': 'puti ang uhay'}, format='json')
        self.assertEqual([m['key'] for m in res.json()['matches']], ['stem_borer'])
        self.assertTrue(res.json()['ai_used'])
        self.assertEqual(self.client.post('/api/advice/match/', {'text': ''}, format='json').status_code, 400)


class ExplainTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='farmer', password='pass12345')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        patcher = mock.patch('apps.ai.context.farmer_context', return_value='Crop at day 30, tillering.')
        patcher.start()
        self.addCleanup(patcher.stop)

    def explain(self, answer, problem='stem_borer', **extra):
        with mock.patch(GEMINI, return_value=answer) as gemini:
            res = self.client.post('/api/advice/explain/', {'problem': problem, 'language': 'ceb', **extra},
                                   format='json')
        self.assertEqual(res.status_code, 200)
        return res.json(), gemini

    def test_a_checked_answer_comes_with_the_booklet_pages(self):
        body, gemini = self.explain({'points': [
            {'text': 'Susiha ang uma sayo sa buntag ug pangitaa ang itlog.', 'cards': ['C4']},   # identify x2, serious, then do_now
        ], 'not_covered': False})
        self.assertTrue(body['ai_used'])
        self.assertEqual(body['points'][0]['sources'][0]['pages'], 'p. 48')
        prompt = gemini.call_args[0][1]
        self.assertIn('C1:', prompt)
        self.assertIn('Crop at day 30', prompt)            # the farm's own stage

    def test_answers_breaking_a_rule_leave_the_booklet_card(self):
        bad = {
            'no source':      {'points': [{'text': 'Do this.', 'cards': []}]},
            'unknown card':   {'points': [{'text': 'Do this.', 'cards': ['C99']}]},
            'chemical':       {'points': [{'text': 'Spray cypermethrin now.', 'cards': ['C5']}]},
            'dose':           {'points': [{'text': 'Use 20 ml per tank.', 'cards': ['C5']}]},
            'other problem':  {'points': [{'text': 'It may also be tungro.', 'cards': ['C5']}]},
            'not a list':     {'points': 'just text'},
        }
        for why, answer in bad.items():
            cache.clear()
            body, _ = self.explain(answer)
            self.assertEqual((body['ai_used'], body['points'], body['note']), (False, [], 'rejected'), why)

    def test_a_problem_the_card_itself_mentions_is_allowed(self):
        # The stem borer card compares whiteheads with neck blast
        body, _ = self.explain({'points': [
            {'text': 'Kung puti ug walay sulod, aksip; kung kolor-uhot, neck blast.', 'cards': ['C2']}]})
        self.assertTrue(body['ai_used'])

    def test_no_ai_still_answers(self):
        body, _ = self.explain(None)
        self.assertEqual((body['ai_used'], body['note']), (False, 'ai_unavailable'))

    def test_the_same_situation_is_answered_once(self):
        answer = {'points': [{'text': 'Ihapa ang tangaw.', 'cards': ['C3']}]}
        self.explain(answer, problem='black_bug')
        _, gemini = self.explain(answer, problem='black_bug')
        gemini.assert_not_called()

    def test_the_daily_ai_limit_is_shared_with_the_chat(self):
        with self.settings(AI_CHAT_DAILY_LIMIT=0):
            body, gemini = self.explain({'points': []})
        gemini.assert_not_called()
        self.assertEqual(body['note'], 'daily_limit')

    def test_unknown_problem_is_an_error(self):
        res = self.client.post('/api/advice/explain/', {'problem': 'aliens'}, format='json')
        self.assertEqual(res.status_code, 400)


class ProblemLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='farmer', password='pass12345')
        farm = Farm.objects.create(user=self.user, name='Mine', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                   area_hectares=1, ecosystem='irrigated_lowland')
        self.cycle = FarmCycle.objects.create(farm=farm, season='wet', year=2026, planting_date=date(2026, 6, 1))
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def log(self, **data):
        return self.client.post('/api/progress/logs/', {
            'farm_cycle': self.cycle.id, 'log_date': '2026-07-10', 'observation': 'Puti ang uhay', **data,
        }, format='json')

    def test_a_picked_problem_is_saved_and_fills_the_problem_type(self):
        res = self.log(problem_key='stem_borer', severity='high')
        self.assertEqual(res.status_code, 201)
        saved = ProgressLog.objects.get()
        self.assertEqual((saved.problem_key, saved.issue_type), ('stem_borer', 'pest'))

    def test_an_unknown_problem_is_refused(self):
        self.assertEqual(self.log(problem_key='aliens').status_code, 400)


class ProblemLogTipTests(TestCase):
    """The problem card under the planting guide: the AI tip is asked once per problem."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username='farmer', password='pass12345')
        farm = Farm.objects.create(user=self.user, name='Mine', barangay='Nanyo', latitude=7.3, longitude=125.68,
                                   area_hectares=1, ecosystem='irrigated_lowland')
        cycle = FarmCycle.objects.create(farm=farm, season='wet', year=2026, planting_date=date(2026, 6, 1))
        self.log = ProgressLog.objects.create(farm_cycle=cycle, log_date=date(2026, 7, 10), problem_key='black_bug',
                                              issue_type='pest', observation='Daghang itom nga tangaw')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        patcher = mock.patch('apps.ai.context.farmer_context', return_value='Crop at day 40.')
        patcher.start()
        self.addCleanup(patcher.stop)

    def explain(self, answer):
        with mock.patch(GEMINI, return_value=answer) as gemini:
            res = self.client.post('/api/advice/explain/', {'problem': 'black_bug', 'language': 'ceb',
                                                            'log': self.log.id}, format='json')
        return res.json(), gemini

    def test_the_tip_is_saved_on_the_log_and_reused(self):
        first, gemini = self.explain({'points': [{'text': 'Ihapa ang tangaw.', 'cards': ['C3']}]})
        self.assertTrue(first['ai_used'])
        self.assertIn('Daghang itom nga tangaw', gemini.call_args[0][1])   # the farmer's own words
        cache.clear()
        again, gemini = self.explain({'points': []})
        gemini.assert_not_called()
        self.assertEqual(again['points'][0]['text'], 'Ihapa ang tangaw.')
        self.log.refresh_from_db()
        self.assertEqual(self.log.advice_tip['problem'], 'black_bug')

    def test_a_failed_tip_is_not_saved(self):
        self.explain(None)
        self.log.refresh_from_db()
        self.assertIsNone(self.log.advice_tip)

    def test_another_farmers_log_is_ignored(self):
        other = User.objects.create_user(username='other', password='pass12345')
        self.client.force_authenticate(other)
        self.explain({'points': [{'text': 'Ihapa ang tangaw.', 'cards': ['C3']}]})
        self.log.refresh_from_db()
        self.assertIsNone(self.log.advice_tip)

    def test_okay_na_marks_the_problem_fixed_and_the_tip_cannot_be_written(self):
        res = self.client.patch(f'/api/progress/logs/{self.log.id}/',
                                {'resolved_at': '2026-07-12T08:00:00Z', 'advice_tip': {'fake': 1}}, format='json')
        self.assertEqual(res.status_code, 200)
        self.log.refresh_from_db()
        self.assertIsNotNone(self.log.resolved_at)
        self.assertIsNone(self.log.advice_tip)

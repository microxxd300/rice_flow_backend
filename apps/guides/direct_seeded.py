"""
The planting guides for farms that sow directly in the field: upland and rainfed lowland.

Upland follows "PalayCheck System for Upland Rice Farming" (PhilRice Rice Technology
Bulletin, 2nd edition). Rainfed lowland follows PhilRice's "Modified Dry Direct Seeding
Technology" bulletin (MDDST, by hand) and the best management practices for rainfed lowland
in "Mechanized Dry Direct Seeding using Multi-Purpose Seeder" (December 2022, MDDS). Pages
are the printed page numbers.

Day 0 is sowing. These booklets name growth stages more often than days, so some days are
estimates: seedlings are taken to emerge EMERGENCE_DAYS after sowing, and upland fertilizer
is placed at tillering and before panicle initiation. A validator must check these guides,
and a native speaker the Filipino and Bisaya text, before farmers rely on them. MDDST was
tried in Ilocos and Abra and MDDS in other regions, not in Davao. Herbicide products and
rates are left out on purpose: the farmer is sent to an agriculturist instead.
"""

import re

EMERGENCE_DAYS = 5
PI_BEFORE_HARVEST = 60

UPLAND = 'upland'
RAINFED = 'rainfed_lowland'

UP_REF = 'PalayCheck Upland, 2nd ed.'
UP_BOOK = 'upland'
MDDST_REF = 'PhilRice MDDST'
MDDST_BOOK = 'mddst'
MDDS_REF = 'PhilRice MDDS 2022'
MDDS_BOOK = 'mdds'
BOOKLET_VIEWER_URL = 'https://riceflow.me/booklet.html'

BOOKS = {
    UPLAND: 'PalayCheck System for Upland Rice Farming, 2nd edition (DA-PhilRice)',
    RAINFED: 'Modified Dry Direct Seeding Technology and Mechanized Dry Direct Seeding (DA-PhilRice)',
}

SOWING_KEYS = ('up_sow', 'rf_sow')
HARVEST_KEYS = ('up_harvest', 'rf_harvest')

# key, KeyCheck (None: not a KeyCheck guide), category, reference text, booklet
_UPLAND_STEPS = [
    ('up_seeds',   1, 'planting',        f'{UP_REF}, pp. 2-3',    UP_BOOK),
    ('up_land',    2, 'planting',        f'{UP_REF}, p. 4',       UP_BOOK),
    ('up_organic', 5, 'fertilizer',      f'{UP_REF}, p. 8',       UP_BOOK),
    ('up_sync',    3, 'planting',        f'{UP_REF}, p. 5',       UP_BOOK),
    ('up_sow',     4, 'planting',        f'{UP_REF}, pp. 6-7',    UP_BOOK),
    ('up_weed1',   7, 'pest_prevention', f'{UP_REF}, p. 13',      UP_BOOK),
    ('up_fert',    5, 'fertilizer',      f'{UP_REF}, p. 8',       UP_BOOK),
    ('up_stand',   4, 'planting',        f'{UP_REF}, p. 7',       UP_BOOK),
    ('up_weed2',   7, 'pest_prevention', f'{UP_REF}, p. 13',      UP_BOOK),
    ('up_water',   6, 'irrigation',      f'{UP_REF}, p. 9',       UP_BOOK),
    ('up_pests',   7, 'pest_prevention', f'{UP_REF}, pp. 10-14',  UP_BOOK),
    ('up_fertpi',  5, 'fertilizer',      f'{UP_REF}, p. 8',       UP_BOOK),
    ('up_harvest', 8, 'harvesting',      f'{UP_REF}, p. 15',      UP_BOOK),
    ('up_store',   8, 'harvesting',      f'{UP_REF}, pp. 15-16',  UP_BOOK),
]

_RAINFED_STEPS = [
    ('rf_seeds',   None, 'planting',        f'{MDDST_REF}, p. 6; {MDDS_REF}, p. 35',  MDDST_BOOK),
    ('rf_land',    None, 'planting',        f'{MDDST_REF}, p. 5; {MDDS_REF}, p. 35',  MDDST_BOOK),
    ('rf_basal',   None, 'fertilizer',      f'{MDDST_REF}, p. 6',                     MDDST_BOOK),
    ('rf_prep',    None, 'planting',        f'{MDDST_REF}, pp. 6-7',                  MDDST_BOOK),
    ('rf_sow',     None, 'planting',        f'{MDDST_REF}, pp. 4, 7',                 MDDST_BOOK),
    ('rf_water',   None, 'irrigation',      f'{MDDST_REF}, p. 8',                     MDDST_BOOK),
    ('rf_weeds',   None, 'pest_prevention', f'{MDDST_REF}, p. 8',                     MDDST_BOOK),
    ('rf_top',     None, 'fertilizer',      f'{MDDST_REF}, p. 9; {MDDS_REF}, p. 35',  MDDST_BOOK),
    ('rf_pests',   None, 'pest_prevention', f'{MDDST_REF}, p. 9',                     MDDST_BOOK),
    ('rf_lcc',     None, 'fertilizer',      f'{MDDST_REF}, p. 9; {MDDS_REF}, p. 35',  MDDST_BOOK),
    ('rf_drain',   None, 'irrigation',      f'{MDDS_REF}, p. 35',                     MDDS_BOOK),
    ('rf_harvest', None, 'harvesting',      f'{MDDST_REF}, p. 9',                     MDDST_BOOK),
]


def _page_url(book: str, reference: str) -> str:
    """The booklet opened at the pages cited first (riceflow.me shows one page at a time)."""
    cited = re.search(r'pp?\. ([\d, -]+)', reference.split(';')[0])
    pages = re.sub(r'[^0-9,-]', '', cited.group(1))
    return f'{BOOKLET_VIEWER_URL}?b={book}&pages={pages}'


REFERENCES = {key: (ref, _page_url(book, ref)) for key, _, _, ref, book in _UPLAND_STEPS + _RAINFED_STEPS}

# The GrowthStage each step belongs to (apps.progress.stages); prep steps have none
STEP_STAGE = {
    'up_sow': 1, 'rf_sow': 1,
    'up_weed1': 3, 'up_fert': 3, 'up_stand': 3, 'up_weed2': 3, 'up_water': 3, 'up_pests': 3,
    'rf_water': 3, 'rf_weeds': 3, 'rf_top': 3, 'rf_pests': 3, 'rf_lcc': 3,
    'up_fertpi': 4,
    'rf_drain': 8,
    'up_harvest': 9, 'rf_harvest': 9,
    'up_store': 10,
}


def _upland_days(maturity: int) -> dict:
    return {
        'up_seeds': -10, 'up_land': -7, 'up_organic': -5, 'up_sync': -3, 'up_sow': 0,
        'up_weed1': EMERGENCE_DAYS + 14, 'up_fert': 21, 'up_stand': 30, 'up_weed2': EMERGENCE_DAYS + 28,
        'up_water': 40, 'up_pests': 45, 'up_fertpi': maturity - PI_BEFORE_HARVEST - 6,
        'up_harvest': maturity, 'up_store': maturity + 1,
    }


def _rainfed_days(maturity: int) -> dict:
    return {
        'rf_seeds': -10, 'rf_land': -7, 'rf_basal': -2, 'rf_prep': -1, 'rf_sow': 0,
        'rf_water': 3, 'rf_weeds': 8, 'rf_top': EMERGENCE_DAYS + 20, 'rf_pests': 35, 'rf_lcc': 47,
        'rf_drain': maturity - 10, 'rf_harvest': maturity,
    }


def plan(maturity_days, ecosystem: str) -> list:
    """The guide steps for a direct-seeded farm, in order: [{key, key_check, category, day}, ...]."""
    maturity = int(maturity_days)
    if ecosystem == UPLAND:
        table, days = _UPLAND_STEPS, _upland_days(maturity)
    else:
        table, days = _RAINFED_STEPS, _rainfed_days(maturity)
    return sorted(
        ({'key': key, 'key_check': kc, 'category': cat, 'day': days[key]} for key, kc, cat, _, _ in table),
        key=lambda s: s['day'],
    )


# (title, instruction, explanation) per language
TEXT = {
    'up_seeds': {
        'en': ('Get good seeds of an upland variety',
               'Use clean, full seeds of a recommended upland variety. They should germinate at least 85%.',
               'Good seeds give fewer weeds, healthier seedlings, and 10-15% more yield.'),
        'fil': ('Kumuha ng magandang binhi para sa upland',
                'Gumamit ng malinis at punong binhi ng inirerekomendang upland na palay. Dapat tumubo ang '
                'hindi bababa sa 85%.',
                'Ang magandang binhi, mas kaunti ang damo, mas malusog ang punla, at 10-15% na mas malaki ang ani.'),
        'ceb': ('Pagkuha og maayong binhi para sa upland',
                'Gamit og limpyo ug puno nga binhi sa girekomendar nga upland nga humay. Kinahanglan moturok '
                'ang dili moubos sa 85%.',
                'Ang maayong binhi, gamay ang sagbot, himsog ang semilya, ug 10-15% mas dako ang ani.'),
    },
    'up_land': {
        'en': ('Prepare the land on time',
               'Plow or rotovate after the last harvest. On flat land, plow once and disc-harrow twice after '
               'the first rains, then make furrows 30-40 cm apart. On a slope, plow along the contour, '
               'harrow once, and plant hedgerows across the slope.',
               'Good preparation gives strong, even seedlings. Contour plowing and hedgerows keep the soil '
               'from washing away.'),
        'fil': ('Ihanda ang lupa sa tamang oras',
                'Araruhin o i-rotovate pagkatapos ng huling ani. Sa patag, araruhin nang isang beses at '
                'suyurin nang dalawang beses pagkatapos ng unang ulan, tapos gumawa ng tudling na 30-40 cm ang '
                'pagitan. Sa dalisdis, mag-araro paikot sa gilid ng burol, suyurin nang isang beses, at '
                'magtanim ng halamang harang pahalang sa dalisdis.',
                'Pag maayos ang lupa, malakas at pantay ang punla. Ang pag-araro paikot at halamang harang ay '
                'pumipigil sa pagguho ng lupa.'),
        'ceb': ('Andama ang yuta sa saktong oras',
                'Daroha o i-rotovate human sa katapusang ani. Sa patag, daroha kausa ug suyda kaduha human sa '
                'unang ulan, dayon paghimo og tudling nga 30-40 cm ang gilay-on. Sa bakilid, pagdaro paliko '
                'subay sa bungtod, suyda kausa, ug tanom og babag nga tanom tabok sa bakilid.',
                'Kung maayo ang yuta, lig-on ug patas ang semilya. Ang pagdaro paliko ug babag nga tanom '
                'mopugong sa pagkaguba sa yuta.'),
    },
    'up_organic': {
        'en': ('Add organic fertilizer after plowing',
               'Spread organic materials or fertilizer evenly after plowing. Base the amount on a soil test '
               'or on what worked before. For organic farming of traditional varieties, use about 1.5 t/ha of '
               'animal manure, or compost and green manure.',
               'Upland soil is often poor and acidic, so feeding it early helps the crop start well.'),
        'fil': ('Maglagay ng organikong abono pagkatapos mag-araro',
                'Ikalat nang pantay ang organikong materyal o abono pagkatapos mag-araro. Ibatay ang dami sa '
                'soil test o sa dating karanasan. Sa organikong tanim ng tradisyunal na palay, gumamit ng mga '
                '1.5 t/ha na dumi ng hayop, o compost at berdeng abono.',
                'Madalas mahina at maasim ang lupa sa upland, kaya nakakatulong ang maagang pag-abono.'),
        'ceb': ('Butangi og organikong abono human sa pagdaro',
                'Ikatag nga patas ang organikong materyal o abono human sa pagdaro. Ibase ang kadaghanon sa '
                'soil test o sa nakaraang kasinatian. Sa organikong tanom sa tradisyonal nga humay, gamit og '
                'mga 1.5 t/ha nga tae sa hayop, o compost ug berde nga abono.',
                'Kasagaran huyang ug aslom ang yuta sa upland, busa makatabang ang sayo nga pag-abono.'),
    },
    'up_sync': {
        'en': ('Plant when your neighbors plant',
               'Plan to sow within 14 days of most upland and lowland rice farms around you.',
               'When farms plant together, pests and diseases cannot keep moving from one crop to the next.'),
        'fil': ('Sumabay sa tanim ng mga kapitbahay',
                'Magplano na magtanim sa loob ng 14 araw kasabay ng karamihan sa mga katabing bukid.',
                'Pag sabay-sabay ang tanim, hindi makalipat-lipat ang peste at sakit.'),
        'ceb': ('Dungan sa tanom sa mga silingan',
                'Pagplano nga manom sulod sa 14 ka adlaw uban sa kadaghanan sa silingang uma.',
                'Kung dungan ang tanom, dili makabalhin-balhin ang peste ug sakit.'),
    },
    'up_sow': {
        'en': ('Sow the seeds directly',
               'Sow in furrows 25-30 cm apart, or dibble holes 25-30 cm apart with 5-7 seeds each, then lightly '
               'cover with soil. You may also broadcast and lightly harrow. Use 40-60 kg of seeds per hectare.',
               'Sowing in rows makes weeding and fertilizing easier and gives a better stand and yield.'),
        'fil': ('Itanim nang direkta ang binhi',
                'Maghasik sa tudling na 25-30 cm ang pagitan, o gumawa ng butas na 25-30 cm ang layo at '
                'maglagay ng 5-7 binhi bawat isa, tapos takpan nang bahagya ng lupa. Puwede ring magsabog at '
                'suyurin nang bahagya. Gumamit ng 40-60 kg na binhi bawat ektarya.',
                'Pag nakahanay ang tanim, mas madaling magdamo at mag-abono, at mas maganda ang ani.'),
        'ceb': ('Itanom direkta ang binhi',
                'Pugas sa tudling nga 25-30 cm ang gilay-on, o buhat og lungag nga 25-30 cm ang layo ug butangi '
                'og 5-7 ka binhi matag usa, dayon taboni og gamay nga yuta. Pwede pud isabwag ug suydon og '
                'gamay. Gamit og 40-60 kg nga binhi matag ektarya.',
                'Kung naka-linya ang tanom, sayon ang paghawan ug pag-abono, ug mas maayo ang ani.'),
    },
    'up_weed1': {
        'en': ('First weeding',
               'Cultivate between the rows and hand weed about 14 days after the seedlings come up. If you '
               'think you need a herbicide, ask your agriculturist first.',
               'Weeds are the main enemy of upland rice while it is young.'),
        'fil': ('Unang pagdadamo',
                'Magbungkal sa pagitan ng hanay at magbunot ng damo mga 14 araw pagkatapos tumubo ang punla. '
                'Kung sa tingin mo kailangan ng herbicide, magtanong muna sa agriculturist.',
                'Ang damo ang pangunahing kalaban ng upland na palay habang bata pa ito.'),
        'ceb': ('Unang paghawan',
                'Pagbungkal tali sa mga linya ug ibton ang sagbot mga 14 ka adlaw human moturok ang semilya. '
                'Kung sa imong hunahuna kinahanglan og herbicide, pangutana una sa agriculturist.',
                'Ang sagbot ang pangunang kaaway sa upland nga humay samtang bata pa.'),
    },
    'up_fert': {
        'en': ('Check the crop\'s nutrients at tillering',
               'Apply the right amount of fertilizer as the plants tiller, based on a soil test or what worked '
               'before. Ask your agriculturist for the rate that fits your soil.',
               'Plants need enough nutrients at tillering to form more panicles later.'),
        'fil': ('Tingnan ang sustansya sa pagsuloy',
                'Maglagay ng tamang dami ng abono habang nagsusuloy ang palay, batay sa soil test o dating '
                'karanasan. Magtanong sa agriculturist kung gaano karami ang bagay sa lupa mo.',
                'Kailangan ng sapat na sustansya sa pagsuloy para dumami ang uhay.'),
        'ceb': ('Susiha ang sustansya sa pagsaha',
                'Butangi og saktong kadaghanon sa abono samtang nagsaha ang humay, base sa soil test o '
                'nakaraang kasinatian. Pangutana sa agriculturist kung pila ang haom sa imong yuta.',
                'Kinahanglan og igo nga sustansya sa pagsaha aron modaghan ang uhay.'),
    },
    'up_stand': {
        'en': ('Count your healthy seedlings',
               'At 30 days after sowing, you should have at least 80 healthy seedlings per square meter '
               '(about 65 if sown in furrows).',
               'A good number of healthy plants now competes better against weeds and yields more.'),
        'fil': ('Bilangin ang malulusog na punla',
                'Sa ika-30 araw pagkatapos magtanim, dapat may hindi bababa sa 80 malusog na punla bawat metro '
                'kuwadrado (mga 65 kung sa tudling itinanim).',
                'Ang sapat na malusog na tanim ay mas kayang labanan ang damo at mas malaki ang ani.'),
        'ceb': ('Ihapa ang himsog nga semilya',
                'Sa ika-30 ka adlaw human sa tanom, kinahanglan naay dili moubos sa 80 ka himsog nga semilya '
                'matag metro kwadrado (mga 65 kung sa tudling gitanom).',
                'Ang igo nga himsog nga tanom mas makaya ang sagbot ug mas dako ang ani.'),
    },
    'up_weed2': {
        'en': ('Second weeding',
               'Cultivate and hand weed again about 28 days after the seedlings come up. Keep weeding until the '
               'leaves cover the ground, about 6-7 weeks after they come up.',
               'Once the leaves cover the ground, weeds get too little light to grow.'),
        'fil': ('Ikalawang pagdadamo',
                'Magbungkal at magbunot ulit mga 28 araw pagkatapos tumubo ang punla. Ituloy hanggang matakpan '
                'ng dahon ang lupa, mga 6-7 linggo pagkatapos tumubo.',
                'Pag natakpan na ng dahon ang lupa, kulang na sa araw ang damo para tumubo.'),
        'ceb': ('Ikaduhang paghawan',
                'Pagbungkal ug ibton pag-usab mga 28 ka adlaw human moturok ang semilya. Padayona hangtod '
                'matabonan sa dahon ang yuta, mga 6-7 ka semana human moturok.',
                'Kung natabonan na sa dahon ang yuta, kulang na sa adlaw ang sagbot aron motubo.'),
    },
    'up_water': {
        'en': ('Watch for too much or too little rain',
               'Check your plants. Rolling, drying leaves mean too little water. Stunted, discolored plants '
               'with few tillers can mean too much rain.',
               'Upland rice depends on rain, so seeing stress early lets you ask for help in time.'),
        'fil': ('Bantayan kung sobra o kulang ang ulan',
                'Tingnan ang tanim. Pag kumukulot at natutuyo ang dahon, kulang sa tubig. Pag bansot, '
                'iba ang kulay at kaunti ang suloy, baka sobra ang ulan.',
                'Ulan lang ang tubig ng upland, kaya mas maagang makahingi ng tulong pag napansin agad.'),
        'ceb': ('Bantayi kung sobra o kulang ang ulan',
                'Susiha ang tanom. Kung nagkulot ug nauga ang dahon, kulang sa tubig. Kung kubos, lahi ang '
                'kolor ug gamay ang saha, basin sobra ang ulan.',
                'Ulan ra ang tubig sa upland, busa sayo makapangayo og tabang kung mamatikdan dayon.'),
    },
    'up_pests': {
        'en': ('Check for pests, diseases, birds and rats',
               'Walk your field regularly and identify the problem correctly. Keep the field clean, and use '
               'pesticide only during an outbreak, after asking your agriculturist.',
               'Most pest problems can be managed early without spraying.'),
        'fil': ('Tingnan kung may peste, sakit, ibon at daga',
                'Libutin ang bukid nang madalas at alamin nang tama ang problema. Panatilihing malinis ang '
                'bukid, at gumamit lang ng pesticide kapag outbreak, pagkatapos magtanong sa agriculturist.',
                'Karamihan ng problema sa peste ay naaayos nang maaga kahit walang spray.'),
        'ceb': ('Susiha kung naay peste, sakit, langgam ug ilaga',
                'Libota ang uma kanunay ug ilha og tarong ang problema. Hinloi ang uma, ug gamit lang og '
                'pesticide kung outbreak, human mangutana sa agriculturist.',
                'Kadaghanan sa problema sa peste masulbad og sayo bisan walay spray.'),
    },
    'up_fertpi': {
        'en': ('Feed the crop before panicles form',
               'Make sure the crop has enough nutrients before panicle initiation and flowering. Ask your '
               'agriculturist for the right rate.',
               'Nutrients at this time decide how many grains each panicle fills.'),
        'fil': ('Abonohan bago lumabas ang uhay',
                'Siguraduhing may sapat na sustansya ang palay bago mag-uhay at mamulaklak. Magtanong sa '
                'agriculturist kung gaano karami.',
                'Ang sustansya sa panahong ito ang nagpapasya kung ilang butil ang mapupuno.'),
        'ceb': ('Abonohi sa dili pa mogawas ang uhay',
                'Siguroha nga igo ang sustansya sa humay sa dili pa mag-uhay ug mobulak. Pangutana sa '
                'agriculturist kung pila.',
                'Ang sustansya niining panahona maoy magbuot kung pila ka lugas ang mapuno.'),
    },
    'up_harvest': {
        'en': ('Harvest at the right time',
               'Harvest when at least 85% of the grains are mature. Thresh within 1-2 days, or keep the panicles '
               'in bundles for sun drying and threshing.',
               'Harvesting too early gives half-filled grains. Too late, and grains shatter and break in milling.'),
        'fil': ('Mag-ani sa tamang oras',
                'Mag-ani kapag hinog na ang hindi bababa sa 85% ng butil. Giikin sa loob ng 1-2 araw, o itali '
                'ang uhay para ibilad at giikin.',
                'Pag masyadong maaga, kulang ang laman ng butil. Pag huli, nalalaglag at nababasag ang butil.'),
        'ceb': ('Pag-ani sa saktong oras',
                'Pag-ani kung hinog na ang dili moubos sa 85% sa lugas. Giika sulod sa 1-2 ka adlaw, o ihigot '
                'ang uhay aron ibilad ug giikon.',
                'Kung sayo kaayo, kulang ang sulod sa lugas. Kung ulahi, mahulog ug mabuak ang lugas.'),
    },
    'up_store': {
        'en': ('Dry and store the grains',
               'Dry to 14% moisture for milling and 12% for seed. Store in clean, airtight, cool, dry and '
               'rat-proof containers.',
               'Airtight storage controls insects without chemicals and keeps seeds able to grow for 6-8 months.'),
        'fil': ('Patuyuin at itabi ang butil',
                'Patuyuin hanggang 14% moisture para sa pagkiskis at 12% para sa binhi. Itabi sa malinis, '
                'hindi pinapasukan ng hangin, malamig, tuyo at hindi nadadaga na lalagyan.',
                'Ang airtight na imbakan ay kontrol sa insekto nang walang kemikal at tumutubo pa ang binhi '
                'hanggang 6-8 buwan.'),
        'ceb': ('Pauga ug tipigi ang lugas',
                'Pauga hangtod 14% moisture para sa galingan ug 12% para sa binhi. Tipigi sa limpyo, way '
                'kasudlan sa hangin, bugnaw, uga ug dili maabot sa ilaga nga sudlanan.',
                'Ang airtight nga tipiganan makakontrol sa insekto nga walay kemikal ug moturok pa ang binhi '
                'hangtod 6-8 ka bulan.'),
    },

    'rf_seeds': {
        'en': ('Get seeds of a rainfed variety',
               'Use a Sahod-Ulan variety or one recommended by DA-PhilRice, DA-RFO or your LGU. Prepare 60-80 kg '
               'of certified seeds per hectare. Wash them and remove the seeds that float.',
               'Rainfed varieties cope better with dry spells. Floating seeds are unfilled and will not grow well.'),
        'fil': ('Kumuha ng binhi para sa sahod-ulan',
                'Gumamit ng Sahod-Ulan na palay o inirerekomenda ng DA-PhilRice, DA-RFO o LGU. Maghanda ng '
                '60-80 kg na certified na binhi bawat ektarya. Hugasan at alisin ang lumulutang.',
                'Mas kaya ng sahod-ulan na palay ang tagtuyot. Walang laman ang lumulutang na binhi.'),
        'ceb': ('Pagkuha og binhi para sa sahod-ulan',
                'Gamit og Sahod-Ulan nga humay o girekomendar sa DA-PhilRice, DA-RFO o LGU. Andam og 60-80 kg '
                'nga certified nga binhi matag ektarya. Hugasi ug kuhaa ang molutaw.',
                'Mas makaya sa sahod-ulan nga humay ang hulaw. Walay sulod ang molutaw nga binhi.'),
    },
    'rf_land': {
        'en': ('Prepare the land well',
               'Plow once or twice and harrow 2-3 times until the soil is fine, level, and free of weeds and '
               'stubble. To test it, squeeze some soil in your palm. If it does not stick together, it is ready.',
               'Fine soil helps seeds germinate, and sun exposes and dries weed seeds.'),
        'fil': ('Ihanda nang mabuti ang lupa',
                'Araruhin nang isa o dalawang beses at suyurin nang 2-3 beses hanggang pino, patag at walang '
                'damo at tuod. Para masubukan, pisilin ang lupa sa palad. Kung hindi dumidikit, handa na.',
                'Nakakatulong ang pinong lupa sa pagtubo, at natutuyo ng araw ang buto ng damo.'),
        'ceb': ('Andama og maayo ang yuta',
                'Daroha kausa o kaduha ug suyda 2-3 ka beses hangtod pino, patag ug walay sagbot ug tuod. Aron '
                'masulayan, pislita ang yuta sa palad. Kung dili modikit, andam na.',
                'Makatabang ang pino nga yuta sa pagturok, ug mauga sa adlaw ang liso sa sagbot.'),
    },
    'rf_basal': {
        'en': ('Add basal fertilizer',
               'During the last harrowing, mix in fertilizer based on a soil test. With no soil test, use 10 sacks '
               'of organic fertilizer (50 kg each) and 3-4 bags of 14-14-14 per hectare, then cover it.',
               'This feeds the plants in their first weeks. Covering it keeps nutrients from being lost.'),
        'fil': ('Maglagay ng basal na abono',
                'Sa huling pagsusuyod, ihalo ang abono batay sa soil test. Kung walang soil test, gumamit ng 10 '
                'sako ng organikong abono (50 kg bawat isa) at 3-4 bag ng 14-14-14 bawat ektarya, tapos takpan.',
                'Ito ang pagkain ng palay sa unang mga linggo. Pag tinakpan, hindi nasasayang ang sustansya.'),
        'ceb': ('Butangi og basal nga abono',
                'Sa katapusang pagsuyod, isagol ang abono base sa soil test. Kung walay soil test, gamit og 10 '
                'ka sako nga organikong abono (50 kg matag usa) ug 3-4 ka bag nga 14-14-14 matag ektarya, dayon '
                'taboni.',
                'Mao ni ang pagkaon sa humay sa unang mga semana. Kung taboni, dili mausik ang sustansya.'),
    },
    'rf_prep': {
        'en': ('Make furrows and pre-germinate the seeds',
               'Make furrows 20 cm apart with a lithao or a plow without the moldboard. Soak the seeds 8-12 hours, '
               'then incubate 8-12 hours until a small white tip shows.',
               'Pre-germinated seeds come up faster and stand a better chance against weeds.'),
        'fil': ('Gumawa ng tudling at patubuin ang binhi',
                'Gumawa ng tudling na 20 cm ang pagitan gamit ang lithao o araro na walang moldboard. Ibabad ang '
                'binhi nang 8-12 oras, tapos i-incubate nang 8-12 oras hanggang may maliit na puting dulo.',
                'Mas mabilis tumubo ang pinatubong binhi at mas kaya ang damo.'),
        'ceb': ('Paghimo og tudling ug paturoka ang binhi',
                'Paghimo og tudling nga 20 cm ang gilay-on gamit ang lithao o daro nga walay moldboard. Ibabad '
                'ang binhi 8-12 ka oras, dayon i-incubate 8-12 ka oras hangtod naay gamay nga puti nga tumoy.',
                'Mas paspas moturok ang napaturok nga binhi ug mas makaya ang sagbot.'),
    },
    'rf_sow': {
        'en': ('Sow when the soil is moist',
               'Sow right after making furrows, early morning or late afternoon, when the top 25-30 cm of soil is '
               'moist. Broadcast evenly and cover with a wooden plank. If rain cannot be predicted and the soil '
               'is dry, dry seeds can be sown over the furrows.',
               'Sowing on moist soil lets you plant on time without waiting for enough rain to transplant.'),
        'fil': ('Magtanim kapag basa ang lupa',
                'Maghasik agad pagkagawa ng tudling, maaga o hapon, kapag basa ang itaas na 25-30 cm ng lupa. '
                'Isabog nang pantay at takpan gamit ang tablang kahoy. Kung hindi mahulaan ang ulan at tuyo ang '
                'lupa, puwedeng ihasik ang tuyong binhi sa tudling.',
                'Sa basang lupa, makakatanim sa oras nang hindi naghihintay ng maraming ulan para maglipat-tanim.'),
        'ceb': ('Pugas kung basa ang yuta',
                'Pugas dayon human sa tudling, sayo sa buntag o hapon, kung basa ang ibabaw nga 25-30 cm sa yuta. '
                'Isabwag nga patas ug taboni gamit ang tabla. Kung dili matag-an ang ulan ug uga ang yuta, pwede '
                'ipugas ang uga nga binhi sa tudling.',
                'Sa basa nga yuta, makatanom sa oras bisan dili maghulat og daghang ulan para magbalhin-tanom.'),
    },
    'rf_water': {
        'en': ('Trap the rainwater',
               'Fix the dikes and water outlets so the field holds all the rain it can.',
               'Your field only gets water from rain, and standing water also helps control weeds.'),
        'fil': ('Ipunin ang tubig-ulan',
                'Ayusin ang pilapil at labasan ng tubig para maipon ang lahat ng ulan.',
                'Ulan lang ang tubig ng bukid mo, at nakakatulong din ang nakatigil na tubig laban sa damo.'),
        'ceb': ('Tigumi ang tubig-ulan',
                'Ayuha ang pilapil ug gawasan sa tubig aron matigom ang tanang ulan.',
                'Ulan ra ang tubig sa imong uma, ug makatabang pud ang tubig batok sa sagbot.'),
    },
    'rf_weeds': {
        'en': ('Control weeds early',
               'Weeds are the main problem in direct-seeded fields. Pull them by spot weeding and keep water in '
               'the field when you can. If you think you need a herbicide, ask your agriculturist first.',
               'Rice and weeds come up together, so the first weeks decide who wins.'),
        'fil': ('Kontrolin agad ang damo',
                'Ang damo ang pangunahing problema sa direktang tanim. Bunutin ito at panatilihin ang tubig sa '
                'bukid kung kaya. Kung sa tingin mo kailangan ng herbicide, magtanong muna sa agriculturist.',
                'Sabay tumutubo ang palay at damo, kaya mahalaga ang unang mga linggo.'),
        'ceb': ('Kontrola dayon ang sagbot',
                'Ang sagbot ang pangunang problema sa direkta nga tanom. Ibton kini ug hupti ang tubig sa uma '
                'kung kaya. Kung sa imong hunahuna kinahanglan og herbicide, pangutana una sa agriculturist.',
                'Dungan moturok ang humay ug sagbot, busa importante ang unang mga semana.'),
    },
    'rf_top': {
        'en': ('Topdress the crop',
               'Apply 2 bags of urea per hectare, 15-25 days after the seedlings come up. Rice Crop Manager or '
               'your DA office can give a rate for your farm.',
               'Young plants use a lot of nitrogen to grow leaves and tillers.'),
        'fil': ('Mag-abono ulit',
                'Maglagay ng 2 bag ng urea bawat ektarya, 15-25 araw pagkatapos tumubo ang punla. Puwedeng '
                'magbigay ng tamang dami ang Rice Crop Manager o DA office.',
                'Malakas gumamit ng nitrogen ang batang palay para sa dahon at suloy.'),
        'ceb': ('Pag-abono pag-usab',
                'Butangi og 2 ka bag nga urea matag ektarya, 15-25 ka adlaw human moturok ang semilya. Makahatag '
                'og saktong kadaghanon ang Rice Crop Manager o DA office.',
                'Kusog mogamit og nitrogen ang bata nga humay para sa dahon ug saha.'),
    },
    'rf_pests': {
        'en': ('Check for pests',
               'Monitor your field regularly and use integrated pest management. Plant at the same time as your '
               'community, and use pesticide carefully, after asking your agriculturist.',
               'Careful spraying protects the insects that eat pests.'),
        'fil': ('Tingnan kung may peste',
                'Bantayan ang bukid nang madalas at gamitin ang integrated pest management. Sumabay sa tanim ng '
                'komunidad, at mag-ingat sa pesticide, pagkatapos magtanong sa agriculturist.',
                'Pag maingat sa pag-spray, ligtas ang mga insektong kumakain ng peste.'),
        'ceb': ('Susiha kung naay peste',
                'Bantayi ang uma kanunay ug gamita ang integrated pest management. Dungan sa tanom sa komunidad, '
                'ug pag-amping sa pesticide, human mangutana sa agriculturist.',
                'Kung amping sa pag-spray, luwas ang mga insekto nga mokaon sa peste.'),
    },
    'rf_lcc': {
        'en': ('Check if the crop needs more nitrogen',
               'Use a Leaf Color Chart, about 45-50 days after sowing, to decide if the crop needs more nitrogen.',
               'The chart helps you add nitrogen only when the crop needs it.'),
        'fil': ('Tingnan kung kailangan pa ng nitrogen',
                'Gumamit ng Leaf Color Chart, mga 45-50 araw pagkatapos magtanim, para malaman kung kailangan '
                'pa ng nitrogen.',
                'Sa chart, nakakapag-abono lang kapag kailangan.'),
        'ceb': ('Susiha kung kinahanglan pa og nitrogen',
                'Gamit og Leaf Color Chart, mga 45-50 ka adlaw human sa tanom, aron mahibal-an kung kinahanglan '
                'pa og nitrogen.',
                'Sa chart, makaabono lang kung kinahanglan.'),
    },
    'rf_drain': {
        'en': ('Drain the field before harvest',
               'Drain any water from the field 1-2 weeks before the expected harvest.',
               'A drier field ripens evenly and is easier to harvest.'),
        'fil': ('Patuyuin ang bukid bago mag-ani',
                'Palabasin ang tubig sa bukid 1-2 linggo bago ang inaasahang ani.',
                'Mas pantay ang hinog at mas madaling anihin ang tuyong bukid.'),
        'ceb': ('Pauga ang uma sa dili pa mag-ani',
                'Pagawsa ang tubig sa uma 1-2 ka semana sa dili pa ang gidahom nga ani.',
                'Mas patas ang hinog ug sayon anihon ang uga nga uma.'),
    },
    'rf_harvest': {
        'en': ('Harvest at the right time',
               'Harvest when 80% of the grains in the panicles have turned golden yellow.',
               'Harvesting at this point gives the most full, unbroken grains.'),
        'fil': ('Mag-ani sa tamang oras',
                'Mag-ani kapag 80% ng butil sa uhay ay kulay ginintuang dilaw na.',
                'Sa ganitong oras, pinakamarami ang punong butil na hindi nababasag.'),
        'ceb': ('Pag-ani sa saktong oras',
                'Pag-ani kung 80% sa lugas sa uhay bulawanon na ang kolor.',
                'Niining orasa, labing daghan ang puno nga lugas nga dili mabuak.'),
    },
}

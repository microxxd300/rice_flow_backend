"""
The planting guide: PalayCheck System for Irrigated Lowland Rice, 2022 Revised Edition
(DA-PhilRice), summarized as one step at a time. Transplanted rice (TPR), the usual method
in Panabo.

Timeline: day 0 = sowing in the seedbed, the same start the farm cycle uses; harvest is the
variety's maturity day (NSIC maturity counts from sowing). Pages are the book's printed page
numbers. Summaries are short; the farmer can open the book at the page for the full detail.

The English summaries keep PalayCheck's numbers. The Filipino and Bisaya text, and the
"explain" text in all three languages, should be checked once by a native speaker and the
validator before the defense.
"""

import re
from . import direct_seeded

REFERENCE = 'PalayCheck System 2022 Revised Edition (DA-PhilRice)'
REFERENCE_URL = 'https://www.philrice.gov.ph/wp-content/uploads/2023/02/PalayCheck-System-2022-Revised-Edition.pdf'
BOOKLET_VIEWER_URL = 'https://riceflow.me/booklet.html'

SEEDLING_AGE_DAYS = 21          # transplanted at 18-21 days (p. 27); the cycle counts from sowing
PI_BEFORE_HARVEST = 60          # panicle initiation about 60 days before harvest
FLOWERING_BEFORE_HARVEST = 30
PREP_DAYS = 10                  # seed and land preparation start 10 days before sowing

LANGUAGES = ('en', 'fil', 'ceb')

# key, KeyCheck, category (the app's icon/colour group), pages
STEPS = [
    ('seeds',       1, 'planting',        '14-15'),
    ('plow',        3, 'planting',        '18, 22'),
    ('seedbed',     4, 'planting',        '27-28'),
    ('leveling',    2, 'planting',        '17'),
    ('transplant',  4, 'planting',        '27-28'),
    ('replant',     4, 'planting',        '28'),
    ('fertilizer1', 5, 'fertilizer',      '35-38'),
    ('lcc',         5, 'fertilizer',      '35'),
    ('water',       6, 'irrigation',      '44-45, 51'),
    ('weeds',       7, 'pest_prevention', '49, 51'),
    ('pests',       7, 'pest_prevention', '48-51'),
    ('fertilizer2', 5, 'fertilizer',      '36'),     # only for varieties maturing in more than 110 days
    ('fertilizerpi', 5, 'fertilizer',     '36'),
    ('flowering',   6, 'irrigation',      '44'),
    ('drain',       6, 'irrigation',      '44, 54'),
    ('harvest',     8, 'harvesting',      '53-55'),
    ('drystore',    9, 'harvesting',      '57-59'),
]
PAGES = {key: pages for key, _, _, pages in STEPS}


def _days(maturity: int) -> dict:
    """Day of each step, counted from sowing, for a variety that matures in `maturity` days."""
    tp = SEEDLING_AGE_DAYS
    pi_fert = maturity - PI_BEFORE_HARVEST - 6            # 5-7 days before panicle initiation
    first_fert = tp + 7                                    # within 0-14 days after transplanting
    return {
        'seeds': -PREP_DAYS, 'plow': -7, 'seedbed': 0, 'leveling': tp - 2, 'transplant': tp,
        'replant': tp + 5, 'fertilizer1': first_fert, 'lcc': tp + 14, 'water': tp + 15,
        'weeds': tp + 19, 'pests': tp + 23,
        'fertilizer2': (first_fert + pi_fert) // 2,        # mid-tillering
        'fertilizerpi': pi_fert,
        'flowering': maturity - FLOWERING_BEFORE_HARVEST,
        'drain': maturity - 12, 'harvest': maturity, 'drystore': maturity + 1,
    }


def plan(maturity_days, ecosystem=None) -> list:
    """The guide steps for a variety on this kind of farm, in order: [{key, key_check, category,
    day, ...}, ...]. Upland and rainfed farms sow directly and follow their own booklets."""
    if ecosystem in direct_seeded.BOOKS:
        steps = direct_seeded.plan(maturity_days, ecosystem)
        if ecosystem == direct_seeded.RAINFED:      # drying and storing are the same as irrigated
            steps.append({'key': 'drystore', 'key_check': 9, 'category': 'harvesting',
                          'day': int(maturity_days) + 1})
        return steps
    maturity = int(maturity_days)
    days = _days(maturity)
    steps = [
        {'key': key, 'key_check': kc, 'category': cat, 'pages': pages, 'day': days[key]}
        for key, kc, cat, pages in STEPS
        if key != 'fertilizer2' or maturity > 110
    ]
    return sorted(steps, key=lambda s: s['day'])


def text(key: str, language: str) -> dict:
    """{'title', 'instruction', 'explanation'} of a step in the farmer's language."""
    entry = TEXT[key]
    title, instruction, explanation = entry.get(language) or entry['en']
    return {'title': title, 'instruction': instruction, 'explanation': explanation}


def reference(pages: str) -> str:
    return f'PalayCheck 2022, p. {pages}' if '-' not in pages and ',' not in pages else f'PalayCheck 2022, pp. {pages}'


def reference_for(key: str) -> str:
    """Where a step comes from, for the farmer: book and page."""
    if key in direct_seeded.REFERENCES:
        return direct_seeded.REFERENCES[key][0]
    return reference(PAGES[key])


def palaycheck_page_url(pages: str) -> str:
    """The booklet opened at the cited pages (riceflow.me shows one page at a time)."""
    cited = re.sub(r'[^0-9,-]', '', pages or '')
    return f'{BOOKLET_VIEWER_URL}?b=palaycheck&pages={cited}' if cited else REFERENCE_URL


def reference_url_for(key: str) -> str:
    if key in direct_seeded.REFERENCES:
        return direct_seeded.REFERENCES[key][1]
    return palaycheck_page_url(PAGES[key])


def book_title(ecosystem) -> str:
    return direct_seeded.BOOKS.get(ecosystem, REFERENCE)


# (title, instruction, explanation) per language
TEXT = {
    'seeds': {
        'en': ('Get certified seeds of a recommended variety',
               'Buy seeds with a valid BPI-NSQCS certified-seed tag, preferably from an accredited seed '
               'grower. Choose a variety that suits your field (irrigated or rainfed) and the season. '
               'If you use old or saved seeds, test that they still germinate before sowing.',
               'Good seeds grow into strong, even plants and a bigger harvest. The tag shows the seeds '
               'were checked by the government. A variety made for your kind of field and season copes '
               'better with the floods or dry spells that season brings.'),
        'fil': ('Bumili ng certified na binhi',
                'Bumili ng binhi na may BPI-NSQCS certified-seed tag, mas okay kung galing sa accredited seed '
                'grower. Piliin ang klase ng palay na bagay sa bukid mo (may patubig o sahod-ulan) at sa '
                'panahon. Kung luma o tinabing binhi ang gamit mo, subukan muna kung tutubo pa bago magpunla.',
                'Ang magandang binhi, matibay at pantay ang tubo, at mas malaki ang ani. Ang tag ang patunay na'
                ' tsinek ng gobyerno ang binhi. Ang palay na para sa klase ng bukid mo at sa panahon ay mas '
                'kaya ang baha o tagtuyot.'),
        'ceb': ('Palit og certified nga binhi',
                'Palit og binhi nga naay BPI-NSQCS certified-seed tag, mas maayo kung gikan sa accredited seed '
                'grower. Pili og klase sa humay nga haom sa imong uma (naay patubig o sahod-ulan) ug sa '
                'panahon. Kung daan o gitipigan nga binhi ang gamiton, sulayi sa una kung moturok pa ba sa dili'
                ' pa magpugas.',
                'Ang maayong binhi, lig-on ug patas ang tubo, ug mas dako ang ani. Ang tag pamatuod nga '
                'gi-check sa gobyerno ang binhi. Ang humay nga para sa imong klase sa uma ug panahon mas makaya'
                ' sa baha o hulaw.'),
    },
    'plow': {
        'en': ('Rest the field, then plow',
               'Let the field rest for at least 30 days after the last harvest. Plow or rotovate 21-30 days '
               'before transplanting, then harrow every 7 days. Plant within 14 days of the regular planting '
               'schedule of the farms around you.',
               'Resting and plowing early lets weeds, straw and stubble rot, so the soil becomes soft and '
               'clean. When nearby farms plant at about the same time, pests cannot keep moving from one '
               'field to the next all season.'),
        'fil': ('Ipahinga ang bukid, tapos araruhin',
                'Pahingahin ang bukid nang 30 araw man lang pagkatapos ng huling ani. Araruhin o i-rotovate '
                '21-30 araw bago maglipat-tanim, tapos suyurin kada 7 araw. Sumabay sa tanim ng mga katabing '
                'bukid (hindi lalayo ng 14 araw).',
                'Pag pinahinga at inararo nang maaga, nabubulok ang damo, dayami at tuod, kaya lumalambot at '
                'lumilinis ang lupa. Pag sabay-sabay nagtanim ang magkakatabing bukid, hindi makalipat-lipat '
                'ang peste buong season.'),
        'ceb': ('Papahulaya ang uma, dayon daroha',
                'Papahulaya ang uma bisan 30 ka adlaw human sa katapusang ani. Daroha o i-rotovate 21-30 ka '
                'adlaw sa dili pa magbalhin-tanom, dayon suyda kada 7 ka adlaw. Dungan sa tanom sa mga '
                'silingang uma (dili molapas og 14 ka adlaw).',
                'Kung gipahulay ug sayo nga gidaro, madunot ang sagbot, dagami ug tuod, mao nga mohumok ug '
                'molimpyo ang yuta. Kung dungan mananom ang magsilingang uma, dili makabalhin-balhin ang peste '
                'sa tibuok season.'),
    },
    'seedbed': {
        'en': ('Prepare the seedbed and sow',
               'Sow 20-40 kg of seeds per hectare on a 400 m2 seedbed. On fine-textured soil, mix in 3-4 bags '
               'of commercial organic fertilizer before leveling the seedbed. Protect the young seedlings '
               'from golden apple snails.',
               'Sowing the right amount of seed gives strong seedlings that are not crowded. Loose, rich '
               'soil makes pulling the seedlings easier, with less damage to the roots.'),
        'fil': ('Ihanda ang punlaan at magpunla',
                'Magpunla ng 20-40 kg na binhi kada ektarya sa 400 m2 na punlaan. Kung pino o malagkit ang '
                'lupa, haluan ng 3-4 sako ng organic fertilizer bago patagin ang punlaan. Bantayan ang batang '
                'punla sa kuhol (golden apple snail).',
                'Pag tama ang dami ng binhi, matibay ang punla at hindi siksikan. Pag malambot at mataba ang '
                'lupa, madaling bunutin ang punla at hindi nasisira ang ugat.'),
        'ceb': ('Andama ang punlaan ug pugas',
                'Pugas og 20-40 kg nga binhi kada ektarya sa 400 m2 nga punlaan. Kung pino o pilit ang yuta, '
                'sagoli og 3-4 ka sako nga organic fertilizer sa dili pa patag-on ang punlaan. Bantayi ang '
                'batan-ong semilya sa kuhol (golden apple snail).',
                'Kung sakto ang gidaghanon sa binhi, lig-on ang semilya ug dili dasok. Kung humok ug tambok ang'
                ' yuta, sayon bunlotan ang semilya ug dili madaot ang gamot.'),
    },
    'leveling': {
        'en': ('Level the field',
               'Puddle and level the field well. After final leveling, no spot should have water deeper '
               'than 5 cm (about a thumb length), and no mound of soil should show above the water.',
               'In a level field, water, fertilizer and weed control reach every part evenly, so the whole '
               'crop grows and ripens together. A poorly prepared field can yield 5% less.'),
        'fil': ('Patagin ang bukid',
                'Putikin at patagin nang maayos ang bukid. Pagkatapos, dapat walang parte na lampas 5 cm ang '
                'lalim ng tubig (mga isang hinlalaki), at walang lupang nakausli sa tubig.',
                'Pag patag ang bukid, pantay ang abot ng tubig, abono at pang-kontrol ng damo, kaya sabay-sabay'
                ' lumalaki at nahihinog ang palay. Pag hindi maayos ang paghanda, puwedeng bumaba ng 5% ang '
                'ani.'),
        'ceb': ('Patag-a ang uma',
                'Lapoka ug patag-a og maayo ang uma. Human niini, wala dapay bahin nga lapas 5 cm ang lawom sa '
                'tubig (mga usa ka kumagko), ug walay yuta nga mogawas sa tubig.',
                'Kung patag ang uma, patas ang abot sa tubig, abono ug pang-kontrol sa sagbot, mao nga dungan '
                'motubo ug mohinog ang humay. Kung dili maayo ang pag-andam, mahimong mokunhod og 5% ang ani.'),
    },
    'transplant': {
        'en': ('Transplant the seedlings',
               'Transplant 18-21-day-old seedlings, 2-3 per hill. Space the hills 20 x 20 cm in the wet season '
               'or 20 x 15 cm in the dry season. Do not cut the leaves of the seedlings before transplanting.',
               'Seedlings older than 25 days recover poorly from transplanting and make fewer tillers. Cut '
               'leaves are an entry point for diseases.'),
        'fil': ('Ilipat-tanim ang punla',
                'Itanim ang punlang 18-21 araw na, 2-3 punla kada butas. 20 x 20 cm ang pagitan pag tag-ulan, '
                '20 x 15 cm pag tag-init. Huwag putulan ang dahon ng punla bago itanim.',
                'Ang punlang lampas 25 araw, hirap makabawi pagkalipat at kaunti ang suwi. Ang pinutulang dahon'
                ' ay madaling pasukin ng sakit.'),
        'ceb': ('Ibalhin-tanom ang semilya',
                'Itanom ang semilya nga 18-21 ka adlaw na, 2-3 ka semilya kada buho. 20 x 20 cm ang gilay-on '
                'kung ting-ulan, 20 x 15 cm kung ting-init. Ayaw putla ang dahon sa semilya sa dili pa itanom.',
                'Ang semilya nga lapas 25 ka adlaw, lisod makabawi pagkabalhin ug gamay ra ang saha. Ang '
                'giputlan nga dahon dali sudlan sa sakit.'),
    },
    'replant': {
        'en': ('Replant missing hills',
               'Within 7 days after transplanting, replant missing hills using seedlings from the same seedbed.',
               'Filling the gaps early keeps enough plants in the field. Seedlings from the same seedbed keep '
               'the whole crop ripening at the same time.'),
        'fil': ('Tamnan ang mga butas na walang tanim',
                'Sa loob ng 7 araw pagkatapos maglipat-tanim, tamnan ang mga bakanteng butas gamit ang punla '
                'galing sa parehong punlaan.',
                'Pag napunan agad ang mga bakante, sapat ang tanim sa bukid. Pag galing sa parehong punlaan, '
                'sabay-sabay pa rin mahihinog ang palay.'),
        'ceb': ('Tamni ang mga buho nga walay tanom',
                'Sulod sa 7 ka adlaw human sa pagbalhin-tanom, tamni ang mga bakante nga buho gamit ang semilya'
                ' gikan sa parehas nga punlaan.',
                'Kung mapunan dayon ang mga bakante, igo ang tanom sa uma. Kung gikan sa parehas nga punlaan, '
                'dungan gihapon mohinog ang humay.'),
    },
    'fertilizer1': {
        'en': ('First fertilizer application',
               'Apply the first fertilizer between 0 and 14 days after transplanting. Base the amounts of N, P and K on a recommendation from the LCC App, RCMAS, NOPT or MOET.',
               'Young plants need nutrients early to make many tillers. These tools show what your field really needs, so you do not pay for fertilizer it does not need.'),
        'fil': ('Unang abono',
                'Mag-abono sa loob ng 0-14 araw pagkatapos maglipat-tanim. Ibase ang dami ng N, P at K sa payo ng LCC App, RCMAS, NOPT o MOET.',
                'Kailangan ng batang palay ang sustansya nang maaga para dumami ang suwi. Ipinapakita ng mga ito kung ano talaga ang kailangan ng bukid mo, kaya hindi ka gagastos sa abonong hindi kailangan.'),
        'ceb': ('Unang abono',
                'Pag-abono sulod sa 0-14 ka adlaw human sa pagbalhin-tanom. Ibase ang gidaghanon sa N, P ug K sa tambag sa LCC App, RCMAS, NOPT o MOET.',
                'Kinahanglan sa batan-ong humay ang sustansya sa sayo aron modaghan ang saha. Ipakita niini kung unsa gyud ang kinahanglan sa imong uma, busa dili ka mogasto sa abono nga dili kinahanglan.'),
    },
    'lcc': {
        'en': ('Check the leaf color every 7 days',
               'From 14 days after transplanting until early flowering, compare the leaves with a Leaf Color '
               'Chart (LCC) or the LCC App every 7 days to see if the crop needs more nitrogen.',
               'Pale leaves mean the plant needs nitrogen. Checking the color keeps you from applying too '
               'little or too much.'),
        'fil': ('Tingnan ang kulay ng dahon kada 7 araw',
                'Mula 14 araw pagkatapos maglipat-tanim hanggang magsimulang mamulaklak, ikumpara ang dahon sa '
                'Leaf Color Chart (LCC) o sa LCC App kada 7 araw, para malaman kung kailangan pa ng nitrogen.',
                'Pag maputla ang dahon, kailangan ng nitrogen. Pag tsinek mo ang kulay, hindi ka kukulangin o '
                'sosobra sa abono.'),
        'ceb': ('Tan-awa ang kolor sa dahon kada 7 ka adlaw',
                'Gikan 14 ka adlaw human sa pagbalhin-tanom hangtod mosugod og pamulak, itandi ang dahon sa '
                'Leaf Color Chart (LCC) o sa LCC App kada 7 ka adlaw, aron mahibal-an kung kinahanglan pa og '
                'nitrogen.',
                'Kung luspad ang dahon, kinahanglan og nitrogen. Kung imong i-check ang kolor, dili ka '
                'makulangan o masobrahan sa abono.'),
    },
    'water': {
        'en': ('Manage the water',
               'Keep the field saturated up to 15 days after transplanting. From early tillering, keep 3-5 cm of water at each irrigation. If water is scarce, practice Alternate Wetting and Drying (AWD) with an observation well.',
               'Too much water and too little water both stress the rice and cut the yield. When water is scarce, AWD is the controlled way to irrigate.'),
        'fil': ('Bantayan ang tubig',
                'Panatilihing basang-basa ang bukid hanggang 15 araw pagkatapos maglipat-tanim. Pagsimula ng pagsuwi, 3-5 cm na tubig kada patubig. Kung kulang ang tubig, gamitin ang AWD (Alternate Wetting and Drying) na may observation well.',
                'Masama sa palay ang sobra at kulang na tubig, at bumababa ang ani. Kapag kulang ang tubig, AWD ang maayos na paraan ng pagpapatubig.'),
        'ceb': ('Bantayi ang tubig',
                'Hupti nga basa kaayo ang uma hangtod 15 ka adlaw human sa pagbalhin-tanom. Pagsugod sa pagsaha, 3-5 cm nga tubig matag patubig. Kung kulang ang tubig, gamita ang AWD (Alternate Wetting and Drying) nga naay observation well.',
                'Dili maayo sa humay ang sobra ug kulang nga tubig, ug mous-os ang ani. Kung kulang ang tubig, AWD ang maayong paagi sa pagpatubig.'),
    },
    'weeds': {
        'en': ('Control weeds and snails',
               'Control weeds from 0 to 45 days after transplanting. Act if weeds cover more than 10% of the '
               'field between 15 and 40 days after transplanting. Pick or trap golden apple snails, '
               'especially while the plants are young.',
               'Weeds take the water and fertilizer meant for your rice, most of all in the first weeks. '
               'Snails eat young plants.'),
        'fil': ('Alisin ang damo at kuhol',
                'Kontrolin ang damo mula 0 hanggang 45 araw pagkatapos maglipat-tanim. Kumilos agad kung lampas'
                ' 10% ng bukid ang may damo sa ika-15 hanggang ika-40 araw. Pulutin o bitagin ang kuhol, lalo '
                'na habang bata pa ang palay.',
                'Inaagaw ng damo ang tubig at abono na para sa palay, lalo na sa unang mga linggo. Kinakain '
                'naman ng kuhol ang batang palay.'),
        'ceb': ('Kuhaa ang sagbot ug kuhol',
                'Kontrola ang sagbot gikan 0 hangtod 45 ka adlaw human sa pagbalhin-tanom. Lihok dayon kung '
                'lapas 10% sa uma ang naay sagbot sa ika-15 hangtod ika-40 nga adlaw. Pupha o litagi ang kuhol,'
                ' labi na samtang batan-on pa ang humay.',
                'Ang sagbot moagaw sa tubig ug abono nga para unta sa humay, labi na sa unang mga semana. Ang '
                'kuhol pud mokaon sa batan-ong humay.'),
    },
    'pests': {
        'en': ('Check for pests and diseases',
               'Monitor the field regularly from the early stage of the crop. Act only when damage goes past the levels listed in PalayCheck '
               '(pp. 48-49). Do not spray against leaf-eating insects within 30 days after transplanting.',
               'Spraying too early or too often also kills the friendly insects that eat pests. Checking first '
               'means you spray only when it is worth it.'),
        'fil': ('Silipin kung may peste o sakit',
                'Regular na ikutin ang bukid mula sa simula ng tanim. Kumilos lang kapag lumampas na ang sira sa nakalista sa '
                'PalayCheck (pp. 48-49). Huwag mag-spray laban sa mga insektong kumakain ng dahon sa unang 30 '
                'araw pagkatapos maglipat-tanim.',
                'Pag masyadong maaga o madalas mag-spray, namamatay din ang mga kaibigang insekto na kumakain '
                'ng peste. Kaya tingnan muna, at mag-spray lang kung sulit.'),
        'ceb': ('Tan-awa kung naay peste o sakit',
                'Regular nga libota ang uma gikan sa sinugdan sa tanom. Lihok lang kung lapas na ang daot sa nakalista sa PalayCheck (pp. '
                '48-49). Ayaw pag-spray sa mga insekto nga mokaon og dahon sulod sa unang 30 ka adlaw human sa '
                'pagbalhin-tanom.',
                'Kung sayo kaayo o kanunay mag-spray, mamatay pud ang mga insekto nga mokaon sa peste. Mao nga '
                'tan-awa sa una, ug mag-spray lang kung sulit.'),
    },
    'fertilizer2': {
        'en': ('Second fertilizer (mid-tillering)',
               'For varieties that mature in more than 110 days, apply the second nitrogen fertilizer at '
               'mid-tillering. Use the Leaf Color Chart to decide the amount.',
               'Longer-maturing varieties grow for more weeks, so their nitrogen is split into three smaller '
               'applications.'),
        'fil': ('Ikalawang abono (gitna ng pagsuwi)',
                'Kung ang palay mo ay nahihinog nang lampas 110 araw, mag-abono ulit ng nitrogen sa gitna ng '
                'pagsuwi. Gamitin ang Leaf Color Chart para malaman ang dami.',
                'Mas matagal lumaki ang mga palay na matagal mahinog, kaya hinahati sa tatlo ang paglagay ng '
                'nitrogen.'),
        'ceb': ('Ikaduhang abono (tunga sa pagsaha)',
                'Kung ang imong humay mohinog lapas 110 ka adlaw, pag-abono usab og nitrogen sa tunga sa '
                'pagsaha. Gamita ang Leaf Color Chart aron mahibal-an ang gidaghanon.',
                'Mas dugay motubo ang humay nga dugay mohinog, mao nga bahinon sa tulo ang pagbutang sa '
                'nitrogen.'),
    },
    'fertilizerpi': {
        'en': ('Fertilizer before panicle initiation',
               'Apply the last nitrogen fertilizer 5-7 days before panicle initiation.',
               'This feeds the young panicle, the future grain head, so more grains form and fill.'),
        'fil': ('Abono bago mag-uhay',
                'Ilagay ang huling abono na nitrogen 5-7 araw bago magsimula ang uhay (panicle initiation).',
                'Ito ang pagkain ng batang uhay na magiging butil, kaya mas maraming butil ang mabubuo at '
                'mapupuno.'),
        'ceb': ('Abono sa dili pa mag-uhay',
                'Ibutang ang katapusang abono nga nitrogen 5-7 ka adlaw sa dili pa magsugod ang uhay (panicle '
                'initiation).',
                'Kini ang pagkaon sa batan-ong uhay nga mahimong lugas, mao nga mas daghang lugas ang maporma '
                'ug mapuno.'),
    },
    'flowering': {
        'en': ('Keep deeper water at flowering',
               'During flowering, keep 5-7 cm of water in the field. Do not let the field dry out from '
               'panicle initiation through grain filling.',
               'Drought at flowering leaves empty grains. This is when the plant needs water the most.'),
        'fil': ('Mas malalim na tubig pag namumulaklak',
                'Habang namumulaklak, panatilihin ang 5-7 cm na tubig sa bukid. Huwag hayaang matuyo ang bukid '
                'mula pag-uhay hanggang magkalaman ang butil.',
                'Pag natuyuan habang namumulaklak, hungkag ang butil. Ito ang panahon na pinaka-kailangan ng '
                'palay ang tubig.'),
        'ceb': ('Lawomi ang tubig samtang namulak',
                'Samtang namulak, hupti ang 5-7 cm nga tubig sa uma. Ayaw pasagdi nga mamala ang uma gikan '
                'pag-uhay hangtod malamnan ang lugas.',
                'Kung mamala samtang namulak, hungot ang lugas. Kini ang panahon nga labing kinahanglan sa '
                'humay ang tubig.'),
    },
    'drain': {
        'en': ('Drain the field before harvest',
               'Drain the field 1-2 weeks before the expected harvest date.',
               'A drained field lets the grains ripen evenly and makes harvesting easier.'),
        'fil': ('Patuyuin ang bukid bago mag-ani',
                'Patuyuin ang bukid 1-2 linggo bago ang inaasahang araw ng ani.',
                'Pag tuyo ang bukid, pantay ang hinog ng butil at mas madaling mag-ani.'),
        'ceb': ('Pahubsa ang uma sa dili pa mag-ani',
                'Pahubsa ang uma 1-2 ka semana sa dili pa ang gipaabot nga adlaw sa ani.',
                'Kung hubas ang uma, patas ang hinog sa lugas ug mas sayon mag-ani.'),
    },
    'harvest': {
        'en': ('Harvest at the right time',
               'Harvest when 85-90% of the grains are golden yellow (90-95% if you use a combine harvester). '
               'Thresh within 1 day after manual harvesting in the wet season, or 2 days in the dry season.',
               'Harvesting too early gives unripe grains; too late, the grains fall off and break. Threshing '
               'quickly keeps the grain from spoiling.'),
        'fil': ('Mag-ani sa tamang oras',
                'Mag-ani kapag 85-90% ng butil ay kulay ginto na (90-95% kung combine harvester ang gamit). '
                'Kung kamay ang pag-ani, giikin sa loob ng 1 araw pag tag-ulan, o 2 araw pag tag-init.',
                'Pag masyadong maaga, hilaw pa ang butil. Pag huli na, nalalaglag at nababasag. Pag giniik '
                'agad, hindi nasisira ang butil.'),
        'ceb': ('Ani sa sakto nga oras',
                'Ani kung 85-90% sa lugas bulawanon na (90-95% kung combine harvester ang gamit). Kung kamot '
                'ang pag-ani, giuka sulod sa 1 ka adlaw kung ting-ulan, o 2 ka adlaw kung ting-init.',
                'Kung sayo kaayo, hilaw pa ang lugas. Kung ulahi na, mangahulog ug mabuak. Kung giuk-on dayon, '
                'dili madaot ang lugas.'),
    },
    'drystore': {
        'en': ('Dry, clean and store the grain',
               'Dry the palay evenly within 12-24 hours after harvest or threshing, down to 12-14% moisture. '
               'Clean the grains 2-3 days after drying, then store them properly.',
               'Wet grain heats up and spoils. Well-dried, clean grain keeps its quality and sells at a '
               'better price.'),
        'fil': ('Patuyuin, linisin at itago ang palay',
                'Ibilad nang pantay ang palay sa loob ng 12-24 oras pagkatapos ng ani o giik, hanggang 12-14% '
                'moisture. Linisin 2-3 araw pagkatapos matuyo, tapos itago nang maayos.',
                'Ang basang palay ay umiinit at nabubulok. Ang tuyo at malinis na palay ay maganda ang kalidad '
                'at mas mataas ang bentahan.'),
        'ceb': ('Pauga, limpyohi ug tipigi ang humay',
                'Ibulad og patas ang humay sulod sa 12-24 ka oras human sa ani o giuk, hangtod 12-14% moisture.'
                ' Limpyohi 2-3 ka adlaw human mauga, dayon tipigi og maayo.',
                'Ang basa nga humay moinit ug madunot. Ang uga ug limpyo nga humay maayo ang kalidad ug mas '
                'taas ang baligya.'),
    },
}

TEXT.update(direct_seeded.TEXT)

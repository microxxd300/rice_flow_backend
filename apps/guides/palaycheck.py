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

REFERENCE = 'PalayCheck System 2022 Revised Edition (DA-PhilRice)'
REFERENCE_URL = 'https://www.philrice.gov.ph/wp-content/uploads/2023/02/PalayCheck-System-2022-Revised-Edition.pdf'

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


def plan(maturity_days) -> list:
    """The guide steps for a variety, in order: [{key, key_check, category, pages, day}, ...]."""
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
        'fil': ('Kumuha ng certified na binhi ng inirerekomendang uri ng palay',
                'Bumili ng binhing may valid na BPI-NSQCS certified-seed tag, mas mabuti kung mula sa '
                'accredited seed grower. Pumili ng uri ng palay na angkop sa inyong bukid (may patubig o '
                'sahod-ulan) at sa panahon. Kung luma o itinabing binhi ang gagamitin, subukan muna kung '
                'tumutubo pa bago magpunla.',
                'Ang magandang binhi ay nagiging matibay at pantay na halaman at mas malaking ani. Ang tag '
                'ay patunay na sinuri ng gobyerno ang binhi. Ang uri ng palay na para sa inyong bukid at '
                'panahon ay mas kayang tiisin ang baha o tagtuyot ng panahong iyon.'),
        'ceb': ('Pagkuha og certified nga binhi sa girekomenda nga klase sa humay',
                'Pagpalit og binhi nga adunay valid nga BPI-NSQCS certified-seed tag, mas maayo kon gikan '
                'sa accredited seed grower. Pagpili og klase sa humay nga haom sa inyong uma (may patubig '
                'o sahod-ulan) ug sa panahon. Kon daan o gitipigan nga binhi ang gamiton, sulayi una kon '
                'moturok pa sa dili pa magpugas.',
                'Ang maayong binhi mahimong lig-on ug patas nga tanom ug mas dako nga ani. Ang tag nagpakita '
                'nga gisusi sa gobyerno ang binhi. Ang klase sa humay nga para sa inyong uma ug panahon mas '
                'makaagwanta sa baha o hulaw nianang panahona.'),
    },
    'plow': {
        'en': ('Rest the field, then plow',
               'Let the field rest for at least 30 days after the last harvest. Plow or rotovate 21-30 days '
               'before transplanting, then harrow every 7 days. Plant within 14 days of the regular planting '
               'schedule of the farms around you.',
               'Resting and plowing early lets weeds, straw and stubble rot, so the soil becomes soft and '
               'clean. When nearby farms plant at about the same time, pests cannot keep moving from one '
               'field to the next all season.'),
        'fil': ('Ipahinga ang bukid, saka araruhin',
                'Hayaang magpahinga ang bukid nang hindi bababa sa 30 araw pagkatapos ng huling ani. '
                'Araruhin o i-rotovate 21-30 araw bago maglipat-tanim, saka suyurin tuwing 7 araw. Magtanim '
                'sa loob ng 14 araw mula sa karaniwang iskedyul ng pagtatanim ng mga katabing bukid.',
                'Kapag ipinahinga at maagang inararo, nabubulok ang damo, dayami at pinagtabasan kaya '
                'lumalambot at lumilinis ang lupa. Kapag sabay-sabay magtanim ang magkakatabing bukid, hindi '
                'makalipat-lipat ang peste buong panahon.'),
        'ceb': ('Papahulaya ang uma, unya daroha',
                'Papahulaya ang uma sulod sa labing menos 30 ka adlaw human sa katapusang ani. Daroha o '
                'i-rotovate 21-30 ka adlaw sa dili pa magbalhin-tanom, unya suyda matag 7 ka adlaw. '
                'Pagtanom sulod sa 14 ka adlaw sa naandang iskedyul sa pagtanom sa mga silingang uma.',
                'Kon gipahulay ug sayo nga gidaro, madunot ang sagbot, dagami ug tuod busa mohumok ug '
                'molimpyo ang yuta. Kon dungan nga motanom ang magsilingang uma, dili makabalhin-balhin ang '
                'peste sa tibuok panahon.'),
    },
    'seedbed': {
        'en': ('Prepare the seedbed and sow',
               'Sow 20-40 kg of seeds per hectare on a 400 m2 seedbed. On fine-textured soil, mix in 3-4 bags '
               'of commercial organic fertilizer before leveling the seedbed. Protect the young seedlings '
               'from golden apple snails.',
               'Sowing the right amount of seed gives strong seedlings that are not crowded. Loose, rich '
               'soil makes pulling the seedlings easier, with less damage to the roots.'),
        'fil': ('Ihanda ang punlaan at magpunla',
                'Magpunla ng 20-40 kg na binhi bawat ektarya sa 400 m2 na punlaan. Sa pino o malagkit na '
                'lupa, maghalo ng 3-4 na sako ng komersyal na organikong pataba bago patagin ang punlaan. '
                'Bantayan ang batang punla laban sa golden apple snail (kuhol).',
                'Ang tamang dami ng binhi ay nagbibigay ng matibay na punla na hindi siksikan. Ang malambot '
                'at mayamang lupa ay nagpapadali sa pagbunot ng punla at hindi nasisira ang ugat.'),
        'ceb': ('Andama ang punlaan ug pagpugas',
                'Pagpugas og 20-40 kg nga binhi matag ektarya sa 400 m2 nga punlaan. Sa pino o pilit nga '
                'yuta, sagoli og 3-4 ka sako sa komersyal nga organikong abono sa dili pa patagon ang '
                'punlaan. Bantayi ang batan-ong semilya batok sa golden apple snail (kuhol).',
                'Ang husto nga gidaghanon sa binhi mohatag og lig-on nga semilya nga dili hugot. Ang humok '
                'ug tambok nga yuta mopasayon sa pagbunot sa semilya ug dili madaot ang gamot.'),
    },
    'leveling': {
        'en': ('Level the field',
               'Puddle and level the field well. After final leveling, no spot should have water deeper '
               'than 5 cm (about a thumb length), and no mound of soil should show above the water.',
               'In a level field, water, fertilizer and weed control reach every part evenly, so the whole '
               'crop grows and ripens together. A poorly prepared field can yield 5% less.'),
        'fil': ('Patagin ang bukid',
                'Putikin at patagin nang mabuti ang bukid. Pagkatapos ng huling pagpapatag, walang bahaging '
                'mas malalim sa 5 cm ang tubig (mga isang hinlalaki) at walang umbok ng lupa na lumilitaw sa '
                'ibabaw ng tubig.',
                'Sa patag na bukid, pantay na naaabot ng tubig, pataba at pagkontrol ng damo ang bawat '
                'bahagi, kaya sabay-sabay lumalaki at nahihinog ang palay. Ang bukid na hindi maayos ang '
                'paghahanda ay maaaring mabawasan ng 5% ang ani.'),
        'ceb': ('Patagon ang uma',
                'Lapoka ug patagon pag-ayo ang uma. Human sa katapusang pagpatag, walay bahin nga lapas sa '
                '5 cm ang giladmon sa tubig (mga usa ka kumagko) ug walay bungdo sa yuta nga makita ibabaw '
                'sa tubig.',
                'Sa patag nga uma, patas nga maabot sa tubig, abono ug pagkontrol sa sagbot ang matag bahin, '
                'busa dungan nga motubo ug mohinog ang humay. Ang uma nga dili maayo ang pag-andam mahimong '
                'mokunhod og 5% ang ani.'),
    },
    'transplant': {
        'en': ('Transplant the seedlings',
               'Transplant 18-21-day-old seedlings, 2-3 per hill. Space the hills 20 x 20 cm in the wet season '
               'or 20 x 15 cm in the dry season. Do not cut the leaves of the seedlings before transplanting.',
               'Seedlings older than 25 days recover poorly from transplanting and make fewer tillers. Cut '
               'leaves are an entry point for diseases.'),
        'fil': ('Ilipat-tanim ang punla',
                'Ilipat-tanim ang 18-21 araw na punla, 2-3 bawat tundos. Gawing 20 x 20 cm ang pagitan sa '
                'tag-ulan o 20 x 15 cm sa tag-init. Huwag putulin ang dahon ng punla bago itanim.',
                'Ang punlang lampas 25 araw ay mahirap makabawi sa paglilipat at kaunti ang suwi. Ang '
                'pinutol na dahon ay daanan ng sakit.'),
        'ceb': ('Ibalhin-tanom ang semilya',
                'Ibalhin-tanom ang 18-21 ka adlaw nga semilya, 2-3 matag tundos. Himoa nga 20 x 20 cm ang '
                'gilay-on sa tingulan o 20 x 15 cm sa tinginit. Ayaw putla ang dahon sa semilya sa dili pa '
                'itanom.',
                'Ang semilya nga lapas 25 ka adlaw lisod makabawi sa pagbalhin ug gamay ra ang saha. Ang '
                'giputol nga dahon agianan sa sakit.'),
    },
    'replant': {
        'en': ('Replant missing hills',
               'Within 7 days after transplanting, replant missing hills using seedlings from the same seedbed.',
               'Filling the gaps early keeps enough plants in the field. Seedlings from the same seedbed keep '
               'the whole crop ripening at the same time.'),
        'fil': ('Tamnan ang mga nawalang tundos',
                'Sa loob ng 7 araw pagkatapos maglipat-tanim, tamnan ang mga nawalang tundos gamit ang punla '
                'mula sa parehong punlaan.',
                'Ang maagang pagpuno sa mga puwang ay nagpapanatili ng sapat na halaman sa bukid. Ang punla '
                'mula sa parehong punlaan ay nagpapanatiling sabay ang paghinog ng palay.'),
        'ceb': ('Tamni ang nawala nga mga tundos',
                'Sulod sa 7 ka adlaw human sa pagbalhin-tanom, tamni ang nawala nga mga tundos gamit ang '
                'semilya gikan sa parehong punlaan.',
                'Ang sayo nga pagpuno sa mga haw-ang nagpabilin og igo nga tanom sa uma. Ang semilya gikan sa '
                'parehong punlaan nagpabilin nga dungan ang paghinog sa humay.'),
    },
    'fertilizer1': {
        'en': ('First fertilizer application',
               'Apply the first fertilizer between 0 and 14 days after transplanting. Base the amounts of N, P '
               'and K on your field\'s soil test or on a recommendation from the LCC App, RCMAS, NOPT or MOET.',
               'Young plants need nutrients early to make many tillers. A soil test shows what your field '
               'really lacks, so you do not pay for fertilizer it does not need.'),
        'fil': ('Unang paglalagay ng pataba',
                'Ilagay ang unang pataba sa pagitan ng 0 at 14 araw pagkatapos maglipat-tanim. Ibatay ang dami '
                'ng N, P at K sa soil test ng inyong bukid o sa rekomendasyon ng LCC App, RCMAS, NOPT o MOET.',
                'Kailangan ng batang halaman ang sustansya nang maaga para dumami ang suwi. Ipinapakita ng soil '
                'test kung ano talaga ang kulang sa inyong bukid, kaya hindi kayo gagastos sa patabang hindi '
                'kailangan.'),
        'ceb': ('Unang pagbutang og abono',
                'Ibutang ang unang abono tali sa 0 ug 14 ka adlaw human sa pagbalhin-tanom. Ibase ang '
                'gidaghanon sa N, P ug K sa soil test sa inyong uma o sa rekomendasyon sa LCC App, RCMAS, NOPT '
                'o MOET.',
                'Kinahanglan sa batan-ong tanom ang sustansya sa sayo aron modaghan ang saha. Ipakita sa soil '
                'test kon unsa gyud ang kulang sa inyong uma, busa dili mogasto sa abono nga dili kinahanglan.'),
    },
    'lcc': {
        'en': ('Check the leaf color every 7 days',
               'From 14 days after transplanting until early flowering, compare the leaves with a Leaf Color '
               'Chart (LCC) or the LCC App every 7 days to see if the crop needs more nitrogen.',
               'Pale leaves mean the plant needs nitrogen. Checking the color keeps you from applying too '
               'little or too much.'),
        'fil': ('Suriin ang kulay ng dahon tuwing 7 araw',
                'Mula 14 araw pagkatapos maglipat-tanim hanggang sa maagang pamumulaklak, ihambing ang dahon sa '
                'Leaf Color Chart (LCC) o sa LCC App tuwing 7 araw para malaman kung kailangan pa ng nitrogen.',
                'Ang maputlang dahon ay nangangahulugang kailangan ng nitrogen. Ang pagsuri ng kulay ay '
                'pumipigil sa paglalagay ng kulang o sobrang pataba.'),
        'ceb': ('Susiha ang kolor sa dahon matag 7 ka adlaw',
                'Gikan sa 14 ka adlaw human sa pagbalhin-tanom hangtod sa sayo nga pagpamulak, itandi ang dahon '
                'sa Leaf Color Chart (LCC) o sa LCC App matag 7 ka adlaw aron mahibaw-an kon kinahanglan pa og '
                'nitrogen.',
                'Ang luspad nga dahon nagpasabot nga kinahanglan og nitrogen. Ang pagsusi sa kolor mopugong sa '
                'pagbutang og kulang o sobra nga abono.'),
    },
    'water': {
        'en': ('Manage the water',
               'Keep the field saturated up to 15 days after transplanting. From early tillering, keep 3-5 cm '
               'of water at each irrigation, practicing Alternate Wetting and Drying (AWD) with an observation '
               'well.',
               'Too much water and too little water both stress the rice and cut the yield. AWD lets the field '
               'dry a little between irrigations, which saves water without hurting the crop.'),
        'fil': ('Pangasiwaan ang tubig',
                'Panatilihing basang-basa ang bukid hanggang 15 araw pagkatapos maglipat-tanim. Mula sa maagang '
                'pagsusuwi, panatilihin ang 3-5 cm na tubig sa bawat patubig, gamit ang Alternate Wetting and '
                'Drying (AWD) na may observation well.',
                'Ang sobra at kulang na tubig ay parehong nakakasama sa palay at nagpapababa ng ani. Sa AWD, '
                'bahagyang natutuyo ang bukid sa pagitan ng patubig, kaya nakakatipid sa tubig nang hindi '
                'nasisira ang pananim.'),
        'ceb': ('Atimana ang tubig',
                'Hupti nga basa kaayo ang uma hangtod 15 ka adlaw human sa pagbalhin-tanom. Gikan sa sayo nga '
                'pagsaha, hupti ang 3-5 cm nga tubig matag patubig, gamit ang Alternate Wetting and Drying '
                '(AWD) nga adunay observation well.',
                'Ang sobra ug kulang nga tubig parehong makadaot sa humay ug mokunhod ang ani. Sa AWD, gamay nga '
                'mamala ang uma tali sa mga patubig, busa makadaginot sa tubig nga dili madaot ang tanom.'),
    },
    'weeds': {
        'en': ('Control weeds and snails',
               'Control weeds from 0 to 45 days after transplanting. Act if weeds cover more than 10% of the '
               'field between 15 and 40 days after transplanting. Pick or trap golden apple snails, '
               'especially while the plants are young.',
               'Weeds take the water and fertilizer meant for your rice, most of all in the first weeks. '
               'Snails eat young plants.'),
        'fil': ('Kontrolin ang damo at kuhol',
                'Kontrolin ang damo mula 0 hanggang 45 araw pagkatapos maglipat-tanim. Kumilos kung higit 10% '
                'ng bukid ang may damo sa pagitan ng 15 at 40 araw pagkatapos maglipat-tanim. Pulutin o bitagin '
                'ang golden apple snail, lalo na habang bata pa ang halaman.',
                'Inaagaw ng damo ang tubig at patabang para sa palay, lalo na sa mga unang linggo. Kinakain ng '
                'kuhol ang batang halaman.'),
        'ceb': ('Kontrola ang sagbot ug kuhol',
                'Kontrola ang sagbot gikan sa 0 hangtod 45 ka adlaw human sa pagbalhin-tanom. Lihok kon lapas '
                '10% sa uma ang adunay sagbot tali sa 15 ug 40 ka adlaw human sa pagbalhin-tanom. Pupha o '
                'litaga ang golden apple snail, labi na samtang batan-on pa ang tanom.',
                'Agawon sa sagbot ang tubig ug abono nga para sa humay, labi na sa unang mga semana. Kan-on sa '
                'kuhol ang batan-ong tanom.'),
    },
    'pests': {
        'en': ('Check for pests and diseases',
               'Walk the field every week. Act only when damage goes past the levels listed in PalayCheck '
               '(pp. 48-49). Do not spray against leaf-eating insects within 30 days after transplanting.',
               'Spraying too early or too often also kills the friendly insects that eat pests. Checking first '
               'means you spray only when it is worth it.'),
        'fil': ('Suriin kung may peste at sakit',
                'Libutin ang bukid linggo-linggo. Kumilos lamang kapag lumampas ang pinsala sa antas na nakalista '
                'sa PalayCheck (pp. 48-49). Huwag mag-spray laban sa mga insektong kumakain ng dahon sa loob ng '
                '30 araw pagkatapos maglipat-tanim.',
                'Ang sobrang aga o madalas na pag-spray ay pumapatay din sa mga kaibigang insekto na kumakain ng '
                'peste. Ang pagsuri muna ay nangangahulugang mag-spray lamang kapag sulit.'),
        'ceb': ('Susiha kon adunay peste ug sakit',
                'Libuta ang uma matag semana. Lihok lamang kon lapas na ang kadaot sa lebel nga nalista sa '
                'PalayCheck (pp. 48-49). Ayaw pag-spray batok sa mga insekto nga mokaon og dahon sulod sa 30 ka '
                'adlaw human sa pagbalhin-tanom.',
                'Ang sayo kaayo o kanunay nga pag-spray mopatay usab sa mga higalang insekto nga mokaon sa peste. '
                'Ang pagsusi una nagpasabot nga mo-spray lamang kon takos.'),
    },
    'fertilizer2': {
        'en': ('Second fertilizer (mid-tillering)',
               'For varieties that mature in more than 110 days, apply the second nitrogen fertilizer at '
               'mid-tillering. Use the Leaf Color Chart to decide the amount.',
               'Longer-maturing varieties grow for more weeks, so their nitrogen is split into three smaller '
               'applications.'),
        'fil': ('Ikalawang pataba (kalagitnaan ng pagsusuwi)',
                'Para sa mga uri ng palay na nahihinog nang higit 110 araw, ilagay ang ikalawang nitrogen na '
                'pataba sa kalagitnaan ng pagsusuwi. Gamitin ang Leaf Color Chart para malaman ang dami.',
                'Mas matagal lumaki ang mga uri na matagal mahinog, kaya hinahati sa tatlong mas maliit na '
                'paglalagay ang nitrogen.'),
        'ceb': ('Ikaduhang abono (tunga-tunga sa pagsaha)',
                'Para sa mga klase sa humay nga mohinog lapas 110 ka adlaw, ibutang ang ikaduhang nitrogen nga '
                'abono sa tunga-tunga sa pagsaha. Gamita ang Leaf Color Chart aron mahibaw-an ang gidaghanon.',
                'Mas dugay motubo ang mga klase nga dugay mohinog, busa bahinon sa tulo ka mas gamay nga '
                'pagbutang ang nitrogen.'),
    },
    'fertilizerpi': {
        'en': ('Fertilizer before panicle initiation',
               'Apply the last nitrogen fertilizer 5-7 days before panicle initiation.',
               'This feeds the young panicle, the future grain head, so more grains form and fill.'),
        'fil': ('Pataba bago ang panicle initiation',
                'Ilagay ang huling nitrogen na pataba 5-7 araw bago ang panicle initiation (pagsisimula ng uhay).',
                'Pinapakain nito ang batang uhay, ang magiging butil, kaya mas maraming butil ang nabubuo at '
                'napupuno.'),
        'ceb': ('Abono sa dili pa ang panicle initiation',
                'Ibutang ang katapusang nitrogen nga abono 5-7 ka adlaw sa dili pa ang panicle initiation '
                '(pagsugod sa uhay).',
                'Pakan-on niini ang batan-ong uhay, ang mahimong lugas, busa mas daghang lugas ang maporma ug '
                'mapuno.'),
    },
    'flowering': {
        'en': ('Keep deeper water at flowering',
               'During flowering, keep 5-7 cm of water in the field. Do not let the field dry out from '
               'panicle initiation through grain filling.',
               'Drought at flowering leaves empty grains. This is when the plant needs water the most.'),
        'fil': ('Mas malalim na tubig sa pamumulaklak',
                'Habang namumulaklak, panatilihin ang 5-7 cm na tubig sa bukid. Huwag hayaang matuyo ang bukid '
                'mula sa panicle initiation hanggang sa pagpupuno ng butil.',
                'Ang tagtuyot sa pamumulaklak ay nag-iiwan ng hungkag na butil. Ito ang panahon na pinakakailangan '
                'ng halaman ang tubig.'),
        'ceb': ('Mas lawom nga tubig sa pagpamulak',
                'Samtang namulak, hupti ang 5-7 cm nga tubig sa uma. Ayaw tugoti nga mamala ang uma gikan sa '
                'panicle initiation hangtod sa pagpuno sa lugas.',
                'Ang hulaw sa pagpamulak mobilin og hungot nga lugas. Kini ang panahon nga labing kinahanglan sa '
                'tanom ang tubig.'),
    },
    'drain': {
        'en': ('Drain the field before harvest',
               'Drain the field 1-2 weeks before the expected harvest date.',
               'A drained field lets the grains ripen evenly and makes harvesting easier.'),
        'fil': ('Patuyuin ang bukid bago mag-ani',
                'Patuyuin ang bukid 1-2 linggo bago ang inaasahang araw ng pag-aani.',
                'Sa tuyong bukid, pantay na nahihinog ang butil at mas madali ang pag-aani.'),
        'ceb': ('Pahubsa ang uma sa dili pa mag-ani',
                'Pahubsa ang uma 1-2 ka semana sa dili pa ang gipaabot nga adlaw sa pag-ani.',
                'Sa hubas nga uma, patas nga mohinog ang lugas ug mas sayon ang pag-ani.'),
    },
    'harvest': {
        'en': ('Harvest at the right time',
               'Harvest when 85-90% of the grains are golden yellow (90-95% if you use a combine harvester). '
               'Thresh within 1 day after manual harvesting in the wet season, or 2 days in the dry season.',
               'Harvesting too early gives unripe grains; too late, the grains fall off and break. Threshing '
               'quickly keeps the grain from spoiling.'),
        'fil': ('Mag-ani sa tamang panahon',
                'Mag-ani kapag 85-90% ng butil ay kulay ginto na (90-95% kung gagamit ng combine harvester). '
                'Giikin sa loob ng 1 araw pagkatapos ng manu-manong pag-aani sa tag-ulan, o 2 araw sa tag-init.',
                'Kapag masyadong maaga, hilaw ang butil; kapag huli na, nalalaglag at nababasag ang butil. Ang '
                'mabilis na paggiik ay pumipigil sa pagkasira ng butil.'),
        'ceb': ('Pag-ani sa husto nga panahon',
                'Pag-ani kon 85-90% sa lugas bulawanon na ang kolor (90-95% kon mogamit og combine harvester). '
                'Giuka sulod sa 1 ka adlaw human sa mano-mano nga pag-ani sa tingulan, o 2 ka adlaw sa tinginit.',
                'Kon sayo kaayo, hilaw ang lugas; kon ulahi na, mangahulog ug mabuak ang lugas. Ang dali nga '
                'paggiuk mopugong sa pagkadaot sa lugas.'),
    },
    'drystore': {
        'en': ('Dry, clean and store the grain',
               'Dry the palay evenly within 12-24 hours after harvest or threshing, down to 12-14% moisture. '
               'Clean the grains 2-3 days after drying, then store them properly.',
               'Wet grain heats up and spoils. Well-dried, clean grain keeps its quality and sells at a '
               'better price.'),
        'fil': ('Patuyuin, linisin at itago ang butil',
                'Patuyuin nang pantay ang palay sa loob ng 12-24 oras pagkatapos ng ani o paggiik, hanggang '
                '12-14% moisture. Linisin ang butil 2-3 araw pagkatapos patuyuin, saka itago nang maayos.',
                'Umiinit at nabubulok ang basang butil. Ang tuyo at malinis na butil ay nananatiling maganda ang '
                'kalidad at mas mataas ang presyo.'),
        'ceb': ('Pauga, limpyohi ug tipigi ang lugas',
                'Pauga og patas ang humay sulod sa 12-24 ka oras human sa ani o paggiuk, hangtod 12-14% '
                'moisture. Limpyohi ang lugas 2-3 ka adlaw human mapauga, unya tipigi og maayo.',
                'Moinit ug madunot ang basa nga lugas. Ang uga ug limpyo nga lugas magpabilin nga maayo ang '
                'kalidad ug mas taas ang presyo.'),
    },
}

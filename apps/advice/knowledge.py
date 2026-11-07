"""
The booklet cards: what RiceFlow tells a farmer about a field problem.

Every line comes from an official PhilRice / PalayCheck booklet and names its page or
slide, so the farmer (and the validator) can check it. The AI never adds to these: it
only finds and explains them (see services.py). Chemical names and doses are left out
on purpose; the cards send the farmer to an agriculturist instead.

Page numbers are the printed page numbers of each booklet. Filipino and Bisaya are
everyday words; a native speaker and the validator still have to check them.

Sections of a problem card, in the order the app shows them:
  identify      how to tell it is this problem
  serious_when  the PalayCheck level where the yield loss becomes significant
  do_now        safe first steps
  dont          what not to do
  next_season   how to prevent it next time
"""

SOURCES = {
    'palaycheck': {
        'title': 'PalayCheck System for Irrigated Lowland Rice (2022 revised edition)',
        'publisher': 'PhilRice',
        'url': 'https://www.philrice.gov.ph/wp-content/uploads/2023/02/PalayCheck-System-2022-Revised-Edition.pdf',
    },
    'keycheck7': {
        'title': 'PalayCheck Key Check 7: Pest Management',
        'publisher': 'PhilRice (PinoyRice)',
        'url': 'https://www.pinoyrice.com/?wpdmdl=7196',
    },
    'harmful': {
        'title': 'Harmful Organisms in Philippine Rice Fields',
        'publisher': 'PhilRice',
        'url': 'https://www.philrice.gov.ph/wp-content/uploads/2023/02/Harmful-organisms-in-Philippine-rice-fields.pdf',
    },
    'snail': {
        'title': 'Golden Apple Snail Management',
        'publisher': 'PhilRice (PinoyRice)',
        'url': 'https://www.pinoyrice.com/?wpdmdl=715',
    },
    'diseases': {
        'title': 'Diseases of Rice and Their Management',
        'publisher': 'PhilRice (PinoyRice)',
        'url': 'https://www.pinoyrice.com/?wpdmdl=712',
    },
    'blb': {
        'title': 'Bacterial Leaf Blight (handout)',
        'publisher': 'PhilRice (PinoyRice)',
        'url': 'https://www.pinoyrice.com/download/bacterial-leaf-blight/',
    },
    'blast_shb': {
        'title': 'Pamamahala ng Sheath Blight at Rice Blast (handout)',
        'publisher': 'PhilRice (PinoyRice)',
        'url': 'https://www.pinoyrice.com/download/pamamahala-ng-sheath-blight-at-rice-blast/',
    },
    'hopper': {
        'title': 'Pamamahala ng Armyworm at Planthopper (handout)',
        'publisher': 'PhilRice (PinoyRice)',
        'url': 'https://www.pinoyrice.com/download/pamamahala-ng-armyworm-at-planthopper',
    },
    # Read by GeoRice AI's booklet search (apps/ai/booklets.py), not quoted on the cards
    'field_guide': {
        'title': 'Field Guide: Harmful and Useful Organisms in Philippine Rice Fields',
        'publisher': 'PhilRice',
        'url': 'https://www.philrice.gov.ph/wp-content/uploads/2023/02/Field-Guide_-Harmful-and-useful-organisms-in-Philippine-rice-fields-Insects-and-Non-insects.pdf',
    },
    'sheath_rot': {
        'title': 'Sheath Rot (handout)',
        'publisher': 'PhilRice (PinoyRice)',
        'url': 'https://www.pinoyrice.com/download/sheath-rot/',
    },
}

# Who to call. The PhilRice Text Center number is from PhilRice's site (2024);
# the adviser should confirm it before release.
HELP_TEXT_NUMBER = '0917-111-7423'

LANGS = ('en', 'fil', 'ceb')


def L(en, fil, ceb, *src):
    """One line in three languages, with its sources: ('palaycheck', 'p. 51')."""
    return {'en': en, 'fil': fil, 'ceb': ceb, 'src': list(src)}


# Shown on every card
GET_HELP = L(
    'If the damage keeps spreading, ask the Panabo City Agriculture Office, or text '
    f'PhilRice at {HELP_TEXT_NUMBER}.',
    'Kung patuloy na kumakalat ang pinsala, magtanong sa City Agriculture Office ng Panabo, '
    f'o mag-text sa PhilRice sa {HELP_TEXT_NUMBER}.',
    'Kung padayon nga mokaylap ang danyos, pangutana sa City Agriculture Office sa Panabo, '
    f'o i-text ang PhilRice sa {HELP_TEXT_NUMBER}.',
)

# Shown when the farmer marks the problem as severe
URGENT = L(
    'Severe problem reported. Do the first steps below now. Take clear photos, and contact '
    'the City Agriculture Office if the damage continues. Your report is saved in your field log.',
    'Malalang problema ang naitala. Gawin na ngayon ang mga unang hakbang sa ibaba. Kumuha ng '
    'malinaw na litrato, at tawagan ang City Agriculture Office kung tuloy pa rin ang pinsala. '
    'Naka-save ang ulat mo sa field log.',
    'Grabe nga problema ang na-report. Buhata karon ang mga unang lakang sa ubos. Pagkuha og '
    'klaro nga litrato, ug kontaka ang City Agriculture Office kung magpadayon ang danyos. '
    'Na-save ang imong report sa field log.',
)

# Insect advice shared by several cards (PalayCheck pp. 50-51)
_LAST_RESORT = L(
    "Don't spray before checking. Insecticide is the last resort, only when other methods fail.",
    'Huwag mag-spray nang hindi muna sinusuri. Huling paraan lang ang insecticide, kapag hindi '
    'umubra ang ibang paraan.',
    'Ayaw pag-spray nga wala pa ma-check. Kataposang paagi ra ang insecticide, kung dili '
    'molampos ang ubang paagi.',
    ('palaycheck', 'p. 50'),
)
_NO_EARLY_SPRAY = L(
    "Don't spray against leaf-eating insects within 30 days after transplanting "
    '(40 days after direct seeding).',
    'Huwag mag-spray laban sa mga insektong kumakain ng dahon sa unang 30 araw matapos '
    'maglipat-tanim (40 araw kung sabog-tanim).',
    'Ayaw pag-spray batok sa mga insekto nga mokaon og dahon sulod sa unang 30 ka adlaw human '
    'sa pagbalhin-tanom (40 ka adlaw kung sabod-tanom).',
    ('palaycheck', 'p. 51'), ('hopper', 'p. 1'),
)
_FRIENDLY_INSECTS = L(
    'Let friendly insects and spiders live in the field. They keep pests down for free.',
    'Hayaang mabuhay ang mga kaibigang insekto at gagamba sa palayan. Sila ang libreng '
    'pumipigil sa peste.',
    'Pasagdi nga mabuhi ang mga higala nga insekto ug lawalawa sa uma. Sila ang libre nga '
    'mopugong sa peste.',
    ('palaycheck', 'pp. 50-51'),
)
_SYNC_PLANTING = L(
    'Next season, plant at the same time as your neighbors after a 30-day rest period, and '
    'use a variety resistant to the pests in your area.',
    'Sa susunod na taniman, sabay-sabay magtanim kasama ang mga kapitbahay matapos ang 30 araw '
    'na pahinga ng lupa, at gumamit ng barayting matibay sa peste rito.',
    'Sa sunod nga tanom, dungan mo og tanom sa mga silingan human sa 30 ka adlaw nga pahulay sa '
    'yuta, ug gamita ang barayti nga lig-on batok sa peste diri.',
    ('palaycheck', 'p. 50'),
)
_TOO_MUCH_N = L(
    "Don't put too much nitrogen fertilizer. Thick, soft leaves attract pests and disease.",
    'Huwag sobrahan ang abonong nitroheno. Ang makapal at malambot na dahon ay umaakit ng '
    'peste at sakit.',
    'Ayaw sobrahi ang abono nga nitrogen. Ang baga ug humok nga dahon modani og peste ug sakit.',
    ('keycheck7', 'slide 20'), ('hopper', 'p. 1'),
)
_ASK_BEFORE_FUNGICIDE = L(
    'Use a fungicide only if it is really needed, and ask an agriculturist which one and how '
    'much first.',
    'Gumamit lang ng fungicide kung talagang kailangan, at itanong muna sa agriculturist kung '
    'alin at gaano karami.',
    'Gamit ra og fungicide kung gikinahanglan gyud, ug pangutana una sa agriculturist kung asa '
    'ug pila ka daghan.',
    ('blast_shb', 'pp. 1-2'),
)


PROBLEMS = {
    'unknown': {
        'category': 'other',
        'name': L('Not sure what it is', 'Hindi sigurado kung ano', 'Dili sigurado kung unsa'),
        'aliases': [],
        'identify': [
            L('Look closely: which part is damaged (leaves, stem, panicle, or the whole plant), how '
              'much of the field, and whether you see insects, eggs, or snails.',
              'Tingnang mabuti: anong bahagi ang sira (dahon, tangkay, uhay, o buong tanim), gaano '
              'kalawak sa palayan, at kung may insekto, itlog, o kuhol.',
              'Tan-awa pag-ayo: unsang bahin ang nadaot (dahon, punoan, uhay, o tibuok tanom), unsa '
              'kalapad sa uma, ug kung naay insekto, itlog, o kuhol.',
              ('diseases', 'slide 5')),
            L('Compare the sick plants with healthy ones in the same field.',
              'Ikumpara ang may sakit na tanim sa malulusog sa parehong palayan.',
              'Ikumpara ang masakiton nga tanom sa himsog nga tanom sa samang uma.',
              ('diseases', 'slide 5')),
        ],
        'serious_when': None,
        'do_now': [
            L('Check the field in the early morning (5-7 AM) or late afternoon, in several spots, '
              'not just one.',
              'Silipin ang palayan nang maaga (5-7 AM) o hapon, sa ilang lugar, hindi lang sa isa.',
              'Susiha ang uma sayo sa buntag (5-7 AM) o hapon, sa pipila ka dapit, dili lang sa usa.',
              ('palaycheck', 'pp. 48, 50')),
        ],
        'dont': [_LAST_RESORT, _NO_EARLY_SPRAY],
        'next_season': [],
    },

    'rats': {
        'category': 'pest',
        'name': L('Rats', 'Daga', 'Ilaga'),
        'aliases': ['rat', 'rats', 'daga', 'ilaga', 'eat-out', 'cut stem', 'cut stems', 'putol',
                    'giputol', 'kinagat', 'burrow', 'lungga', 'lungag'],
        'identify': [
            L('Stems or panicles are cut, often worst in the middle of the field (eat-outs). Rats '
              'attack at every crop stage.',
              'Putol ang mga tangkay o uhay, kadalasang pinakamalala sa gitna ng palayan. Umaatake '
              'ang daga sa lahat ng yugto ng palay.',
              'Putol ang mga punoan o uhay, kasagaran pinakagrabe sa tunga sa uma. Moatake ang '
              'ilaga sa tanang yugto sa humay.',
              ('harmful', 'chart')),
        ],
        'serious_when': L(
            'Serious when more than 5% of the field has damaged tillers, from maximum tillering to '
            'maturity.',
            'Malala na kapag higit 5% ng palayan ang may sirang suwi, mula sa pinakamaraming suwi '
            'hanggang sa paghinog.',
            'Grabe na kung kapin sa 5% sa uma ang adunay nadaot nga saha, gikan sa kinadaghang '
            'saha hangtod sa paghinog.',
            ('palaycheck', 'p. 49')),
        'do_now': [
            L('Work with your neighbors. Rat control works only when it is timely and done by the '
              'whole community.',
              'Makipagtulungan sa mga kapitbahay. Umuubra lang ang pagpuksa ng daga kung napapanahon '
              'at sabay-sabay ang buong komunidad.',
              'Pakigtambayayong sa mga silingan. Molampos ra ang pagpugong sa ilaga kung sakto sa '
              'panahon ug dungan ang tibuok komunidad.',
              ('palaycheck', 'p. 51')),
            L('Fill rat burrows with soil and water.',
              'Tabunan ng lupa at tubig ang mga lungga ng daga.',
              'Taboni og yuta ug tubig ang mga lungag sa ilaga.',
              ('palaycheck', 'p. 51')),
            L('Keep the field and bunds clean so rats have fewer places to hide.',
              'Panatilihing malinis ang palayan at pilapil para kaunti ang taguan ng daga.',
              'Hinloi ang uma ug pilapil aron gamay ra ang tagoanan sa ilaga.',
              ('palaycheck', 'p. 51')),
        ],
        'dont': [],
        'next_season': [_SYNC_PLANTING],
    },

    'stem_borer': {
        'category': 'pest',
        'name': L('Stem borer', 'Aksip (stem borer)', 'Stem borer (aksip)'),
        'aliases': ['stem borer', 'stemborer', 'borer', 'aksip', 'deadheart', 'dead heart',
                    'whitehead', 'white head', 'puting uhay', 'puti nga uhay', 'walay sulod',
                    'walang laman', 'empty panicle', 'uod sa punoan', 'uod sa tangkay'],
        'identify': [
            L('Young plants: the center leaf dries and turns brown (deadheart). Older plants: the '
              'panicle turns white and empty (whitehead). The larvae bore inside the stem.',
              'Batang tanim: natutuyo at nagiging kayumanggi ang gitnang dahon (deadheart). '
              'Matandang tanim: pumuputi at walang laman ang uhay (whitehead). Nasa loob ng tangkay '
              'ang uod.',
              'Batan-on nga tanom: mamala ug mo-brown ang tunga nga dahon (deadheart). Tigulang nga '
              'tanom: moputi ug walay sulod ang uhay (whitehead). Naa sa sulod sa punoan ang ulod.',
              ('harmful', 'chart')),
            L('A whitehead from stem borer is completely empty and white. A panicle with neck blast '
              'is straw-colored and half-filled.',
              'Ang whitehead dahil sa aksip ay talagang walang laman at puti. Ang uhay na may neck '
              'blast ay kulay-dayami at kalahati ang laman.',
              'Ang whitehead tungod sa aksip hingpit nga walay sulod ug puti. Ang uhay nga adunay '
              'neck blast kolor-uhot ug katunga ra ang sulod.',
              ('palaycheck', 'p. 72')),
        ],
        'serious_when': L(
            'Serious at more than 30% deadheart (early tillering), more than 1 egg mass per square '
            'meter (mid to maximum tillering), or more than 20% whitehead (flowering onward).',
            'Malala na kapag higit 30% ang deadheart (maagang pagsuwi), higit 1 kumpol ng itlog '
            'bawat metro kuwadrado (gitna hanggang pinakamaraming suwi), o higit 20% ang whitehead '
            '(mula pamumulaklak).',
            'Grabe na kung kapin sa 30% ang deadheart (sayong pagsaha), kapin sa 1 ka pungpong sa '
            'itlog matag metro kwadrado (tunga hangtod kinadaghang saha), o kapin sa 20% ang '
            'whitehead (gikan sa pagpamulak).',
            ('palaycheck', 'p. 48')),
        'do_now': [
            L('Check the field in the early morning (5-7 AM) or late afternoon. Look for egg masses '
              'on the leaves.',
              'Silipin ang palayan nang maaga (5-7 AM) o hapon. Hanapin ang kumpol ng itlog sa dahon.',
              'Susiha ang uma sayo sa buntag (5-7 AM) o hapon. Pangitaa ang pungpong sa itlog sa dahon.',
              ('palaycheck', 'p. 48')),
            L('Protect the friendly insects: long-horned grasshoppers eat stem borer egg masses.',
              'Alagaan ang kaibigang insekto: kinakain ng long-horned grasshopper ang itlog ng aksip.',
              'Atimana ang higala nga insekto: kan-on sa long-horned grasshopper ang itlog sa aksip.',
              ('palaycheck', 'p. 51')),
        ],
        'dont': [_LAST_RESORT, _NO_EARLY_SPRAY],
        'next_season': [_SYNC_PLANTING],
    },

    'black_bug': {
        'category': 'pest',
        'name': L('Rice black bug', 'Itim na atangya', 'Itom nga tangaw (rice black bug)'),
        'aliases': ['black bug', 'rice black bug', 'rbb', 'atangya', 'itim na atangya', 'tangaw',
                    'itom nga tangaw', 'bugburn', 'bug burn', 'reddish brown', 'pula-pula'],
        'identify': [
            L('Black bugs suck the stems: deadheart, reddish-brown leaves, and fewer tillers. In bad '
              'cases the whole field looks burnt (bug burn).',
              'Sinisipsip ng atangya ang tangkay: deadheart, mamula-mulang kayumangging dahon, at '
              'kaunting suwi. Kapag malala, mukhang sunog ang buong palayan (bug burn).',
              'Supsupon sa tangaw ang punoan: deadheart, pula-brown nga dahon, ug gamay nga saha. '
              'Kung grabe, morag nasunog ang tibuok uma (bug burn).',
              ('harmful', 'chart')),
        ],
        'serious_when': L(
            'Serious at more than 10 bugs per hill in early tillering, or more than 20 per hill '
            'from mid tillering on.',
            'Malala na kapag higit 10 atangya bawat puno sa maagang pagsuwi, o higit 20 bawat puno '
            'mula gitna ng pagsuwi.',
            'Grabe na kung kapin sa 10 ka tangaw matag puno sa sayong pagsaha, o kapin sa 20 matag '
            'puno gikan sa tunga sa pagsaha.',
            ('palaycheck', 'p. 48')),
        'do_now': [
            L('Count the bugs on several hills in the early morning or late afternoon.',
              'Bilangin ang atangya sa ilang puno nang maaga o hapon.',
              'Ihapa ang tangaw sa pipila ka puno sayo sa buntag o hapon.',
              ('palaycheck', 'p. 48')),
            _FRIENDLY_INSECTS,
        ],
        'dont': [_LAST_RESORT, _TOO_MUCH_N],
        'next_season': [_SYNC_PLANTING],
    },

    'planthopper': {
        'category': 'pest',
        'name': L('Brown planthopper', 'Kayumangging hanip (ngusong kabayo)', 'Brown planthopper (hanip)'),
        'aliases': ['planthopper', 'plant hopper', 'hopper', 'bph', 'hanip', 'ngusong kabayo',
                    'hopperburn', 'hopper burn', 'nalaya', 'nauga', 'yellow patches'],
        'identify': [
            L('Plants turn yellow and dry up quickly, in patches (hopperburn). The insects stay at the '
              'base of the plant, not on the leaves.',
              'Naninilaw at mabilis matuyo ang tanim, pa-patse-patse (hopperburn). Nasa puno ng tanim '
              'ang insekto, hindi sa dahon.',
              'Mo-dalag ug dali mamala ang tanom, por-patse (hopperburn). Naa sa punoan sa tanom ang '
              'insekto, dili sa dahon.',
              ('harmful', 'chart'), ('hopper', 'p. 1')),
        ],
        'serious_when': L(
            'Serious at more than 25 insects per hill (early tillering), 50 (mid tillering to '
            'flowering), or 100 (milk stage to maturity).',
            'Malala na kapag higit 25 insekto bawat puno (maagang pagsuwi), 50 (gitna ng pagsuwi '
            'hanggang pamumulaklak), o 100 (paggatas hanggang paghinog).',
            'Grabe na kung kapin sa 25 ka insekto matag puno (sayong pagsaha), 50 (tunga sa pagsaha '
            'hangtod pagpamulak), o 100 (pagluto sa lugas hangtod paghinog).',
            ('palaycheck', 'p. 48')),
        'do_now': [
            L('Check the base of the plants, where planthoppers live, in the early morning or late '
              'afternoon.',
              'Silipin ang puno ng tanim, kung saan nakatira ang hanip, nang maaga o hapon.',
              'Susiha ang punoan sa tanom, diin nagpuyo ang hanip, sayo sa buntag o hapon.',
              ('hopper', 'p. 1'), ('palaycheck', 'p. 48')),
            L('Protect friendly insects: spiders eat planthoppers.',
              'Alagaan ang kaibigang insekto: kinakain ng gagamba ang hanip.',
              'Atimana ang higala nga insekto: kan-on sa lawalawa ang hanip.',
              ('palaycheck', 'p. 51'), ('hopper', 'p. 2')),
        ],
        'dont': [
            _NO_EARLY_SPRAY,
            L('If spraying is really needed, spray the base of the plant, not the leaves. Ask an '
              'agriculturist first.',
              'Kung talagang kailangang mag-spray, sa puno ng tanim i-spray, hindi sa dahon. Magtanong '
              'muna sa agriculturist.',
              'Kung gikinahanglan gyud mag-spray, sa punoan sa tanom i-spray, dili sa dahon. Pangutana '
              'una sa agriculturist.',
              ('hopper', 'p. 1')),
            _TOO_MUCH_N,
        ],
        'next_season': [
            L('Plant a variety resistant to planthoppers and change varieties every two years. Plant '
              'together with your neighbors after a rest period.',
              'Magtanim ng barayting matibay sa hanip at magpalit ng barayti tuwing ikalawang taon. '
              'Sabay-sabay magtanim kasama ang kapitbahay matapos ipahinga ang lupa.',
              'Pagtanom og barayti nga lig-on batok sa hanip ug ilisi ang barayti matag ikaduhang '
              'tuig. Dungan mo og tanom sa silingan human pahulaya ang yuta.',
              ('hopper', 'p. 1')),
        ],
    },

    'golden_apple_snail': {
        'category': 'pest',
        'name': L('Golden apple snail', 'Golden kuhol', 'Golden kuhol'),
        'aliases': ['snail', 'snails', 'kuhol', 'golden kuhol', 'golden apple snail', 'gas',
                    'missing hills', 'pink eggs', 'pink nga itlog', 'rosas na itlog',
                    'floating leaves', 'naglutaw'],
        'identify': [
            L('Missing hills and floating pieces of rice plants, mostly 2-3 weeks after '
              'transplanting. Bright pink egg masses on stems and stakes.',
              'May nawawalang puno at palutang-lutang na piraso ng palay, kadalasan 2-3 linggo matapos '
              'maglipat-tanim. May matingkad na rosas na kumpol ng itlog sa tangkay at tulos.',
              'Naay nawala nga puno ug naglutaw nga piraso sa humay, kasagaran 2-3 ka semana human sa '
              'pagbalhin-tanom. Naay hayag nga pink nga pungpong sa itlog sa punoan ug istaka.',
              ('harmful', 'chart'), ('snail', 'slides 7, 13')),
        ],
        'serious_when': L(
            'Serious when more than 10% of the field has missing or snail-damaged hills at 14 days '
            'after transplanting or seeding.',
            'Malala na kapag higit 10% ng palayan ang may nawala o sirang puno dahil sa kuhol, 14 '
            'araw matapos magtanim.',
            'Grabe na kung kapin sa 10% sa uma ang adunay nawala o nadaot nga puno tungod sa kuhol, '
            '14 ka adlaw human sa pagtanom.',
            ('palaycheck', 'p. 49')),
        'do_now': [
            L('Hand-pick snails and pink egg masses in the morning and afternoon, when they are most '
              'active.',
              'Pulutin ang kuhol at rosas na itlog sa umaga at hapon, kung kailan sila pinakaaktibo.',
              'Pamupoa ang kuhol ug pink nga itlog sa buntag ug hapon, kung kanus-a sila pinaka-aktibo.',
              ('snail', 'slide 15')),
            L('Put leaves of gabi, banana, papaya, or kangkong as bait, then collect the snails that '
              'gather.',
              'Maglagay ng dahon ng gabi, saging, papaya, o kangkong bilang pain, saka pulutin ang '
              'mga kuhol na nagtipon.',
              'Butangi og dahon sa gabi, saging, kapayas, o kangkong ingon pain, dayon pamupoa ang '
              'mga kuhol nga nagtapok.',
              ('snail', 'slide 15')),
            L('Keep the water shallow (2-3 cm) from 3 days after transplanting, and drain now and '
              'then to slow the snails.',
              'Panatilihing mababaw ang tubig (2-3 cm) mula 3 araw matapos maglipat-tanim, at '
              'patuyuin paminsan-minsan para bumagal ang kuhol.',
              'Huptan nga mabaw ang tubig (2-3 cm) gikan sa 3 ka adlaw human sa pagbalhin-tanom, ug '
              'hubsi usahay aron mohinay ang kuhol.',
              ('snail', 'slides 25-26')),
            L('Put a wire or bamboo screen at the water inlets and outlets.',
              'Maglagay ng screen na alambre o kawayan sa daluyan ng tubig papasok at palabas.',
              'Butangi og screen nga alambre o kawayan sa agianan sa tubig pasulod ug pagawas.',
              ('palaycheck', 'p. 51')),
        ],
        'dont': [
            L("Don't flood the field deep while the plants are young. Snails move and feed more in "
              'deep water.',
              'Huwag lunurin sa malalim na tubig ang palayan habang bata pa ang tanim. Mas gumagalaw '
              'at kumakain ang kuhol sa malalim na tubig.',
              'Ayaw pabahaa og lawom ang uma samtang batan-on pa ang tanom. Mas maglihok ug mokaon '
              'ang kuhol sa lawom nga tubig.',
              ('snail', 'slides 14, 25')),
            L('Use chemicals only as a last resort, when other methods fail.',
              'Gumamit lang ng kemikal bilang huling paraan, kapag hindi umubra ang iba.',
              'Gamit ra og kemikal ingon kataposang paagi, kung dili molampos ang uban.',
              ('snail', 'slide 20')),
        ],
        'next_season': [
            L('During the last harrowing, make small canals where snails gather for collection. Let '
              'ducks into the field after harvest until the last harrowing.',
              'Sa huling pagsusuyod, gumawa ng maliliit na kanal kung saan magtitipon ang kuhol. '
              'Pakawalan ang mga pato sa palayan pagkatapos umani hanggang sa huling pagsusuyod.',
              'Sa kataposang pagsuyod, paghimo og gagmay nga kanal diin magtapok ang kuhol. Buhii ang '
              'mga itik sa uma human sa ani hangtod sa kataposang pagsuyod.',
              ('snail', 'slides 17, 21')),
        ],
    },

    'blast': {
        'category': 'disease',
        'name': L('Rice blast', 'Mata-mata (rice blast)', 'Blast (mata-mata)'),
        'aliases': ['blast', 'rice blast', 'mata-mata', 'matamata', 'diamond', 'diamond-shaped',
                    'neck rot', 'neck blast', 'leaf spot', 'leaf spots', 'batik', 'tulbok',
                    'kulay abo'],
        'identify': [
            L('Diamond-shaped spots on the leaves, gray in the center with reddish-brown edges. With '
              'neck blast, the neck of the panicle rots and the grains are half-filled.',
              'Hugis-diamanteng batik sa dahon, abuhin sa gitna at mapula-pula ang gilid. Kapag neck '
              'blast, nabubulok ang batok ng uhay at kalahati lang ang laman ng butil.',
              'Porma-diamante nga tulbok sa dahon, abuhon sa tunga ug pula-pula ang ngilit. Kung neck '
              'blast, madunot ang liog sa uhay ug katunga ra ang sulod sa lugas.',
              ('blast_shb', 'p. 2'), ('palaycheck', 'p. 72')),
        ],
        'serious_when': L(
            'Serious when more than 30% of the field has leaf blast (mid to maximum tillering), or '
            'more than 10% has neck or panicle blast (flowering to milk stage).',
            'Malala na kapag higit 30% ng palayan ang may leaf blast (gitna hanggang pinakamaraming '
            'suwi), o higit 10% ang may neck o panicle blast (pamumulaklak hanggang paggatas).',
            'Grabe na kung kapin sa 30% sa uma ang adunay leaf blast (tunga hangtod kinadaghang '
            'saha), o kapin sa 10% ang adunay neck o panicle blast (pagpamulak hangtod pagluto).',
            ('palaycheck', 'p. 49')),
        'do_now': [
            L('If you can, flood the field. Water lowers blast, especially in rainfed fields.',
              'Kung kaya, patubigan ang palayan. Nababawasan ng tubig ang mata-mata, lalo na sa '
              'sahod-ulan.',
              'Kung kaya, patubigi ang uma. Makunhoran sa tubig ang blast, labi na sa uma nga '
              'nagsalig sa ulan.',
              ('blast_shb', 'p. 2'), ('diseases', 'slide 29')),
        ],
        'dont': [
            L("Don't walk through the field while the leaves are wet. It spreads the disease.",
              'Huwag lumusong sa palayan habang basa pa ang dahon. Naikakalat nito ang sakit.',
              'Ayaw paglakaw sa uma samtang basa pa ang dahon. Mokaylap ang sakit tungod niini.',
              ('blast_shb', 'p. 2')),
            _TOO_MUCH_N,
            _ASK_BEFORE_FUNGICIDE,
        ],
        'next_season': [
            L('Use a blast-resistant variety, and burn or plow under the sick stubble after harvest.',
              'Gumamit ng barayting matibay sa mata-mata, at sunugin o araruhin ang pinaggapasang may '
              'sakit matapos umani.',
              'Gamita ang barayti nga lig-on batok sa blast, ug sunoga o daroha ang dagami nga '
              'masakiton human sa ani.',
              ('blast_shb', 'p. 2')),
        ],
    },

    'bacterial_leaf_blight': {
        'category': 'disease',
        'name': L('Bacterial leaf blight', 'Bacterial leaf blight (BLB)', 'Bacterial leaf blight (BLB)'),
        'aliases': ['blb', 'bacterial', 'bacterial leaf blight', 'leaf blight', 'blight',
                    'yellow stripe', 'yellow stripes', 'orange', 'dilaw', 'dalag', 'naninilaw',
                    'nangalaya', 'wilting', 'ooze', 'kresek'],
        'identify': [
            L('Water-soaked to yellow-orange stripes on the leaf edges and tips that move down the '
              'leaf. Young plants may wilt. Yellow ooze may show in the early morning.',
              'Basang-basa hanggang dilaw-kahel na guhit sa gilid at dulo ng dahon na bumababa sa '
              'dahon. Maaaring malanta ang batang tanim. May dilaw na katas sa umaga.',
              'Morag basa hangtod dalag-orange nga linya sa ngilit ug tumoy sa dahon nga molugsong '
              'sa dahon. Mahimong malaya ang batan-on nga tanom. Naay dalag nga duga sa buntag.',
              ('blb', 'p. 1'), ('palaycheck', 'p. 72')),
        ],
        'serious_when': L(
            'Serious when more than 30% of the field has BLB, from mid tillering onward.',
            'Malala na kapag higit 30% ng palayan ang may BLB, mula gitna ng pagsuwi.',
            'Grabe na kung kapin sa 30% sa uma ang adunay BLB, gikan sa tunga sa pagsaha.',
            ('palaycheck', 'p. 49')),
        'do_now': [
            L('If it is severe, drain the field to lower the humidity.',
              'Kung malala, patuyuin ang palayan para bumaba ang halumigmig.',
              'Kung grabe, hubsi ang uma aron mokunhod ang kaumog.',
              ('blb', 'p. 2')),
            L("Stop irrigation water from flowing from a sick field into others.",
              'Pigilan ang tubig-irigasyon na dumaloy mula sa may sakit na palayan papunta sa iba.',
              'Pugngi ang tubig sa irigasyon nga moagas gikan sa masakiton nga uma ngadto sa uban.',
              ('blb', 'p. 2'), ('diseases', 'slide 14')),
            L('Clean tools used in a sick field before using them in another.',
              'Linisin ang gamit na ginamit sa may sakit na palayan bago gamitin sa iba.',
              'Hinloi ang galamiton nga gigamit sa masakiton nga uma sa dili pa gamiton sa uban.',
              ('diseases', 'slide 14')),
            L('Remove weeds on the bunds; they host the bacteria.',
              'Alisin ang damo sa pilapil; doon nabubuhay ang bakterya.',
              'Ibton ang sagbot sa pilapil; didto mabuhi ang bakterya.',
              ('blb', 'p. 2')),
        ],
        'dont': [
            L("Don't put too much nitrogen. Split it into smaller applications.",
              'Huwag sobrahan ang nitroheno. Hatiin sa ilang maliliit na paglalagay.',
              'Ayaw sobrahi ang nitrogen. Bahina sa pipila ka gamay nga pagbutang.',
              ('blb', 'p. 2')),
        ],
        'next_season': [
            L('Use clean seed of a resistant variety, handle seedlings gently when transplanting, '
              'and plow and dry the stubble after harvest.',
              'Gumamit ng malinis na binhi ng barayting matibay, ingatan ang punla sa paglilipat, at '
              'araruhin at patuyuin ang pinaggapasan matapos umani.',
              'Gamita ang limpyo nga binhi sa barayti nga lig-on, amping-ampingi ang semilya sa '
              'pagbalhin, ug daroha ug pauga ang dagami human sa ani.',
              ('blb', 'p. 2')),
        ],
    },

    'sheath_blight': {
        'category': 'disease',
        'name': L('Sheath blight', 'Sheath blight', 'Sheath blight'),
        'aliases': ['sheath blight', 'sheath', 'shb', 'lapak', 'oval spots', 'gray spots',
                    'abuhin', 'lodging', 'natumba', 'natumba ang humay'],
        'identify': [
            L('Oval gray spots with brown edges on the leaf sheaths near the water line, seen from '
              'maximum tillering onward.',
              'Hugis-itlog na abuhing batik na may kayumangging gilid sa lapak malapit sa tubig, '
              'makikita mula sa pinakamaraming suwi.',
              'Porma-itlog nga abuhon nga tulbok nga brown ang ngilit sa lapak duol sa tubig, makita '
              'gikan sa kinadaghang saha.',
              ('diseases', 'slides 18, 20'), ('blast_shb', 'p. 1')),
        ],
        'serious_when': L(
            'Serious when more than 40% of the field has sheath blight (mid tillering to milk stage).',
            'Malala na kapag higit 40% ng palayan ang may sheath blight (gitna ng pagsuwi hanggang '
            'paggatas).',
            'Grabe na kung kapin sa 40% sa uma ang adunay sheath blight (tunga sa pagsaha hangtod '
            'pagluto).',
            ('palaycheck', 'p. 49')),
        'do_now': [
            L('Drain the field for a few days at maximum tillering.',
              'Patuyuin ang palayan nang ilang araw sa pinakamaraming suwi.',
              'Hubsi ang uma sulod sa pipila ka adlaw sa kinadaghang saha.',
              ('diseases', 'slide 23')),
            L('Remove weeds in the paddy and on the bunds.',
              'Alisin ang damo sa palayan at sa pilapil.',
              'Ibton ang sagbot sa uma ug sa pilapil.',
              ('diseases', 'slide 23'), ('blast_shb', 'p. 1')),
        ],
        'dont': [_TOO_MUCH_N, _ASK_BEFORE_FUNGICIDE],
        'next_season': [
            L('Use the right seeding rate and wider spacing, and plow under the sick stubble after '
              'harvest.',
              'Sundin ang tamang dami ng binhi at mas maluwag na pagitan, at araruhin ang '
              'pinaggapasang may sakit matapos umani.',
              'Sunda ang sakto nga gidaghanon sa binhi ug mas lapad nga gilay-on, ug daroha ang '
              'dagami nga masakiton human sa ani.',
              ('blast_shb', 'p. 1'), ('diseases', 'slide 23')),
        ],
    },

    'tungro': {
        'category': 'disease',
        'name': L('Tungro', 'Tungro', 'Tungro'),
        'aliases': ['tungro', 'stunted', 'bansot', 'kubo', 'mottled', 'yellow orange',
                    'yellow-orange', 'green leafhopper', 'leafhopper', 'berdeng ngusong kabayo'],
        'identify': [
            L('Young leaves are mottled, older leaves turn yellow to orange, and the plants are '
              'stunted. It is a virus spread by green leafhoppers.',
              'Batik-batik ang batang dahon, naninilaw hanggang kahel ang matandang dahon, at bansot '
              'ang tanim. Virus ito na ikinakalat ng berdeng ngusong kabayo.',
              'Mantsa-mantsa ang batan-on nga dahon, mo-dalag hangtod orange ang tigulang nga dahon, '
              'ug kubo ang tanom. Virus kini nga ikaylap sa berde nga leafhopper.',
              ('diseases', 'slides 30-31')),
            L('Nitrogen shortage looks similar, but then the whole plant is yellowish green and the '
              'leaf tips turn brown.',
              'Kahawig nito ang kulang sa nitroheno, pero doon ay madilaw-dilaw na berde ang buong '
              'tanim at kayumanggi ang dulo ng dahon.',
              'Susama niini ang kulang sa nitrogen, apan didto dalag-berde ang tibuok tanom ug brown '
              'ang tumoy sa dahon.',
              ('palaycheck', 'p. 72')),
        ],
        'serious_when': L(
            'Serious when more than 20% of the field has tungro in early tillering, or more than 40% '
            'from mid to maximum tillering.',
            'Malala na kapag higit 20% ng palayan ang may tungro sa maagang pagsuwi, o higit 40% '
            'mula gitna hanggang pinakamaraming suwi.',
            'Grabe na kung kapin sa 20% sa uma ang adunay tungro sa sayong pagsaha, o kapin sa 40% '
            'gikan sa tunga hangtod kinadaghang saha.',
            ('palaycheck', 'p. 49')),
        'do_now': [
            L("Check your field and your neighbors' fields. The critical time is about 6 weeks "
              'after transplanting.',
              'Silipin ang palayan mo at ng mga kapitbahay. Kritikal ang mga 6 na linggo matapos '
              'maglipat-tanim.',
              'Susiha ang imong uma ug ang sa mga silingan. Kritikal ang mga 6 ka semana human sa '
              'pagbalhin-tanom.',
              ('diseases', 'slide 35')),
            L('Look for green leafhoppers, which carry the virus.',
              'Hanapin ang berdeng ngusong kabayo, na nagdadala ng virus.',
              'Pangitaa ang berde nga leafhopper, nga nagdala sa virus.',
              ('diseases', 'slide 35')),
        ],
        'dont': [],
        'next_season': [
            L('Rest the field (fallow), plant together with neighbors, use a resistant variety, and '
              'plow the stubble right after harvest.',
              'Ipahinga ang lupa, sabay-sabay magtanim kasama ang kapitbahay, gumamit ng barayting '
              'matibay, at araruhin agad ang pinaggapasan matapos umani.',
              'Pahulaya ang yuta, dungan og tanom sa silingan, gamita ang barayti nga lig-on, ug '
              'daroha dayon ang dagami human sa ani.',
              ('diseases', 'slide 36')),
        ],
    },
}

SECTIONS = ('identify', 'serious_when', 'do_now', 'dont', 'next_season')

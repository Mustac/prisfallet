"""Sort a product into a Prisfallet subcategory from its shop URL path and name.

Rules are checked in order; the first match wins. The URL path of most Norwegian
shops already contains the shop's own category (e.g. "gaming/spill/..."), so it is
checked together with the product name.
"""
import re

# (subcategory id, regex) — order matters: specific before general
RULES = [
    # --- early, very specific
    ("fridges", r"minikjøleskap"),
    ("security", r"overvåk(n)?ingskamera|eufycam|ringeklokke|video doorbell|arlo|ring (stick|spotlight|video)"),
    ("cooling", r"cpu-kjøler|cpu kjøler|kjølepasta|\bcooler\b(?! master m)"),
    ("smarthome", r"fotoramme|frameo"),
    ("tablets", r"apple pencil|stylus|ipad"),
    ("climate", r"adax|panelovn|varmeovn|oljeovn|termostat|puresense|avfukter"),
    ("machines", r"kenwood (chef|kmix)|chef xl"),
    ("hair", r"varmluftsbørste|varmluftstyler|multistyler|airstyle|flexstyle|hårstyler|\bstyler\b|magic style"),
    ("shaving", r"hairclipper|hårklipper|clipper"),
    ("oral", r"philips hx\d{4}"),
    ("speakers", r"marshall (willen|acton|stanmore|emberton|middleton|woburn|tufton|kilburn)"),
    ("pcacc", r"air duster|gas duster|mission sg (esd|ggx|bit|air)|gaming-skrivebord|gamingbord|soundshield"),
    ("watches", r"oura ring|smartring"),
    ("wellness", r"withings body|personvekt|led facemask|ansiktsmaske"),
    ("garden", r"\bava (go|easy|evolution)|høytrykksvasker|vindusvaskerobot|juletre"),
    ("smallapp", r"sandwich maker|symaskin"),
    ("smarthome", r"aqara|smart ?plug"),
    ("audio", r"yeti orb|mikrofon"),
    ("controllers", r"thrustmaster"),
    ("washers", r"bosch wq|electrolux edi|edh\d|ew\d"),
    ("wellness", r"øyemaske|massasje|massage"),
    # --- gaming
    ("vr", r"\bvr\b|virtual reality|quest 3|playstation vr|psvr"),
    ("controllers", r"kontroller|controller|dualsense|gamepad|joy-con|ratt og pedal|racing wheel|styrespak"),
    ("consoles", r"spillkonsoll|playstation 5 (slim|pro)|ps5 (slim|pro|digital)|xbox series|nintendo switch 2(?! .*spill)|steam deck|rog ally|legion go|/spillkonsoller/"),
    ("games", r"/spill/|\(ps5\)|\(ps4\)|\(switch 2?\)|\(xbox|\(pc\)|ps5-spill|switch-spill|videospill"),
    ("gheadsets", r"gaming ?headset|gamingheadset|arctis|hyperx cloud|razer (kraken|blackshark|barracuda)|logitech g\d{3}.*headset|steelseries.*headset"),
    ("chairs", r"gamingstol|gaming chair|gaming-stol|kontorstol|/stoler/"),
    ("toys", r"funko|julekalender|actionfigur|\bfigur\b"),
    ("pcacc", r"pc-veske|laptopveske|laptopsekk|datasekk|støvblåser|luftblåser|trykkluft"),
    ("desktops", r"\bbuild \d{3}\b|i[579]/\d+/\d+tb|r[579]/\d+/\d+tb"),
    ("shaving", r"hodebarberer"),
    ("climate", r"airthings|radon|luftkvalitet|skotørker"),
    # --- computers
    ("gpu", r"skjermkort|geforce|radeon rx|rtx \d{4}"),
    ("cpu", r"prosessor|\bcpu\b|ryzen \d \d{4}x|core i\d-\d{4,5}k|core ultra \d \d{3}k"),
    ("motherboards", r"hovedkort|motherboard"),
    ("ram", r"\bddr[45]\b|minnebrikke|\bram\b"),
    ("storage", r"\bssd\b|harddisk|\bhdd\b|nvme|minnepenn|minnekort|usb-stick|\bsd(xc|hc)?\b.*kort|ekstern disk"),
    ("psu", r"strømforsyning|\bpsu\b|\d{3,4}w (gold|bronze|platinum)"),
    ("cases", r"kabinett|mid tower|midi tower|pc-kabinett"),
    ("cooling", r"cpu-kjøler|kjøler|aio\b|vifte|fan\b"),
    ("keyboards", r"tastatur|keyboard"),
    ("mice", r"\bmus\b|gamingmus|\bmouse\b|musematte"),
    ("printers", r"printer|skriver|blekk|toner|ecotank|smart tank"),
    ("network", r"router|mesh|wifi|wi-fi|nettverk|switch \d+-port|access point|deco x|orbi"),
    ("monitors", r"skjerm(?!kort|beskytter|feste)|monitor|gamingskjerm"),
    ("laptops", r"bærbar|barbar-pc|laptop|macbook|chromebook|notebook|copilot\+ pc|zenbook|vivobook|ideapad|thinkpad|surface laptop"),
    ("desktops", r"stasjonær|gaming-pc|gaming pc|mini-pc|mini pc|imac|mac mini|mac studio|komplett-pc"),
    # --- phones & tablets
    ("phoneacc", r"deksel|skjermbeskytter|case\b|smarttag|airtag|tracker|mobilholder"),
    ("watches", r"smartklokke|smartwatch|apple watch|galaxy watch|pixel watch|garmin|aktivitetsarmbånd|fitbit|watch fit|watch gt|amazfit|polar\b|suunto|coros"),
    ("tablets", r"nettbrett|\bipad\b|galaxy tab|tablet|lesebrett|kindle|kobo"),
    ("phones", r"mobiltelefon|smarttelefon|smartphone|iphone|galaxy [asz]\d|pixel \d|oneplus|xiaomi|redmi|motorola|oppo find|nothing phone|/mobil/"),
    ("chargers", r"lader|charger|powerbank|kabel|cable|usb-c hub|dokkingstasjon|docking|adapter"),
    # --- sound & tv
    ("soundbars", r"lydplanke|soundbar|subwoofer|hjemmekino|sub mini|arc ultra"),
    ("tv", r"\btv\b|oled|qled|mini led tv|projektor|projector|/tv/"),
    ("earbuds", r"ørepropper|earbuds|true wireless|airpods|buds|in-ear|tws"),
    ("headphones", r"hodetelefon|headphone|over-ear|on-ear|wh-1000|quietcomfort"),
    ("speakers", r"høyttaler|speaker|partybox|soundlink|sonos (era|move|roam|five|play)|jbl (flip|charge|clip|go|xtreme)|bluetooth-høyttaler|radio|platespiller|turntable"),
    ("music", r"dj-|dj controller|ddj-|mikser|gitar|piano|keyboard-instrument|synth"),
    # --- photo
    ("drones", r"drone|dji (mini|air|mavic|avata|neo)"),
    ("actioncams", r"actionkamera|gopro|insta360 x|osmo action|360"),
    ("gimbals", r"gimbal|osmo mobile|dji rs"),
    ("cameras", r"kamera|camera|objektiv|eos r|alpha a?\d|lumix|fujifilm x|nikon z"),
    ("webcams", r"webkamera|webcam"),
    ("audio", r"mikrofon|microphone|podcast|rodecaster"),
    ("calibration", r"kalibrering|spyder|calibrite"),
    ("bags", r"fotoveske|kamerasekk|stativ|tripod|selfie"),
    # --- appliances (hvitevarer)
    ("washers", r"vaskemaskin|tørketrommel|tørkeskap|washing machine|dryer|vask og tørk|vask-tork"),
    ("fridges", r"kjøleskap|fryser|kombiskap|vinskap|fridge|freezer"),
    ("dishwashers", r"oppvaskmaskin|dishwasher"),
    ("ovens", r"stekeovn|komfyr|platetopp|induksjon|kokeplate|ventilator|kjøkkenvifte|avtrekk|mikrobølgeovn|microwave"),
    # --- home
    ("robovac", r"robotstøvsuger|robot vacuum|roborock|roomba|dreame (x|l)\d|ecovacs|deebot"),
    ("vacuums", r"støvsuger|vacuum|våt/tørr|vaskemopp|wet ?dry|dyson v\d|gulvvasker"),
    ("garden", r"robotgressklipper|gressklipper|hage|trimmer.*gress|løvblåser|høytrykksspyler|grill(?!pinne)|lawn|mower"),
    ("climate", r"luftrenser|avfukter|luftfukter|varmepumpe|panelovn|vifte|ovn\b|air purifier|heater|klimaanlegg|sensibo"),
    ("security", r"overvåkingskamera|ringeklokke|doorbell|alarm|sikkerhet|ring (stick|video)|arlo|eufy.*cam"),
    ("smarthome", r"smarthus|smart home|smartpære|hue\b|google home|nest hub|echo\b|alexa|homey|smartplugg|smart lys"),
    ("lighting", r"lampe|lykt|stormlykt|lys(slynge|lenke)|led-list|belysning|lantern"),
    ("laundry", r"strykejern|steamer|dampstryker|\biron\b|puregliss"),
    # --- kitchen
    ("coffee", r"kaffemaskin|espressomaskin|kaffetrakter|kaffekvern|nespresso|dolce gusto|melkeskummer|coffee|espresso|moccamaster|french press|presskanne"),
    ("machines", r"kjøkkenmaskin|stavmikser|blender|foodprocessor|food processor|håndmikser|kitchenaid|cooking chef|assistent|mums\d"),
    ("smallapp", r"airfryer|airfrier|varmluftsfriter|vannkoker|kettle|brødrister|toaster|sandwichgrill|vaffeljern|riskoker|slowcooker|sous vide|kjøkkenvekt|krydderkvern|woodfire|ninja"),
    ("knives", r"kniv|knife"),
    ("pans", r"stekepanne|sautèpanne|sautepanne|wokpanne|\bpanne\b|frying pan"),
    ("pots", r"gryte|kjele|grytesett|kasserolle|\bpot\b"),
    ("boards", r"skjærebrett|skjærefjøl|cutting board"),
    ("ovenware", r"ildfast|ovnfast|bakeform|langpanne|pizzasten|pizza stone"),
    ("tableware", r"tallerken|asjett|glass\b|kopp|krus|bestikk|servise|bolle|skål|ramekin|karaffel"),
    ("food", r"sjokolade|\bte\b|krydder(?!kvern)|trøffel|gaveeske|delikatesse"),
    ("utensils", r"redskap|termometer|visp|slikkepott|rivjern|mandolin|salatslynge|sil\b|tang\b|spade\b|øse|hvitløkspresse|saks\b"),
    # --- beauty & health
    ("oral", r"tannbørste|toothbrush|munnskyll|tannkrem|oral-b|sonicare|vannflosser|munnstykke|irrigator"),
    ("shaving", r"barbermaskin|shaver|trimmer|skjeggtrimmer|hårklipper|ipl|epilator|lumea"),
    ("hair", r"hårføner|føner|hair ?dryer|glattetang|krølltang|airwrap|hårstyler|varmebørste|stylingbørste|supersonic"),
    ("skincare", r"parfyme|eau de|hudpleie|serum|ansiktskrem|sminke|mascara|skincare"),
    ("wellness", r"massasje|massage|massasjepistol|kompresjon|vekt\b.*kropp|personvekt|blodtrykk|helse"),
    # --- toys
    ("baby", r"barnevogn|bilstol|babycall|babymonitor|stellebord|tåteflaske|bæresele|babynest|sittevogn|\bbaby"),
    ("lego", r"\blego\b"),
    ("toys", r"leke|leketøy|dukke|bamse|brettspill|puslespill|\btoy|playmobil|barbie|hot wheels|nerf|fjernstyrt|rc-bil"),
    # --- sports & outdoor
    ("clothing", r"skirt|skjort\b|skjørt|singlet|\bshorts?\b|socks|strømpe|strompe|jersey|chinos|sweat|\btop\b|tee\b|polo\b|leggings|tights|hettegenser|crew\b|pants|jacket|parka|vest\b"),
    ("outdoor", r"tarp|telt|sovepose|liggeunderlag|drikkeflaske|termos|primus|stormkjøkken|oppblåsbar|oppblasbar|kajakk|padle|hodelykt|tursekk|ryggsekk|dagstursekk|klatre|innlegg|spisepinner|campfire"),
    ("winter", r"\bski\b|skisko|skistav|staver|langrenn|alpin|slalåm|snowboard|skøyter|skiskøyter|akebrett|truger|feller\b|skismøring|skibinding"),
    ("shoes", r"sko\b|løpesko|lopesko|joggesko|sneakers?|støvler?|stovler?|sandal|tursko|fotballsko|innesko|vintersko|boots"),
    ("clothing", r"jakke|bukse|genser|hoodie|t-skjorte|tskjorte|skjorte|tights|shorts|vest\b|dunjakke|parkas|regnjakke|ullundertøy|undertøy|sokker|lue\b|hansker|votter|truse|bh\b|kjole|skjørt|treningsoverdel|fleece|softshell|anorakk|dress\b"),
    ("bikes", r"sykkel|el-sparkesykkel|sparkesykkel|scooter|ninebot|segway|elsykkel|bike\b|mtb|terrengsykkel|grussykkel"),
    ("fitness", r"tredemølle|treningssykkel|romaskin|manualer|kettlebell|treningsmatte|fitness|spinning"),
    ("outdoor", r"telt|sovepose|tursekk|hodelykt|ski\b|skisko|turutstyr|friluft|jakke|kajakk|fiske"),
]
RULES = [(sub, re.compile(rx, re.I)) for sub, rx in RULES]

# Shop URL path segments -> subcategory, used when the name alone is ambiguous
PATH_HINTS = [
    ("/barbar-pc/", "laptops"), ("/pc-baerbar", "laptops"), ("/gaming-laptop", "laptops"),
    ("/stasjonaer-pc", "desktops"), ("/gaming-pc", "desktops"),
    ("/pc-skjerm", "monitors"), ("/gamingskjerm", "monitors"), ("/skjermer/", "monitors"),
    ("/mobiltelefon", "phones"), ("/nettbrett", "tablets"), ("/smartklokke", "watches"),
    ("/hodetelefoner", "headphones"), ("/horetelefoner", "headphones"), ("/ørepropper", "earbuds"),
    ("/hoyttalere", "speakers"), ("/høyttaler", "speakers"), ("/lydplanke", "soundbars"),
    ("/tv/", "tv"), ("/projektor", "tv"),
    ("/spill/", "games"), ("/spillkonsoll", "consoles"), ("/gaming-tilbehor", "controllers"), ("/gaming-headset", "gheadsets"),
    ("/vaskemaskin", "washers"), ("/torketrommel", "washers"), ("/vask-og-tork", "washers"),
    ("/kjoleskap", "fridges"), ("/fryser", "fridges"), ("/kjol-og-frys", "fridges"),
    ("/oppvaskmaskin", "dishwashers"), ("/komfyr", "ovens"), ("/stekeovn", "ovens"), ("/platetopp", "ovens"),
    ("/robotstovsuger", "robovac"), ("/stovsuger", "vacuums"),
    ("/kaffe", "coffee"), ("/kjokkenmaskin", "machines"), ("/airfryer", "smallapp"),
    ("/harfoner", "hair"), ("/rettetang", "hair"), ("/harpleie", "hair"), ("/barbering", "shaving"), ("/tannpleie", "oral"),
    ("/lego", "lego"), ("/leker", "toys"),
    ("/el-sparkesykkel", "bikes"), ("/sykkel", "bikes"), ("/trening", "fitness"),
    ("/printer", "printers"), ("/nettverk", "network"), ("/ruter", "network"),
    ("/tastatur", "keyboards"), ("/mus/", "mice"), ("/pc-mus", "mice"),
    ("/smarte-hjem", "smarthome"), ("/smarthjem", "smarthome"), ("/sikkerhet", "security"),
    ("/hage", "garden"), ("/klima", "climate"), ("/luftrenser", "climate"),
]


def _path(url: str) -> str:
    """The shop's specific category path: drop the domain, 'product' and the top-level category."""
    from urllib.parse import urlparse
    segs = [x for x in urlparse(url.lower()).path.split("/") if x]
    if segs and segs[0] in ("product", "produkt", "p"):
        segs = segs[1:]
    if len(segs) > 2:
        segs = segs[1:]
    return "/" + "/".join(segs) + "/"


def classify(name: str, url: str = "") -> str:
    path = _path(url) if url.startswith("http") else url.lower()
    text = (name or "").lower()
    # 1) product name rules (most precise)
    for sub, rx in RULES:
        if rx.search(text):
            return sub
    # 2) the shop's own category path
    for seg, sub in PATH_HINTS:
        if seg in path:
            return sub
    # 3) rules against the path text as a last resort
    for sub, rx in RULES:
        if rx.search(path):
            return sub
    return "other"


if __name__ == "__main__":
    tests = [
        ("Final Fantasy VII Remake Intergrade (Switch 2)", "gaming/spill/x"),
        ("Bosch Serie 6 induksjonstopp med ventilator PVQ89BH26E (80cm)", ""),
        ("HyperX Cloud III S Wireless gaming headset (black/red)", ""),
        ("Samsung Galaxy A17 5G smarttelefon 128GB (sort)", ""),
        ("Bosch Serie 6 Vaskemaskin WGG244ZTSN (9kg)", ""),
        ("TCL 65\" MSQLED85L 4K SQD-Mini LED TV (2026)", ""),
        ("Lenovo IdeaPad Slim 3x 15Q8X10 X1/16GB/512GB 15,3\" Copilot+ PC", ""),
        ("Epson EcoTank ET-2915 multifunksjonsskriver (sort)", ""),
        ("Cherry Xtrfy M68 PRO sort mus", ""),
        ("Nintendo Switch 2 spillkonsoll", ""),
        ("Samsung 55\" S99H 4K OLED Smart-TV", ""),
        ("Philips Sonicare 9900 Prestige", ""),
        ("LEGO Technic Ferrari", ""),
        ("Ninebot by Segway F3 D el-sparkesykkel", ""),
    ]
    for n, u in tests:
        print(f"{classify(n, u):12} {n}")

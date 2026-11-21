"""Sort a product into a Prisfallet subcategory from its shop URL path and name.

Rules are checked in order; the first match wins. The URL path of most Norwegian
shops already contains the shop's own category (e.g. "gaming/spill/..."), so it is
checked together with the product name.
"""
import re

# (subcategory id, regex) — order matters: specific before general
RULES = [
    ("dishwashers", r"electrolux e[dfs][ie]\d|oppvaskmaskin"),
    ("security", r"doorbell|dørklokke|ringeklokke|tapo d\d"),
    ("watches", r"moto watch|oneplus watch|xiaomi watch|huawei watch"),
    ("phoneacc", r"lens guard|moto tag|torras|airtag"),
    ("earbuds", r"moto (sound|buds)"),
    ("tablets", r"oneplus pad|xiaomi pad|redmi pad|lenovo tab|galaxy tab"),
    ("hair", r"hårføner|hairdryer|hair dryer"),
    ("pcacc", r"thunderbolt.*dock|docking station|stand & hub|mac mini.*(stand|hub)"),
    ("lighting", r"floor lamp|gulvlampe|smart.*bulb|tapo l\d"),
    ("soundbars", r"soundbar|lydplanke"),
    ("speakers", r"computer speaker|datahøyttaler"),
    ("tv", r"\bnebula\b"),
    ("toys", r"magical tablet|tegnetavle"),
    ("drop", r"fôrautomat|fôrdispenser|fibox|legion glasses"),
    ("watches", r"apple watch (series|se|ultra)(?!.*(bumper|skjermbeskytter|reim|band \(|lader))"),
    ("smallapp", r"brødrister|toaster|vannkoker|kettle|vaffel|våffel|slowcooker|slow cooker|crock-pot|bottle warmer|flaskevarmer"),
    ("lighting", r"ceiling lamp|taklampe|light strip|lysstripe|led strip|govee"),
    ("climate", r"air quality monitor|luftkvalitet"),
    ("smarthome", r"smart (wi-?fi )?(socket|plug)|tapo p1\d\d"),
    ("fitness", r"fitness trampoline|treningsmatte|gymstick"),
    ("printers", r"officejet|inkjet|laserjet|deskjet|ecotank|pixma"),
    ("pcacc", r"monitor arm|skjermarm|skjermholder|usb-h\d|usb hub|dokkingstasjon"),
    ("security", r"outdoor camera|utendørskamera"),
    ("chargers", r"empower bank|powerbank|power bank|turbo \d+w"),
    ("pcacc", r"(\bcase\b|etui|sleeve|deksel|cover|veske|bag\b).*(macbook|laptop|bærbar)|(macbook|laptop).*(\bcase\b|etui|sleeve|deksel|veske)"),
    ("drop", r"hedgehog|tv mount|full motion tv|motorized tv|wallmount|telemecanique|blazepod|pure ?sense psha"),
    ("fitness", r"exercise bike|treningssykkel|spinningsykkel|spinning bike"),
    ("security", r"\bpoe\b.*camera|solar-powered.*(camera|kamera)|security camera|reolink|tapo c\d"),
    ("smarthome", r"water leak|lekkasjesensor|smart home styreenhet|persienne-kontroll|ac controller|netatmo|switchbot"),
    ("vr", r"\bvr2?\b|playstation vr|bobovr|kiwidesign|quest 3"),
    ("shaving", r"kroppstrimmer|skjeggtrimmer|braun styler|beard|hårklipper|\bstyler (bt|hc)"),
    ("climate", r"handheld fan|neck fan|portable fan|takvifte|ceiling fan|bordvifte"),
    ("earbuds", r"\bwf-|soundgear|open-ear"),
    ("coffee", r"espressomaskin|espresso maker|coffeebird"),
    ("pcacc", r"etui for laptop|laptop sleeve|laptopetui|rgb strip|led strip.*argb"),
    ("ovens", r"siemens hb\d"),
    ("psu", r"elite (gold|platinum|bronze) \d{3,4}"),
    ("chargers", r"usb-c ?- ?usb-c|usb-c kabel|usb-c cable|braided .*\d+w"),
    ("gimbals", r"isteady|gimbal"),
    ("drop", r"tv-gulvstativ|gulvstativ|tv wall ?mount|wallmount|veggfeste for tv|tv-veggfeste|stativ med glassfot|andersson ats"),
    ("pcacc", r"laptop ?(backpack|sleeve|bag|veske|sekk)|laptopstativ|bag for bærbar|ryggsekk for bærbar|pc-veske|laptopsekk|datasekk"),
    ("speakers", r"soundlink|jbl (flip|charge|clip|go|xtreme|boom)|partybox|soundcore (boom|motion|select|rave)|høyttaler"),
    ("soundbars", r"tv speaker|lydplanke|soundbar"),
    ("monitors", r"odyssey|alienware aw\d|evnia|^\d\d(,\d)?\" "),
    ("car", r"dash ?cam|dashbordkamera|drivesmart|garmin drive|garmin camper|oljeplugg|motorsykkel-gps|motorsykkel gps"),
    ("mice", r"mouse ?pad|musematte"),
    ("laptops", r"swift (edge|go|air|\d)|zenbook|vivobook|ideapad|thinkpad|thinkbook|elitebook|probook|macbook|chromebook|\blaptop\b"),
    ("tv", r"prosjektor|projektor"),
    ("drop", r"sumup|betalingsterminal|kassesystem|gulvstativ for tv|tv-stativ"),
    ("phoneacc", r"\bcase\b|deksel|\bcover\b|skjermbeskytter|screen protector|screen guard|lens protector|easyglass|panzerglass|\bhoops\b|mobilholder|bumper|magsafe.*(holder|ring)"),
    ("chargers", r"maggo|usb-c adapter|\badapter\b.*\b(iphone|usb)"),
    ("gimbals", r"gimbal"),
    ("earbuds", r"\bbuds\b|nord buds|redmi buds"),
    ("watches", r"\bwatch\b(?!.*(reim|rem|strap|band|lader|charger))"),
    ("tablets", r"xiaomi pad|redmi pad"),
    ("vacuums", r"våt/tørr|våt-/tørr|wet ?dry"),
    ("garden", r"bassengrobot|for basseng|winbot|vindusrobot|vindusvask"),
    ("wellness", r"restitusjon|fotbad|recovery boot"),
    ("christmas", r"partyslynge"),
    ("watches", r"smartklokke|smartwatch|galaxy watch|\bvenu\b"),
    ("phones", r"smarttelefon|galaxy s\d\d|iphone \d"),
    ("tablets", r"nettbrett|lenovo tab\b"),
    ("tv", r"projektor|flatskjerm-tv|\bsmart-tv|\d\d\" .*\btv\b"),
    ("headphones", r"marshall monitor"),
    ("wellness", r"sleep monitor|søvnmonitor"),
    ("earbuds", r"freebuds|galaxy buds|earbuds|ørepropper|true wireless|\bin-ear|nothing ear|live beam|live flex|live buds|tune beam|tune buds|tune flex|wave flex|wave beam|powerbeats"),
    ("games", r"^(?!.*(headset|kontroller|controller|\bratt\b|wheel|mus\b|tastatur)).*(\((xbox|ps[45]|switch 2?|pc)[^)]*\)|- (microsoft )?xbox series x - |- nintendo switch 2 - |nintendo switch 2 edition)"),
    ("drones", r"fpv-drone|\bdrone\b"),
    ("psu", r"strømforsyning|\bpsu\b"),
    ("cooling", r"cpu-kjøler|cpu luftkjøler|luftkjøler|vannkjøl|\baio\b"),
    ("ovens", r"innbyggingsovn|kompaktovn|stekeovn"),
    ("garden", r"pizzaovn"),
    ("lighting", r"lava ?lamp|lavalampe"),
    ("smarthome", r"rullegardin|smartgardin|motionblinds"),
    ("audio", r"interview go|rødecaster|\brøde\b"),
    ("shoes", r"(sykkel|løpe|tur|fotball|jogge|gå|vinter|inne|terrengsykkel|landeveis|tennis|padel|innebandy)sko\b|sneakers?\b"),
    ("clothing", r"isolasjonsjakke|dunjakke|skalljakke|regnjakke|vinterjakke|softshelljakke|fleecejakke|ullgenser|baselayer"),
    ("cooling", r"kabinettvifte|case fan|aio-kjøler|vannkjøler"),
    ("security", r"sikkerhetskamera|overvåkingskamera|floodlight cam|indoor camera|outdoor camera|utendørs ?kamera|innendørs ?kamera|tapo c\d|ring (floodlight|indoor|outdoor|spotlight|stick)"),
    ("phoneacc", r"camera lens protector|kameralinsebeskytter|linsebeskytter"),
    ("webcams", r"webkamera|webcam"),
    ("monitors", r'\d\d(,\d)?" .*(gamingskjerm|skjerm|monitor)|odyssey g\d'),
    ("chargers", r"charging station|ladestasjon(?! for elbil)|trådløs lader|wireless charg"),
    ("smallapp", r"sandwichgrill|optigrill|smørbrødgrill|kontaktgrill|bordgrill|raclette"),
    ("fridges", r"drikkekjøler|minikjøler|vinkjøler"),
    ("pcacc", r"skjermarm|skjermholder|monitorarm"),
    ("lego", r"\blego\b"),
    # --- added 21 Nov: kids (before everything else, so "radiostyrt" toys don't land in electronics)
    ("climate", r"dieselvarmer|parafinovn|byggvarmer|byggtørker|vifteovn|vedovnsvifte|baderomsvarmer|gassvarmer|terrassevarmer"),
    ("build", r"sagbukk|bjelkesko|vinkelbeslag|beslag\b"),
    ("rc", r"radiostyrt|fjernstyrt|rc-bil|rc bil|\brc\b(?!-?argb)"),
    ("outdoorkids", r"akebrett|rattkjelke|kjelke|akematte|akemadrass|snøscooter for barn|sparkstøtting|trampoline|lekestue|sandkasse|huske(stativ)?\b|sklie|barneski|snowracer|\bstiga\b"),
    ("boardgames", r"brettspill|puslespill|kortspill|familiespill|selskapsspill|\bpuslespill|\bspill for barn|\bmonopoly\b|\bludo\b|\balias\b|\buno\b|\byatzy\b|\bsjakk"),
    ("dolls", r"kosedyr|\bbamse|plysj|dukke|barbie|baby born|squishmallow|\bplush"),
    ("crafts", r"\bperler\b|\bhama\b|tegnesett|malesett|tusjer|fargeblyant|modellkitt|\bleire\b|kreativ|hobbysett|tegnebrett|klistremerke"),
    # --- tools (Jula, Biltema, Clas Ohlson...)
    ("garden", r"motorsag|kjedesag|vedkløyver|hekksaks|gresstrimmer|løvblåser|gressklipper|snøfreser|snøskuffe|snøslynge"),
    ("powertools", r"drill|skrutrekker(?!sett)|slagtrekker|muttertrekker|vinkelsliper|sirkelsag|stikksag|kappsag|bajonettsag|multiverktøy|multicutter|slipemaskin|eksentersliper|båndsliper|høvel|overfres|borhammer|meiselhammer|batteridrevet (?!.*(lys|lampe|lyskaster|radio))|\b18 ?v\b(?!.*(lys|lampe|led))|batteripakke|varmluftpistol|limpistol|el-verktøy"),
    ("garden", r"høytrykks?spyler"),
    ("workshop", r"kompressor|sveis|trykkluft|\bjekk\b|garasjejekk|arbeidsbenk|verktøyvogn|verktøyskap|verktøykasse|verktøytralle|lodd(e|ing)|skruestikke|tvinge|arbeidslampe|batterilader (for )?(bil|mc|båt)|ctek|startbooster|starthjelp|arbeidsbukk"),
    ("handtools", r"verktøysett|pipenøkkel|fastnøkkel|momentnøkkel|unbrako|\bbits\b|bitssett|\btang\b|nebbtang|avbitertang|hammer|skrutrekkersett|vater|målebånd|tommestokk|kniv(sett)?\b.*(tapet|hobby)|tapetkniv|baufil|håndsag|meisel|filsett"),
    ("car", r"\bbil(pleie|vask|voks|polering|lakk|dekk|matte|matter|lader)|vindusvisker|frontrute|takboks|lastholder|sykkelholder|hengerfeste|snøkjetting|dekkskift|felg|\bmc\b|motorsykkel|motorolje|kjølervæske|spylervæske|ladekabel elbil|elbillader|bremse|tanklokk|lyspære.*(h4|h7)"),
    ("storage", r"oppbevaringshylle|lagerreol|reol\b|hyllesystem|oppbevaringskasse|oppbevaringsboks|veggpanel|verktøyoppheng|plastboks|stablekasse"),
    ("build", r"maling|pensel|malerull|fugemasse|silikon|sparkel|grunning|\blakk\b|\bbeis\b|\bstige\b|stillas|\blim\b|\btape\b|byggfolie|isolasjon|skruer|spiker|plugger"),
    ("christmas", r"julepynt|julelys|juletre|julebelysning|lysgirlander|lysslynge|lyslenke|adventsstake|adventslys|julestjerne|\bnisse|juledekor|kunstig juletre|lysgardin|lysfigur|julekule|led-lys.*(jul|stjerne)|stjerne.*led|utendørs ?lys.*jul"),
    # --- added 20 Nov: things that used to land in "Annet"
    ("laptops", r"galaxy book|bærbar pc|chromebook"),
    ("phones", r"\brealme\b|smarttelefon"),
    ("watches", r"galaxy ring|smartring|aktivitetsarmbånd"),
    ("bikes", r"grussykkel|terrengsykkel|el-sykkel|elsykkel|landeveissykkel|sparkesykkel"),
    ("teamsport", r"hockey|padel|bordtennis|rebounder|fotball(?!sko)|håndball|innebandy|tennisracket"),
    ("strollers", r"vognpose|barnevogn|\btrille\b|løpevogn|sportsvogn|sittevogn|kombivogn|duovogn|tvillingvogn|vognpakke"),
    ("carseats", r"bilstol|beltestol|babysete|isofix"),
    ("baby", r"matstol|babygym|gåstol|stellebord|babycall|bæresele"),
    ("toys", r"radiostyrt|karaoke|lekekjøkken|kjørbar|tusjer|malesett|leketøy|dukke|byggesett|puslespill|brettspill"),
    ("controllers", r"racingratt|\bratt\b"),
    ("smarthome", r"smartplugg|smart ?plug|wifi-plugg"),
    ("outdoor", r"duffel|ryggsekk|telt\b|sovepose"),
    ("cameras", r"zv-e10|systemkamera|speilrefleks|objektiv"),
    ("chairs", r"gaming-skrivebord|gamingbord"),
    # --- early, very specific
    ("fridges", r"minikjøleskap"),
    ("security", r"overvåk(n)?ingskamera|eufycam|ringeklokke|video doorbell|\barlo\b|ring (stick|spotlight|video)"),
    ("cooling", r"cpu-kjøler|cpu kjøler|kjølepasta|\bcooler\b(?! master m)"),
    ("smarthome", r"fotoramme|frameo"),
    ("tablets", r"apple pencil|stylus|\bipad|galaxy tab|nettbrett|lenovo (idea )?tab|\btab (s|a)\d|tab nexus"),
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
    ("washers", r"bosch wq|\bedh\d|\bew\d"),
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
    ("chargers", r"lader|charger|power ?bank|kabel|cable|usb-c hub|dokkingstasjon|docking|strømadapter|usb-c-adapter|usb-c adapter|reiseadapter|travel adapter|nettadapter|skjøteledning"),
    # --- sound & tv
    ("soundbars", r"lydplanke|soundbar|subwoofer|hjemmekino|sub mini|arc ultra"),
    ("tv", r"\btv\b|oled|qled|mini led tv|projektor|projector|/tv/"),
    ("earbuds", r"ørepropper|earbuds|true wireless|airpods|buds|in-ear|\btws\b"),
    ("headphones", r"hodetelefon|headphone|over-ear|on-ear|wh-1000|quietcomfort"),
    ("speakers", r"høyttaler|speaker|partybox|soundlink|sonos (era|move|roam|five|play)|jbl (flip|charge|clip|go|xtreme)|bluetooth-høyttaler|radio|platespiller|turntable"),
    ("music", r"\bdj\b|dj-|dj controller|ddj-|dj-mikser|mikserbord|lydmikser|gitar|piano|keyboard-instrument|synth"),
    # --- photo
    ("drones", r"drone|dji (mini|air|mavic|avata|neo)"),
    ("actioncams", r"actionkamera|gopro|insta360 (x|ace|go)|osmo action|360-kamera|360 kamera"),
    ("gimbals", r"gimbal|osmo mobile|dji rs"),
    ("cameras", r"kamera|camera|objektiv|eos r|alpha a?\d|lumix|fujifilm x|nikon z"),
    ("webcams", r"webkamera|webcam"),
    ("audio", r"mikrofon|microphone|podcast|rodecaster"),
    ("calibration", r"kalibrering|spyder|calibrite"),
    ("bags", r"fotoveske|kamerasekk|kamerastativ|\bstativ\b|tripod|selfie"),
    # --- appliances (hvitevarer)
    ("washers", r"vaskemaskin|tørketrommel|tørkeskap|washing machine|dryer|vask og tørk|vask-tork"),
    ("fridges", r"kjøleskap|fryser|kombiskap|vinskap|fridge|freezer"),
    ("dishwashers", r"oppvaskmaskin|dishwasher"),
    ("ovens", r"stekeovn|komfyr|platetopp|induksjon|kokeplate|ventilator|kjøkkenvifte|avtrekkshette|avtrekksvifte|mikrobølgeovn|microwave"),
    # --- home
    ("robovac", r"robotstøvsuger|robot vacuum|roborock|roomba|dreame (x|l)\d|ecovacs|deebot"),
    ("vacuums", r"støvsuger|vacuum|våt/tørr|vaskemopp|wet ?dry|dyson v\d|gulvvasker"),
    ("garden", r"robotgressklipper|gressklipper|\bhage|trimmer.*gress|løvblåser|høytrykksspyler|grill(?!pinne)|lawn|mower"),
    ("climate", r"luftrenser|avfukter|luftfukter|varmepumpe|panelovn|vifte|ovn\b|air purifier|heater|klimaanlegg|sensibo"),
    ("security", r"overvåkingskamera|ringeklokke|doorbell|alarm|sikkerhet|ring (stick|video)|\barlo\b|eufy.*cam"),
    ("smarthome", r"smarthus|smart home|smartpære|\bhue\b|google home|nest hub|echo\b|alexa|homey|smartplugg|smart lys"),
    ("lighting", r"lampe|lykt|stormlykt|lys(slynge|lenke)|led-list|belysning|lantern"),
    ("laundry", r"strykejern|steamer|dampstryker|puregliss"),
    # --- kitchen
    ("coffee", r"kaffemaskin|espressomaskin|kaffetrakter|kaffekvern|nespresso|dolce gusto|melkeskummer|coffee|espresso|moccamaster|french press|presskanne"),
    ("machines", r"kjøkkenmaskin|stavmikser|blender|foodprocessor|food processor|håndmikser|kitchenaid|cooking chef|assistent|mums\d"),
    ("smallapp", r"air ?fryer|airfrier|varmluftsfriter|vannkoker|kettle|brødrister|toaster|sandwichgrill|vaffeljern|riskoker|slowcooker|sous vide|kjøkkenvekt|krydderkvern|woodfire|ninja"),
    ("knives", r"kniv|knife"),
    ("pans", r"stekepanne|sautèpanne|sautepanne|wokpanne|\bpanne\b|frying pan"),
    ("pots", r"gryte|\bkjele|grytesett|kasserolle|\bpot\b"),
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
    ("strollers", r"barnevogn|sittevogn|sportsvogn|\btrille\b"),
    ("carseats", r"bilstol|beltestol"),
    ("baby", r"babycall|babymonitor|stellebord|tåteflaske|bæresele|babynest|\bbaby"),
    ("lego", r"\blego\b"),
    ("toys", r"leke|leketøy|dukke|bamse|brettspill|puslespill|\btoy|playmobil|barbie|hot wheels|nerf|fjernstyrt|rc-bil"),
    # --- sports & outdoor
    ("clothing", r"skirt|skjort\b|skjørt|singlet|\bshorts?\b|socks|strømpe|strompe|jersey|chinos|sweat|\btop\b|tee\b|polo\b|\bleggings|tights|hettegenser|crew\b|pants|jacket|parka|vest\b"),
    ("outdoor", r"tarp|telt|sovepose|liggeunderlag|drikkeflaske|termos|primus|stormkjøkken|oppblåsbar|oppblasbar|kajakk|padle|hodelykt|tursekk|ryggsekk|dagstursekk|klatre|innlegg|spisepinner|campfire"),
    ("winter", r"\bski\b|skisko|skistav|staver|langrenn|alpin|slalåm|snowboard|skøyter|skiskøyter|akebrett|truger|feller\b|skismøring|skibinding"),
    ("shoes", r"sko\b|løpesko|lopesko|joggesko|sneakers?|støvler?|stovler?|sandal|tursko|fotballsko|innesko|vintersko|boots"),
    ("clothing", r"jakke|bukse|genser|hoodie|t-skjorte|tskjorte|skjorte|tights|shorts|vest\b|dunjakke|parkas|regnjakke|ullundertøy|undertøy|sokker|lue\b|hansker|votter|truse|bh\b|kjole|skjørt|treningsoverdel|fleece|softshell|anorakk|dress\b"),
    ("bikes", r"sykkel|el-sparkesykkel|sparkesykkel|scooter|ninebot|segway|elsykkel|bike\b|mtb|terrengsykkel|grussykkel"),
    ("fitness", r"tredemølle|treningssykkel|romaskin|manualer|kettlebell|treningsmatte|fitness|spinning"),
    ("outdoor", r"telt|sovepose|tursekk|hodelykt|ski\b|skisko|turutstyr|friluft|jakke|kajakk|fiske"),
]
def _guard(rx):
    """Put a word boundary in front of short top-level alternatives ("lue" must not match "Blue")."""
    parts, depth, cur = [], 0, ""
    for ch in rx:
        if ch == "(" : depth += 1
        if ch == ")" : depth -= 1
        if ch == "|" and depth == 0: parts.append(cur); cur = ""; continue
        cur += ch
    parts.append(cur)
    out = []
    for a in parts:
        core = re.sub(r"\\b|\$", "", a)
        if re.fullmatch(r"[a-zæøåé]{2,5}", core) and not a.startswith("\\b"):
            a = "\\b" + a
        out.append(a)
    return "|".join(out)
RULES = [(sub, re.compile(_guard(rx), re.I)) for sub, rx in RULES]

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
    ("/kaffe", "coffee"), ("/airfryer", "smallapp"), ("/vannkoker", "smallapp"), ("/brodrister", "smallapp"), ("/smorbrodgrill", "smallapp"), ("/brodbaker", "smallapp"), ("/multikoker", "smallapp"), ("/blender", "machines"), ("/stavmikser", "machines"), ("/kjokkenmaskin", "machines"),
    ("/harfoner", "hair"), ("/rettetang", "hair"), ("/harpleie", "hair"), ("/barbering", "shaving"), ("/tannpleie", "oral"),
    ("/leker", "toys"), ("/leketoy", "toys"), ("/vinterleker", "outdoorkids"), ("/utendorsleker", "outdoorkids"), ("/utelek", "outdoorkids"), ("/radiostyrte", "rc"),
    ("/el-verktoy", "powertools"), ("/handverktoy", "handtools"), ("/trykkluft", "workshop"), ("/sveising", "workshop"), ("/bilverktoy", "workshop"), ("/verksted", "workshop"),
    ("/bil---mc/", "car"), ("/bil-og-garasje/", "car"), ("/biltilbehor", "car"), ("/bilpleie", "car"), ("/oppbevaring", "storage"), ("/maling", "build"), ("/stiger", "build"), ("/jul/", "christmas"), ("/julebelysning", "christmas"), ("/julepynt", "christmas"),
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
    sub = _classify(name, url)
    if sub == "lego" and not re.search(r"\blego\b", name or "", re.I):
        return "toys"  # only real LEGO in the LEGO category
    return sub


def _classify(name: str, url: str = "") -> str:
    path = _path(url) if url.startswith("http") else url.lower()
    text = (name or "").lower()
    # 1) product name rules (most precise)
    for sub, rx in RULES:
        if rx.search(text):
            return sub
    # 2) the shop's own category path, most specific (deepest) segment first
    segs = [x for x in path.split("/") if x]
    for seg in reversed(segs):
        for hint, sub in PATH_HINTS:
            h = hint.strip("/")
            if h and h in seg:
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


def explain(name: str, url: str = ""):
    """(sub, matched text, start, end, source) for auditing which rule fired."""
    text = (name or "").lower()
    for sub, rx in RULES:
        m = rx.search(text)
        if m:
            return sub, m.group(0), m.start(), m.end(), "name"
    path = _path(url) if url.startswith("http") else url.lower()
    for seg, sub in PATH_HINTS:
        if seg in path:
            return sub, seg, -1, -1, "path"
    for sub, rx in RULES:
        m = rx.search(path)
        if m:
            return sub, m.group(0), -1, -1, "pathrule"
    return "other", "", -1, -1, ""

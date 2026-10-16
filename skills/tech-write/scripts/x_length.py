#!/usr/bin/env python3
"""Count the weighted length of X (Twitter) posts in a draft file.

usage: python3 x_length.py <draft> [--limit N]

Counting follows twitter-text config v3: after NFC normalization, code points
in U+0000-10FF, U+2000-200D, U+2010-201F and U+2032-2037 weigh 1 and every
other code point weighs 2. A URL weighs 23 whatever its length, and an emoji
weighs 2. A thread is split into posts at runs of three or more blank lines;
each post is trimmed of leading and trailing whitespace and counted alone.

Output: one line per post with its weighted length, the limit and the
remaining or exceeded amount. Exit 0 when every post fits the limit, 1 when a
post exceeds it, 2 when the draft is empty, unreadable or the arguments are
invalid. Standard library only.

URL detection is a port of twitter-text's extractUrlsWithIndices (the same
rules X applies when it turns text into links):

- A URL may start with http:// or https:// or have no scheme. It may follow
  any character except ASCII letters and digits, @, $ and # (and their
  full-width forms), so a URL written right after Japanese text is a URL.
- The last label must be a top-level domain in the IANA root zone (the
  generic, country and internationalized lists below, or a punycode label
  such as xn--p1ai). A scheme-less domain also needs ASCII labels, and may not
  follow -, _, . or /.
- A scheme-less domain made of one label and a country-code top-level domain
  (example.jp, example.ai, readme.md, main.py) is not a URL unless a path
  follows it (example.jp/a); the only exceptions are .co and .tv
  (huggingface.co, twitch.tv). Generic top-level domains (example.com,
  deno.land) are URLs even without a path.
- The path keeps balanced parentheses and stops at characters that cannot
  end a path, so a closing bracket or a sentence-ending mark after a URL is
  counted as text. Characters outside the ASCII, Latin-accent and Cyrillic
  sets (Japanese, for example) end the path.
- A t.co URL keeps only its alphanumeric slug.

The regex is tried only where a domain can start (see url_start_reachable),
so a long draft is counted in linear time even when every sentence ends in an
ASCII period.

A byte order mark at the start of the file is ignored.
Emoji sequences joined with ZWJ, skin tone modifiers, keycaps and flags each
count as one emoji of weight 2, which approximates twitter-text's emoji table.
"""
import argparse
import re
import sys
import unicodedata

DEFAULT_LIMIT = 280
URL_WEIGHT = 23
EMOJI_WEIGHT = 2
LIGHT_RANGES = ((0x0000, 0x10FF), (0x2000, 0x200D), (0x2010, 0x201F), (0x2032, 0x2037))

POST_SEPARATOR = re.compile(r"\n(?:[ \t]*\n){3,}")

# Top-level domains from the IANA root zone (data.iana.org/TLD, version 2026101600),
# like the TLD tables of twitter-text. Internationalized TLDs are listed in
# Unicode form; their punycode form (xn--...) is accepted by the regex.
GENERIC_TLDS = frozenset("""
    aaa aarp abb abbott abbvie abc able abogado abudhabi academy accenture accountant
    accountants aco actor ads adult aeg aero aetna afl africa agakhan agency aig airbus airforce
    airtel akdn alibaba alipay allfinanz allstate ally alsace alstom amazon americanexpress
    americanfamily amex amfam amica amsterdam analytics android anquan anz aol apartments app
    apple aquarelle arab aramco archi army arpa art arte asda asia associates athleta attorney
    auction audi audible audio auspost author auto autos aws axa azure baby baidu banamex band
    bank bar barcelona barclaycard barclays barefoot bargains baseball basketball bauhaus bayern
    bbc bbt bbva bcg bcn beats beauty beer berlin best bestbuy bet bharti bible bid bike bing
    bingo bio biz black blackfriday blockbuster blog bloomberg blue bms bmw bnpparibas boats
    boehringer bofa bom bond boo book booking bosch bostik boston bot boutique box bradesco
    bridgestone broadway broker brother brussels build builders business buy buzz bzh cab cafe
    cal call calvinklein cam camera camp canon capetown capital capitalone car caravan cards
    care career careers cars casa case cash casino cat catering catholic cba cbn cbre center ceo
    cern cfa cfd chanel channel charity chase chat cheap chintai christmas chrome church
    cipriani circle cisco citadel citi citic city claims cleaning click clinic clinique clothing
    cloud club clubmed coach codes coffee college cologne com commbank community company compare
    computer comsec condos construction consulting contact contractors cooking cool coop corsica
    country coupon coupons courses cpa credit creditcard creditunion cricket crown crs cruise
    cruises cuisinella cymru cyou dad dance data date dating datsun day dclk dds deal dealer
    deals degree delivery dell deloitte delta democrat dental dentist desi design dev dhl
    diamonds diet digital direct directory discount discover dish diy dnp docs doctor dog
    domains dot download drive dtv dubai dupont durban dvag dvr earth eat eco edeka edu
    education email emerck energy engineer engineering enterprises epson equipment ericsson erni
    esq estate eurovision eus events exchange expert exposed express extraspace fage fail
    fairwinds faith family fan fans farm farmers fashion fast fedex feedback ferrari ferrero
    fidelity fido film final finance financial fire firestone firmdale fish fishing fit fitness
    flickr flights flir florist flowers fly foo food football ford forex forsale forum
    foundation fox free fresenius frl frogans frontier ftr fujitsu fun fund furniture futbol fyi
    gal gallery gallo gallup game games gap garden gay gbiz gdn gea gent genting george ggee
    gift gifts gives giving glass gle global globo gmail gmbh gmo gmx godaddy gold goldpoint
    golf goodyear goog google gop got gov grainger graphics gratis green gripe grocery group
    gucci guge guide guitars guru hair hamburg hangout haus hbo hdfc hdfcbank health healthcare
    help helsinki here hermes hiphop hisamitsu hitachi hiv hkt hockey holdings holiday homedepot
    homegoods homes homesense honda horse hospital host hosting hot hotels hotmail house how
    hsbc hughes hyatt hyundai ibm icbc ice icu ieee ifm ikano imamat imdb immo immobilien inc
    industries infiniti info ing ink institute insurance insure int international intuit
    investments ipiranga irish ismaili ist istanbul itau itv jaguar java jcb jeep jetzt jewelry
    jio jll jmp jnj jobs joburg jot joy jpmorgan jprs juegos kaufen kddi kerryhotels
    kerryproperties kfh kia kids kim kindle kitchen kiwi koeln komatsu kosher kpmg kpn krd kred
    kuokgroup kyoto lacaixa lamborghini lamer land landrover lanxess lasalle lat latino latrobe
    law lawyer lds lease leclerc lefrak legal lego lexus lgbt lidl life lifeinsurance lifestyle
    lighting like lilly limited limo lincoln link live living llc llp loan loans locker locus
    lol london lotte lotto love lpl lplfinancial ltd ltda lundbeck luxe luxury madrid maif
    maison makeup man management mango map market marketing markets marriott marshalls mattel
    mba mckinsey med media meet melbourne meme memorial men menu merck merckmsd miami microsoft
    mil mini mint mit mitsubishi mlb mls mma mobi mobile moda moe moi mom monash money monster
    mormon mortgage moscow moto motorcycles mov movie msd mtn mtr museum music nab nagoya name
    navy nba nec net netbank netflix network neustar new news next nextdirect nexus nfl ngo nhk
    nico nike nikon ninja nissan nissay nokia norton now nowruz nowtv nra nrw ntt nyc obi
    observer office okinawa olayan olayangroup ollo omega one ong onl online ooo open oracle
    orange org organic origins osaka otsuka ott ovh page panasonic paris pars partners parts
    party pay pccw pet pfizer pharmacy phd philips phone photo photography photos physio pics
    pictet pictures pid pin ping pink pioneer pizza place play playstation plumbing plus pnc
    pohl poker politie porn post praxi press prime pro prod productions prof progressive promo
    properties property protection pru prudential pub pwc qpon quebec quest racing radio read
    realestate realtor realty recipes red redumbrella rehab reise reisen reit reliance ren rent
    rentals repair report republican rest restaurant review reviews rexroth rich richardli ricoh
    ril rio rip rocks rodeo rogers room rsvp rugby ruhr run rwe ryukyu saarland safe safety
    sakura sale salon samsclub samsung sandvik sandvikcoromant sanofi sap sarl sas save saxo sbi
    sbs scb schaeffler schmidt scholarships school schule schwarz science scot search seat
    secure security seek select sener services seven sew sex sexy sfr shangrila sharp shell shia
    shiksha shoes shop shopping shouji show silk sina singles site ski skin sky skype sling
    smart smile sncf soccer social softbank software sohu solar solutions song sony soy spa
    space sport spot srl stada staples star statebank statefarm stc stcgroup stockholm storage
    store stream studio study style sucks supplies supply support surf surgery suzuki swatch
    swiss sydney systems tab taipei talk taobao target tatamotors tatar tattoo tax taxi tci tdk
    team tech technology tel temasek tennis teva thd theater theatre tiaa tickets tienda tips
    tires tirol tjmaxx tjx tkmaxx tmall today tokyo tools top toray toshiba total tours town
    toyota toys trade trading training travel travelers travelersinsurance trust trv tube tui
    tunes tushu tvs ubank ubs unicom university uno uol ups vacations vana vanguard vegas
    ventures verisign versicherung vet viajes video vig viking villas vin vip virgin visa vision
    viva vivo vlaanderen vodka volvo vote voting voto voyage wales walmart walter wang wanggou
    watch watches weather weatherchannel web webcam weber website wed wedding weibo weir whoswho
    wien wiki williamhill win windows wine winners wme woodside work works world wow wtc wtf
    xbox xerox xihuan xin xxx xyz yachts yahoo yamaxun yandex yodobashi yoga yokohama you
    youtube yun zappos zara zero zip zone zuerich
""".split())
COUNTRY_TLDS = frozenset("""
    ac ad ae af ag ai al am ao aq ar as at au aw ax az ba bb bd be bf bg bh bi bj bm bn bo br bs
    bt bv bw by bz ca cc cd cf cg ch ci ck cl cm cn co cr cu cv cw cx cy cz de dj dk dm do dz ec
    ee eg er es et eu fi fj fk fm fo fr ga gb gd ge gf gg gh gi gl gm gn gp gq gr gs gt gu gw gy
    hk hm hn hr ht hu id ie il im in io iq ir is it je jm jo jp ke kg kh ki km kn kp kr kw ky kz
    la lb lc li lk lr ls lt lu lv ly ma mc md me mg mh mk ml mm mn mo mp mq mr ms mt mu mv mw mx
    my mz na nc ne nf ng ni nl no np nr nu nz om pa pe pf pg ph pk pl pm pn pr ps pt pw py qa re
    ro rs ru rw sa sb sc sd se sg sh si sj sk sl sm sn so sr ss st su sv sx sy sz tc td tf tg th
    tj tk tl tm tn to tr tt tv tw tz ua ug uk us uy uz va vc ve vg vi vn vu wf ws ye yt za zm zw
""".split())
IDN_TLDS = frozenset("""
    vermögensberater vermögensberatung ελ ευ бг бел дети ею католик ком мкд мон москва онлайн
    орг рус рф сайт срб укр қаз հայ ישראל קום ابوظبي ارامكو الاردن البحرين الجزائر السعودية
    العليان المغرب امارات ایران بارت بازار بيتك بھارت تونس سودان سورية شبكة عراق عرب عمان فلسطين
    قطر كاثوليك كوم مصر مليسيا موريتانيا موقع همراه پاکستان ڀارت कॉम नेट भारत भारतम् भारोत संगठन
    বাংলা ভারত ভাৰত ਭਾਰਤ ભારત ଭାରତ இந்தியா இலங்கை சிங்கப்பூர் భారత్ ಭಾರತ ഭാരതം ලංකා คอม ไทย ລາວ
    გე みんな アマゾン クラウド グーグル コム ストア セール ファッション ポイント 世界 中信 中国 中國 中文网 亚马逊 企业 佛山 信息 健康 八卦 公司 公益 台湾 台灣
    商城 商店 商标 嘉里 嘉里大酒店 在线 大拿 天主教 娱乐 家電 广东 微博 慈善 我爱你 手机 招聘 政务 政府 新加坡 新闻 时尚 書籍 机构 淡马锡 游戏 澳門 点看 移动
    组织机构 网址 网店 网站 网络 联通 谷歌 购物 通販 集团 電訊盈科 飞利浦 食品 餐厅 香格里拉 香港 닷넷 닷컴 삼성 한국
""".split())

# --- URL detection: port of twitter-text's regexp/*.js and extractUrlsWithIndices ---
PUNCT = r"!'#%&'()*+,\\\-./:;<=>?@\[\]^_{|}~$"
SPACES = r"\t-\r \x85\xa0\u1680\u180e\u2000-\u200a\u2028\u2029\u202f\u205f\u3000"
INVALID_CHARS = r"\ufffe\ufeff\uffff"
DIRECTIONAL = r"\u202a-\u202e\u061c\u200e\u200f\u2066-\u2069"
LATIN_ACCENT = (r"\xc0-\xd6\xd8-\xf6\xf8-\xff\u0100-\u024f\u0253\u0254\u0256\u0257"
                r"\u0259\u025b\u0263\u0268\u026f\u0272\u0289\u028b\u02bb\u0300-\u036f\u1e00-\u1eff")
CYRILLIC = r"\u0400-\u04ff"


def _alternation(tlds):
    return "|".join(re.escape(t) for t in sorted(tlds, key=lambda t: (-len(t), t)))


TLD_END = r"(?=[^0-9a-zA-Z@+-]|$)"
GTLD = r"(?:(?:" + _alternation(GENERIC_TLDS | IDN_TLDS) + r")" + TLD_END + r")"
CCTLD = r"(?:(?:" + _alternation(COUNTRY_TLDS) + r")" + TLD_END + r")"
SPECIAL_CCTLD = r"(?:(?:co|tv)" + TLD_END + r")"
PUNYCODE = r"(?:xn--[-0-9a-z]+)"
DOMAIN_CHAR = r"[^" + PUNCT + SPACES + INVALID_CHARS + DIRECTIONAL + r"]"
SUBDOMAIN = r"(?:(?:" + DOMAIN_CHAR + r"(?:[_-]|" + DOMAIN_CHAR + r")*)?" + DOMAIN_CHAR + r"\.)"
DOMAIN_NAME = r"(?:(?:" + DOMAIN_CHAR + r"(?:-|" + DOMAIN_CHAR + r")*)?" + DOMAIN_CHAR + r"\.)"
DOMAIN = r"(?:" + SUBDOMAIN + r"*" + DOMAIN_NAME + r"(?:" + GTLD + r"|" + CCTLD + r"|" + PUNYCODE + r"))"
ASCII_DOMAIN = (r"(?:(?:[-a-z0-9" + LATIN_ACCENT + r"]+)\.)+(?:" + GTLD + r"|" + CCTLD + r"|"
                + PUNYCODE + r")")
PATH_CHAR = r"[a-z" + CYRILLIC + r"0-9!*';:=+,.$/%#\[\]\-\u2013_~@|&" + LATIN_ACCENT + r"]"
BALANCED_PARENS = (r"\((?:" + PATH_CHAR + r"+|(?:" + PATH_CHAR + r"*\(" + PATH_CHAR + r"+\)"
                   + PATH_CHAR + r"*))\)")
PATH_END = r"(?:[+\-a-z" + CYRILLIC + r"0-9=_#/" + LATIN_ACCENT + r"]|" + BALANCED_PARENS + r")"
URL_PATH = (r"(?:(?:" + PATH_CHAR + r"*(?:" + BALANCED_PARENS + PATH_CHAR + r"*)*" + PATH_END
            + r")|(?:@" + PATH_CHAR + r"+/))")
QUERY_CHAR = r"[a-z0-9!?*'@();:&=+$/%#\[\]\-_.,~|]"
QUERY_END = r"[a-z0-9\-_&=#/]"
PRECEDING = r"(?:[^A-Za-z0-9@\uff20$#\uff03" + INVALID_CHARS + r"]|[" + DIRECTIONAL + r"]|^)"
EXTRACT_URL = re.compile(
    r"(" + PRECEDING + r")"                        # 1 preceding character
    r"((https?://)?"                               # 2 URL, 3 scheme
    r"(" + DOMAIN + r")"                           # 4 domain
    r"(?::([0-9]+))?"                              # 5 port
    r"(/" + URL_PATH + r"*)?"                      # 6 path
    r"(\?" + QUERY_CHAR + r"*" + QUERY_END + r")?)",  # 7 query
    re.IGNORECASE)
ASCII_DOMAIN_RE = re.compile(ASCII_DOMAIN, re.IGNORECASE)
INVALID_SHORT_DOMAIN = re.compile(r"^" + DOMAIN_NAME + CCTLD + r"$", re.IGNORECASE)
SPECIAL_SHORT_DOMAIN = re.compile(r"^" + DOMAIN_NAME + SPECIAL_CCTLD + r"$", re.IGNORECASE)
INVALID_SCHEMELESS_PRECEDING = re.compile(r"[-_./]$")
TCO_URL = re.compile(r"^https?://t\.co/([a-z0-9]+)(?:\?" + QUERY_CHAR + r"*" + QUERY_END + r")?",
                     re.IGNORECASE)
MAX_TCO_SLUG_LENGTH = 40
DOMAIN_CHAR_RE = re.compile(DOMAIN_CHAR, re.IGNORECASE)
SCHEME = re.compile(r"https?://", re.IGNORECASE)
ASCII_TLDS = GENERIC_TLDS | COUNTRY_TLDS
ASCII_TLD_RUN = re.compile(r"[0-9A-Za-z@+-]*")
IDN_TLD_RE = re.compile(r"(?:" + _alternation(IDN_TLDS) + r")" + TLD_END, re.IGNORECASE)
PUNYCODE_RE = re.compile(PUNYCODE, re.IGNORECASE)


def tld_follows(text, dot):
    """Whether a top-level domain, as the URL regex accepts it, starts right after text[dot]."""
    q = dot + 1
    if q >= len(text):
        return False
    if text[q].isascii():
        # An ASCII top-level domain must be followed by a character outside [0-9a-zA-Z@+-],
        # so the whole run of those characters has to be a known top-level domain.
        run = ASCII_TLD_RUN.match(text, q).group(0)
        return run.lower() in ASCII_TLDS or PUNYCODE_RE.match(text, q) is not None
    return IDN_TLD_RE.match(text, q) is not None


def url_start_reachable(text):
    """For each index, whether a domain as the URL regex accepts it can start there.

    A domain is a chain of labels separated by '.' whose last label is a top-level
    domain: every label before the last one starts and ends with a domain character,
    and the one right before the top-level domain contains no '_'. The chain is
    found label by label from the right, so the scan is linear. The URL regex is
    then tried only where a domain is known to exist, which keeps long drafts with
    many '.' (sentences ending in an ASCII period, for example) from making the
    regex backtrack at every position.
    """
    n = len(text)
    reach = [False] * (n + 1)
    dc = [DOMAIN_CHAR_RE.match(ch) is not None for ch in text]
    i = n - 1
    while i >= 0:
        if not (dc[i] or text[i] in "-_"):
            i -= 1
            continue
        end = i + 1
        start = i
        while start > 0 and (dc[start - 1] or text[start - 1] in "-_"):
            start -= 1
        has_dot = end < n and text[end] == "."
        label_ok = has_dot and dc[end - 1]
        next_reach = label_ok and reach[end + 1]
        tld_here = label_ok and tld_follows(text, end)
        underscore_after = False
        for j in range(end - 1, start - 1, -1):
            reach[j] = dc[j] and (next_reach or (tld_here and not underscore_after))
            underscore_after = underscore_after or text[j] == "_"
        i = start - 1
    return reach


def extract_urls(text, prefilter=True):
    """Return [start, end) spans of the URLs in text, as twitter-text extracts them.

    With prefilter the regex is tried only where url_start_reachable says a
    domain exists; without it the regex is tried at every position, which gives
    the same spans but can take quadratic time. The tests compare the two.
    """
    spans = []
    reach = url_start_reachable(text) if prefilter else None
    n = len(text)

    def may_start(q):
        if reach is None:
            return True
        if q >= n:
            return False
        if reach[q]:
            return True
        m = SCHEME.match(text, q)
        return m is not None and reach[m.end()]

    pos = 0
    while pos < n:
        # The match consumes the preceding character at pos (or nothing at 0),
        # so the URL itself would start at pos + 1 (or at 0).
        if not (may_start(pos + 1) or (pos == 0 and may_start(0))):
            pos += 1
            continue
        m = EXTRACT_URL.match(text, pos)
        if not m:
            pos += 1
            continue
        before, url, scheme, domain, path = m.group(1), m.group(2), m.group(3), m.group(4), m.group(6)
        end = m.end()
        start = end - len(url)
        pos = end
        if scheme:
            t = TCO_URL.match(url)
            if t:
                if len(t.group(1)) > MAX_TCO_SLUG_LENGTH:
                    continue
                end = start + len(t.group(0))
            spans.append([start, end])
            continue
        if INVALID_SCHEMELESS_PRECEDING.search(before):
            continue
        # Without a scheme only the ASCII part of the domain is a URL.
        last = None
        ascii_end = 0
        for a in ASCII_DOMAIN_RE.finditer(domain):
            ascii_domain = a.group(0)
            ascii_start = domain.find(ascii_domain, ascii_end)
            ascii_end = ascii_start + len(ascii_domain)
            last = [start + ascii_start, start + ascii_end]
            if (path or SPECIAL_SHORT_DOMAIN.match(ascii_domain)
                    or not INVALID_SHORT_DOMAIN.match(ascii_domain)):
                spans.append(last)
        if last is not None and path:
            last[1] = end
    return spans


# --- emoji ---
ZWJ = "\u200d"
VS16 = "\ufe0f"
KEYCAP = "\u20e3"


def is_emoji_base(cp):
    return (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF
            or 0x2B00 <= cp <= 0x2BFF or cp in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139,
                                                0x231A, 0x231B, 0x2328, 0x23CF, 0x24C2, 0x3030, 0x303D,
                                                0x3297, 0x3299)
            or 0x2190 <= cp <= 0x21FF or 0x23E9 <= cp <= 0x23FA or 0x25AA <= cp <= 0x25FE)


def is_modifier(cp):
    return cp == 0xFE0F or 0x1F3FB <= cp <= 0x1F3FF or 0xE0020 <= cp <= 0xE007F


def is_regional(cp):
    return 0x1F1E6 <= cp <= 0x1F1FF


def char_weight(cp):
    return 1 if any(lo <= cp <= hi for lo, hi in LIGHT_RANGES) else 2


def emoji_length(text, i):
    """Return the length of the emoji sequence starting at text[i], or 0 if none."""
    n = len(text)
    cp = ord(text[i])
    if text[i] in "0123456789#*":
        j = i + 1
        if j < n and text[j] == VS16:
            j += 1
        return j + 1 - i if j < n and text[j] == KEYCAP else 0
    if is_regional(cp):
        return 2 if i + 1 < n and is_regional(ord(text[i + 1])) else 1
    if not is_emoji_base(cp):
        return 0
    # Characters below U+2190 (©, ®, ‼ and so on) are emoji only with VS16.
    if cp < 0x2190 and not (i + 1 < n and text[i + 1] == VS16):
        return 0
    j = i + 1
    while True:
        while j < n and is_modifier(ord(text[j])):
            j += 1
        if j + 1 < n and text[j] == ZWJ and is_emoji_base(ord(text[j + 1])):
            j += 2
            continue
        return j - i


def weighted_length(post):
    """Return (weight, used_zwj) for one post."""
    text = unicodedata.normalize("NFC", post)
    url_end_at = {start: end for start, end in extract_urls(text)}
    total = 0
    used_zwj = False
    i = 0
    n = len(text)
    while i < n:
        if i in url_end_at:
            total += URL_WEIGHT
            i = url_end_at[i]
            continue
        k = emoji_length(text, i)
        if k:
            used_zwj = used_zwj or ZWJ in text[i:i + k]
            total += EMOJI_WEIGHT
            i += k
            continue
        total += char_weight(ord(text[i]))
        i += 1
    return total, used_zwj


def split_posts(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return [p.strip() for p in POST_SEPARATOR.split(text) if p.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(description="X の投稿の重み付き文字数を数える")
    parser.add_argument("draft", help="稿のファイル（UTF-8）。空行 3 つ以上でスレッドの投稿を区切る")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"1 投稿の上限（既定 {DEFAULT_LIMIT}）")
    args = parser.parse_args(argv)
    if args.limit <= 0:
        print("エラー: --limit は 1 以上を指定してください", file=sys.stderr)
        return 2
    try:
        with open(args.draft, encoding="utf-8-sig") as f:
            text = f.read()
    except (OSError, UnicodeError) as e:
        print(f"エラー: 稿のファイルを読めません: {args.draft} ({e.__class__.__name__})", file=sys.stderr)
        return 2
    posts = split_posts(text)
    if not posts:
        print(f"エラー: 稿が空です: {args.draft}", file=sys.stderr)
        return 2

    over = 0
    used_zwj = False
    for number, post in enumerate(posts, 1):
        weight, zwj = weighted_length(post)
        used_zwj = used_zwj or zwj
        if weight > args.limit:
            over += 1
            status = f"{weight - args.limit} 超過"
        else:
            status = f"残り {args.limit - weight}"
        print(f"投稿 {number}/{len(posts)}: {weight} / {args.limit}（{status}）")
    print(f"上限を超えた投稿: {over} 件")
    if used_zwj:
        print("注: ZWJ で連結した絵文字は 1 つの絵文字（2）として数えた近似です")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())

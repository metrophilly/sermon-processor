import html
import os
import json
import re
import httpx  # type: ignore
from dotenv import load_dotenv  # type: ignore


def format_passage_ref_for_studylight(passage_ref):
    """
    StudyLight API Instructions - as of April 30, 2024

    Requesting Bible passage from the StudyLight.org server is a simple process using these instructions

    Input: passage=Joh 3:12-18 - This is an example of how to call the reference

    Book:                      - You are required to use the following 3-letter abbreviation for the
                                  book reference:

                                  Gen = Genesis           Exo = Exodus            Lev = Leviticus         Num = Numbers           Deu = Deuteronomy
                                  Jos = Joshua            Jdg = Judges            Rut = Ruth              1Sa = 1 Samuel          2Sa = 2 Samuel
                                  1Ki = 1 Kings           2Ki = 2 Kings           1Ch = 1 Chronicles      2Ch = 2 Chronicles      Ezr = Ezra
                                  Neh = Nehemiah          Est = Esther            Job = Job               Psa = Psalms            Pro = Proverbs
                                  Ecc = Ecclesiastes      Sng = Song of Solomon   Isa = Isaiah            Jer = Jeremiah          Lam = Lamentations
                                  Eze = Ezekiel           Dan = Daniel            Hos = Hosea             Joe = Joel              Oba = Obadiah
                                  Jon = Jonah             Mic = Micah             Nah = Nahum             Hab = Habakkuk          Zep = Zepheniah
                                  Hag = Haggai            Zec = Zechariah         Mal = Malachi

                                  Mat = Matthew           Mar = Mark              Luk = Luke              Joh = John              Act = Acts
                                  Rom = Romans            1Co = 1 Corinthians     2Co = 2 Corinthians     Gal = Galatians         Eph = Ephesians
                                  Php = Philippians       Col = Colossians        1Th = 1 Thessalonians   2Th = 2 Thessalonians   1Ti = 1 Timothy
                                  2Ti = 2 Timothy         Tit = Titus             Phm = Philemon          Heb = Hebrews           Jas = James
                                  1Pe = 1 Peter           2Pe = 2 Peter           1Jo = 1 John            2Jo = 2 John            3Jo = 3 John
                                  Jud = Jude              Rev = Revelation

    Chapter and verse(s):      - Must be separated by a colon (:) with verses separated
                                  either by a hyphen or comma depending on the range
                                  (examples: 3:1-14 or 12:3,4). References spanning
                                  chapter boundries will be ignored.

    Additional info:

    lang=                      - Languages are called by their three-letter abbreviations. The default
                                  is English but you can choose any of the languages listed below.

                                  ind = Bahasa Indonesia   ind = Bahasa Indonesia   ind = Bahasa Indonesia   ind = Bahasa Indonesia
                                  afr = Afrikaans          alb = Shqip              ara = Arabic             bul = български
                                  bur = မြန်မာယူနီကုတ်        chi = 简体中文           cze = Čeština            dan = Dansk
                                  dut = Nederlands         eng = English            fin = Suomi              fre = Français
                                  ger = Deutch             gre = Greek              heb = Hebrew             hin = हिंदी
                                  hrv = Hrvatski           hun = Magyar             ice = Íslensku           ind = Bahasa Indonesia
                                  ita = Italiano           jpn = Japanese           kor = 한국어              mao = Maori
                                  nep = Nepali             nor = Norsk              per = Farsi              pol = Polska
                                  por = Português          pun = ਪੰਜਾਬੀ              rum = Romanian           rus = Русский
                                  som = Somali             spa = Español            swe = Svenska            tgl = Filipino
                                  tha = ภาษาไทย           tur = Türkçe             ukr = український        urd = اردو
                                  vie = tiếng Việt         xho = isiXhosa


    trans=                     - Translation are called by their three-letter abbreviations.  If a language is
                                  request the Bibles available will be listed below otherwise the English Bibles
                                  that are available will be listed.

                                  amp = Amplified Bible                       asl = American Sign Language Version        asv = American Standard Version
                                  bbe = Bible in Basic English                bis = Bishop's Bible                        brl = Brenton's Septuagint
                                  brv = English Revised Version               bsb = The Holy Bible, Berean Study Bible    cev = Contemporary English Version
                                  cjb = Complete Jewish Bible                 dby = The Darby Translation                 erv = Easy-to-Read Version
                                  esv = English Standard Version              gen = Geneva Bible                          glt = George Lamsa Translation
                                  gnt = Good News Translation                 hcs = Christian Standard Bible &reg;        hnv = Hebrew Names Version
                                  isv = International Standard Version        jet = Etheridge Translation                 jmt = Murdock Translation
                                  jps = JPS Old Testament                     kja = King James Version (1611)             kjv = King James Version
                                  leb = Lexham English Bible                  lit = Green's Literal Translation           lsb = Legacy Standard Bible
                                  lsv = Literal Standard Version              mcb = Myles Coverdale Bible                 mnt = Mace New Testament
                                  msg = THE MESSAGE                           n84 = New International Version (1984)      n95 = New American Standard Bible (1995)
                                  nas = New American Standard Bible           ncv = New Century Version                   net = The NET Bible&reg;
                                  niv = New International Version             nkj = New King James Version                nlt = New Living Translation
                                  nlv = New Life Version                      nrs = New Revised Standard                  reb = J.B. Rotherham Emphasized Bible
                                  rhe = Douay-Rheims Bible                    rsv = Revised Standard Version              scv = Simplified Cowboy Version
                                  tyn = Tyndale New Testament                 ubv = Updated Bible Version                 wbt = Webster's Bible Translation
                                  web = World English Bible                   wes = Wesley's New Testament                wnt = Weymouth New Testament
                                  wyc = Wycliffe Bible                        ylt = Young's Literal Translation


    vsrefs=                    - If you wish to remove the verse number, add "no" (vsrefs=no) otherwise
                                  don't call it


    instructions=              - If you wish to remove these instructions, add "no" (instructions=no)
                                  otherwise they will be displayed
    """

    # Mapping from full book names to their abbreviations
    book_abbreviations = {
        "Genesis": "Gen",
        "Exodus": "Exo",
        "Leviticus": "Lev",
        "Numbers": "Num",
        "Deuteronomy": "Deu",
        "Joshua": "Jos",
        "Judges": "Jdg",
        "Ruth": "Rut",
        "1 Samuel": "1Sa",
        "2 Samuel": "2Sa",
        "1 Kings": "1Ki",
        "2 Kings": "2Ki",
        "1 Chronicles": "1Ch",
        "2 Chronicles": "2Ch",
        "Ezra": "Ezr",
        "Nehemiah": "Neh",
        "Esther": "Est",
        "Job": "Job",
        "Psalms": "Psa",
        "Proverbs": "Pro",
        "Ecclesiastes": "Ecc",
        "Song of Solomon": "Sng",
        "Isaiah": "Isa",
        "Jeremiah": "Jer",
        "Lamentations": "Lam",
        "Ezekiel": "Eze",
        "Daniel": "Dan",
        "Hosea": "Hos",
        "Joel": "Joe",
        "Obadiah": "Oba",
        "Jonah": "Jon",
        "Micah": "Mic",
        "Nahum": "Nah",
        "Habakkuk": "Hab",
        "Zephaniah": "Zep",
        "Haggai": "Hag",
        "Zechariah": "Zec",
        "Malachi": "Mal",
        "Matthew": "Mat",
        "Mark": "Mar",
        "Luke": "Luk",
        "John": "Joh",
        "Acts": "Act",
        "Romans": "Rom",
        "1 Corinthians": "1Co",
        "2 Corinthians": "2Co",
        "Galatians": "Gal",
        "Ephesians": "Eph",
        "Philippians": "Php",
        "Colossians": "Col",
        "1 Thessalonians": "1Th",
        "2 Thessalonians": "2Th",
        "1 Timothy": "1Ti",
        "2 Timothy": "2Ti",
        "Titus": "Tit",
        "Philemon": "Phm",
        "Hebrews": "Heb",
        "James": "Jas",
        "1 Peter": "1Pe",
        "2 Peter": "2Pe",
        "1 John": "1Jo",
        "2 John": "2Jo",
        "3 John": "3Jo",
        "Jude": "Jud",
        "Revelation": "Rev",
    }

    parts = passage_ref.split()
    book_name = " ".join(parts[:-1])
    chapter_verse = parts[-1]

    abbreviation = book_abbreviations.get(book_name)

    if abbreviation:
        formatted_reference = f"{abbreviation}+{chapter_verse}"
        return formatted_reference.lower()
    else:
        raise ValueError("Book name not found in the list of abbreviations")


def extract_and_format_text_from_studylight_html(json_data) -> str:
    """
    Extracts and formats text from HTML content embedded within JSON or dict data,
    ensuring that all text is processed by removing undesired HTML tags like <p>, <br>,
    and heading tags (<h1>, <h2>, <h3>, etc.). Processes the text line by line to maintain
    narrative flow as per each original line in the HTML, and prepends each line with
    5 white spaces.

    Args:
        json_data (str or dict): JSON string or dict containing the HTML content.

    Returns:
        str: The cleaned, extracted text content, formatted to maintain narrative flow
        with each line beginning with 5 white spaces.
    """
    if isinstance(json_data, dict):
        data = json_data
    else:
        data = json.loads(json_data)

    html_content = data["text"]
    html_content = re.sub(r"<h[1-6].*?>.*?</h[1-6]>", "", html_content, flags=re.DOTALL)
    html_content = re.sub(
        r"<p[^>]*>|<br\s*/?>", "\n", html_content, flags=re.IGNORECASE
    )
    html_content = re.sub(r"</p>|<span[^>]*>|</span>", "", html_content)

    lines = html_content.split("\n")
    formatted_text = []

    for line in lines:
        line = html.unescape(line).strip()
        if line:  # Ensure the line is not just whitespace
            formatted_text.append("     " + line)

    full_text = "\n".join(formatted_text)
    return full_text


def fetch_passage_via_studylight(formatted_passage: str) -> object:
    """
    Fetches Bible passage data from StudyLight API.

    Args:
      formatted_passage (str): The formatted passage to fetch.

    Returns:
      object: The fetched data.

    Raises:
      ValueError: If AUTH_ID or AUTH_CODE environment variables are not set.
    """
    load_dotenv()

    auth_id = os.getenv("STUDYLIGHT_AUTH_ID")
    auth_code = os.getenv("STUDYLIGHT_AUTH_CODE")

    if not auth_id or not auth_code:
        raise ValueError("AUTH_ID and AUTH_CODE environment variables must be set.")

    url = f"https://beta.studylight.org/sandbox/bible_verse.cgi?auth-id={auth_id}&auth-code={auth_code}&lang=eng&instructions=no&vsrefs=no&trans=n84&passage={formatted_passage}"

    response = httpx.get(url)
    if response.status_code == 200:
        data = response.json()
    else:
        print("Failed to fetch data")

    return data

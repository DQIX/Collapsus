import json
import re
from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Recipe:
    """Class for a recipe."""
    type: str = ""
    result: str = ""
    qty1: int = 0
    item1: str = ""
    qty2: int = 0
    item2: str = ""
    qty3: int = 0
    item3: str = ""
    alchemiracle: bool = False
    notes: str = ""
    image: str = ""


@dataclass_json
@dataclass
class Quest:
    """Class for a quest."""
    number: int = 0
    name: str = ""
    story: bool = False
    location: str = ""
    request: str = ""
    solution: str = ""
    reward: str = ""
    prerequisite: str = "None"
    repeat: bool = False


@dataclass_json
@dataclass
class Monster:
    """Class for a monster."""
    number: str = ""
    level: str = ""
    name: str = ""
    exp: int = 0
    gold: int = 0
    family: str = ""
    hp: int = 0
    mp: int = 0
    atk: int = 0
    defn: int = 0
    agi: int = 0
    fire: int = 0
    ice: int = 0
    wind: int = 0
    blast: int = 0
    earth: int = 0
    dark: int = 0
    light: int = 0
    dazzle: int = 0
    sleep: int = 0
    death: int = 0
    haunts: str = ""
    drop1: str = ""
    drop2: str = ""
    drop3: str = ""
    image: str = ""


@dataclass_json
@dataclass
class Translation:
    """Class for a translation."""
    english: str = ""
    japanese: str = ""
    spanish: str = ""
    french: str = ""
    german: str = ""
    italian: str = ""


@dataclass_json
@dataclass
class Song:
    """Class for a song."""
    title: str = ""
    url: str = ""


@dataclass
class Grotto:
    """Class for a grotto."""
    name: str
    url: str
    special: int
    seed: str
    rank: str
    type: str
    floors: str
    boss: str
    monster_rank: str
    chests: str
    locations: str
    notes: str = ""
    owner: str = ""


@dataclass_json
@dataclass
class Quote:
    """Class for a quote."""
    name: str
    author: int
    content: str
    image: str = None
    aliases: list[str] = None


translation_languages = ["English", "Japanese (日本語)", "Spanish (Español)", "French (Français)", "German (Deutsch)",
                         "Italian (Italiano)"]

translation_languages_simple = ["english", "japanese", "spanish", "french", "german", "italian"]

with open('data/translations/grottos.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

grotto_prefixes = {lang: [] for lang in translation_languages_simple}
grotto_environments = {lang: [] for lang in translation_languages_simple}
grotto_suffixes = {lang: [] for lang in translation_languages_simple}

for index, translation in enumerate(data['translations']):
    if index < 16:
        for lang in translation_languages_simple:
            grotto_prefixes[lang].append(translation[lang])
    elif index < 16 + 24:
        for lang in translation_languages_simple:
            grotto_environments[lang].append(translation[lang])
    elif index < 16 + 24 + 16:
        for lang in translation_languages_simple:
            grotto_suffixes[lang].append(translation[lang])

grotto_special = "Has a special floor"
grotto_keys = ("Seed", "Rank", "Name", "Boss", "Type", "Floors", "Monster Rank", "Chests", "Locations")

grotto_chest_ranks = ["**S**", "**A**", "**B**", "**C**", "**D**", "**E**", "**F**", "**G**", "**H**", "**I**"]
grotto_ranks = {1: "02", 2: "38", 3: "3D", 4: "4C", 5: "51", 6: "65", 7: "79", 8: "8D", 9: "A1", 10: "B5", 11: "C9",
                12: "DD"}

quests_regex = r'^(?:(?:(⭐) )?\*\*Quest #(\d+) - (.+)\*\*(?: \1)?(?:```yml)?|(\w+): (.+?)(?:```)?)$'
cleanup_regex = r'([\w\d\.\-:/() ]+)'

item_types = ["items"]
weapon_types = ["claws", "axes", "fans", "bows", "wands", "knives", "boomerangs", "staves", "whips", "spears", "swords",
                "hammers"]
armor_types = ["torso", "legs", "feet", "head", "arms"]
accessory_types = ["accessories"]

tourney_data_types = ["Monsters"]

songs = ["00 - Overture IX", "01 - Intermezzo", "02 - Come to Our Town", "03 - Our Dreaming Town",
         "04 - The Sun Gathering Village", "05 - Evening in the Village", "06 - Pub Polka", "07 - Alchemy Pot",
         "08 - Healed by a Hymn", "09 - The Palace Oboe", "10 - Heaven's Prayer", "11 - Assemble, People",
         "12 - Cross the Fields, Cross the Mountains", "13 - Guide Them to Their Fate", "14 - With My Companions",
         "15 - Sea Breeze", "16 - Riding in the Ark", "17 - Dark Den of Thieves", "18 - Omen of Towering Death",
         "19 - A Temple With No Master", "20 - Dungeon", "21 - Are You a Loser", "22 - Swirling Desire",
         "23 - The Time of the Decisive Battle", "24 - The Dragonlord", "25 - Malroth ~ The True Evil",
         "26 - Gruelling Fight", "27 - Hero's Challenge", "28 - Incarnation of Evil", "29 - Evil One",
         "30 - Lord Mildrath", "31 - Monsters", "32 - Demon Combat", "33 - Orgo Demila", "34 - Dhoulmagus",
         "35 - Battle in the Heavens", "36 - Verse of Prayer", "37 - Sandy's Theme",
         "38 - Protectors of the Starry Sky", "39 - Painful Feelings", "40 - Toward the Starry Sky",
         "41 - Sandy's Tears", "42 - Cave Waltz", "43 - Accepting a Quest", "44 - Quest Clear", "45 - Job Change",
         "46 - Level Up", "47 - Victory", "48 - Stay at the Inn", "49 - Gained an Ally", "50 - Found Mini Medal",
         "51 - Defeated", "52 - Church Treatment", "53 - Pray at the Church", "54 - Cursed", "55 - Fanfare1",
         "56 - Fanfare2", "57 - Found Precious Item", "58 - Harp Melody", "59 - Superstar", "60 - Surprise",
         "61 - You Lose", "62 - Tragic Prologue (with Effects)", "63 - Swirling Desire ~ Destiny (with Effects)"]


def remove_extra_whitespace(string):
    return re.sub(' +', ' ', string).strip()


def _hex(value):
    n = int(value)
    if n <= 16:
        return n
    n = int(value, base=16)

    hex_str = str.upper(hex(n)[2:])
    return hex_str.zfill(2)


def is_special(data):
    try:
        return data[0] == grotto_special
    except ValueError:
        return False


def create_grotto(datas):
    converters = (_hex, int, str)

    res = []

    seed_found = False
    next_grotto = False

    for data in datas:
        match_found = re.compile(cleanup_regex).match(data)

        if match_found:
            stripped = str.strip(match_found.group(), "' ")

            if stripped != "":
                for i, converter in enumerate(converters):
                    try:
                        converted = converter(stripped)
                    except:
                        continue
                    else:
                        if isinstance(converted, str):
                            if converted.find(":") > -1:
                                if converted == "Seed:":
                                    if not seed_found:
                                        seed_found = True
                                    else:
                                        next_grotto = True
                                continue
                            elif converted == grotto_special:
                                res.insert(0, converted)
                            else:
                                res.append(converted)
                        else:
                            res.append(converted)
                        break
                    finally:
                        if next_grotto:
                            yield tuple(res)
                            res = []
                            next_grotto = False

    if len(res) > 0:
        yield tuple(res)


def parse_regex(type, string):
    regex = ""
    if type == Quest:
        regex = quests_regex

    matches = re.findall(regex, string, flags=re.MULTILINE)

    if type == Quest:
        number = int(matches[0][1])
        name = matches[0][2]
        story = matches[0][0] == "⭐"

        location = ""
        request = ""
        solution = ""
        reward = ""
        prerequisite = "None"
        repeat = False

        for info in matches[1:]:
            title = info[3].lower()
            data = remove_extra_whitespace(info[4].strip())

            if title == "location":
                location = data
            if title == "request":
                request = data
            if title == "solution":
                solution = data
            if title == "reward":
                reward = data
            if title == "prerequisite":
                prerequisite = data
            if title == "repeat":
                repeat = data.lower() == "yes"

        quest = Quest(number, name, story, location, request, solution, reward, prerequisite, repeat)
        return quest.to_dict()

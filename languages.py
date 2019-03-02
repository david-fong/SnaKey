"""
Please only use as follows:
from LANGUAGES import LANGUAGES

Rules for defining languages:
-- must map from display key (what the player sees)
   to typing key (what the player types to move around).
-- no typing keys should start with another typing key as a substring.
"""

lowercase = 'abcdefghijklmnopqrstuvwxyz'

jpn_temp = [[consonant + vowel for vowel in 'aiueo']
            for consonant in ['', ] + list('kstnhmr')]
jpn_temp[2][1] = 'shi'
jpn_temp[3][1] = 'chi'
jpn_temp[3][2] = 'tsu'
jpn_temp[5][2] = 'fu'
jpn_romanization = []
for row in jpn_temp:
    jpn_romanization.extend(row)
jpn_romanization.extend(['ya', 'yu', 'yo', 'wa', 'wo', 'nn'])
jpn_romanization = tuple(jpn_romanization)
hiragana = 'あいうえおかきくけこさしすせそ' \
             'たちつてとなにぬねのはひふへほ' \
             'まみむめもらりるれろやゆよわをん'
katakana = 'アイウエオカキクケコサシスセソ' \
             'タチツテトナニヌネノハヒフヘホ' \
             'マミムメモラリルレロヤユヨワヲン'

LANGUAGES = {
    'english lower': {l: l for l in lowercase},
    'japanese hiragana': {k: v for k, v in zip(hiragana, jpn_romanization)},
    'japanese katakana': {k: v for k, v in zip(katakana, jpn_romanization)},
}

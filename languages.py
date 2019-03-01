"""
Please only use as follows:
from LANGUAGES import LANGUAGES
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
jpn_romanization.extend(['ya', 'yu', 'yo', 'wa', 'wo', 'n'])
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


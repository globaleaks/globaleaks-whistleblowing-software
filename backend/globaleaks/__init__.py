# -*- coding: utf-8 -*-
"""
GlobaLeaks - Free and Open-Source Whistleblowing Software
"""
import operator

__author__ = 'GlobaLeaks'
__email__ = 'info@globaleaks.org'
__copyright__ = '2011-2024 - GlobaLeaks'
__version__ = '5.0.10'
__license__ = 'AGPL-3.0'

DATABASE_VERSION = 69
FIRST_DATABASE_VERSION_SUPPORTED = 52

# Add new languages as they are supported here! To do this retrieve the name of
# the language and its code from transifex. Then use the following command to
# generate the 'native' unicode string:
#
# python -c "code='ar'; import babel; print('native: %s' % repr(babel.Locale.parse(code).get_display_name(code)));"
#
# NOTE that the cmd requires Babel is installed via pip and `code` is defined.
LANGUAGES_SUPPORTED = [
    {'code': 'am', 'name': 'Amharic', 'native': '\u12a0\u121b\u122d\u129b'},
    {'code': 'ar', 'name': 'Arabic', 'native': '\u0627\u0644\u0639\u0631\u0628\u064a\u0629'},
    {'code': 'az', 'name': 'Azerbaijani', 'native': 'Az\u0259rbaycanca'},
    {'code': 'ba', 'name': 'Bashkir', 'native': '\u0411\u0430\u0448\u04a1\u043e\u0440\u0442\u0441\u0430\u002c\u0020\u0411\u0430\u0448\u04a1\u043e\u0440\u0442\u0020\u0442\u0435\u043b\u0435'},
    {'code': 'be', 'name': 'Belarusian', 'native': '\u0431\u0435\u043b\u0430\u0440\u0443\u0441\u043a\u0430\u044f'},
    {'code': 'bg', 'name': 'Bulgarian', 'native': '\u0431\u044a\u043b\u0433\u0430\u0440\u0441\u043a\u0438'},
    {'code': 'bn', 'name': 'Bengali', 'native': '\u09ac\u09be\u0982\u09b2\u09be'},
    {'code': 'bo', 'name': 'Tibetan', 'native': '\u0f56\u0f7c\u0f51\u0f0b\u0f66\u0f90\u0f51\u0f0b'},
    {'code': 'bs', 'name': 'Bosnian', 'native': 'Bosanski'},
    {'code': 'ca', 'name': 'Catalan', 'native': 'Catal\u00e0'},
    {'code': 'ca@valencia', 'name': 'Valencian', 'native': 'Valenci\u00e0'},
    {'code': 'ce', 'name': 'Chechen', 'native': '\u043d\u043e\u0445\u0447\u0438\u0439\u043d'},
    {'code': 'crh', 'name': 'Crimean Turkish', 'native': '\u13e3\u13b3\u13a9'},
    {'code': 'cs', 'name': 'Czech', 'native': '\u010ce\u0161tina'},
    {'code': 'da', 'name': 'Danish', 'native': 'Dansk'},
    {'code': 'de', 'name': 'German', 'native': 'Deutsch'},
    {'code': 'dv', 'name': 'Divehi', 'native': '\u078b\u07a8\u0788\u07ac\u0780\u07a8'},
    {'code': 'el', 'name': 'Greek', 'native': '\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac'},
    {'code': 'en', 'name': 'English', 'native': 'English'},
    {'code': 'es', 'name': 'Spanish', 'native': 'Espa\u00f1ol'},
    {'code': 'et', 'name': 'Estonian', 'native': 'Eesti'},
    {'code': 'eu', 'name': 'Basque', 'native': 'Euskara'},
    {'code': 'fa', 'name': 'Persian', 'native': '\u0641\u0627\u0631\u0633\u06cc'},
    {'code': 'fa_AF', 'name': 'Persian (Afghanistan) ', 'native': '\u0641\u0627\u0631\u0633\u06cc\u0020\u0028\u0627\u0641\u063a\u0627\u0646\u0633\u062a\u0627\u0646\u0029'},
    {'code': 'fi', 'name': 'Finnish', 'native': 'Suomi'},
    {'code': 'fr', 'name': 'French', 'native': 'Fran\u00e7ais'},
    {'code': 'gl', 'name': 'Galician', 'native': 'Galego'},
    {'code': 'he', 'name': 'Hebrew', 'native': '\u05e2\u05d1\u05e8\u05d9\u05ea'},
    {'code': 'hr_HR', 'name': 'Croatian', 'native': 'Hrvatski'},
    {'code': 'hu_HU', 'name': 'Hungarian', 'native': 'Magyar'},
    {'code': 'hy', 'name': 'Armenian', 'native': '\u0570\u0561\u0575\u0565\u0580\u0565\u0576'},
    {'code': 'id', 'name': 'Indonesian', 'native': 'Indonesia'},
    {'code': 'it', 'name': 'Italian', 'native': 'Italiano'},
    {'code': 'ja', 'name': 'Japanese', 'native': '\u65e5\u672c\u8a9e'},
    {'code': 'ka', 'name': 'Georgian', 'native': '\u10e5\u10d0\u10e0\u10d7\u10e3\u10da\u10d8'},
    {'code': 'kk', 'name': 'Kazakh', 'native': '\u049b\u0430\u0437\u0430\u049b\u0020\u0442\u0456\u043b\u0456'},
    {'code': 'km', 'name': 'Khmer', 'native': '\u1781\u17d2\u1798\u17c2\u179a'},
    {'code': 'ko', 'name': 'Korean', 'native': '\ud55c\uad6d\uc5b4'},
    {'code': 'ky', 'name': 'Kyrgyz', 'native': '\u043a\u044b\u0440\u0433\u044b\u0437\u0447\u0430'},
    {'code': 'lo', 'name': 'Lao', 'native': '\u0ea5\u0eb2\u0ea7'},
    {'code': 'lt', 'name': 'Lithuanian', 'native': 'Lietuvių'},
    {'code': 'lv', 'name': 'Latvian', 'native': 'Latviešu'},
    {'code': 'mg', 'name': 'Malagasy', 'native': 'Malagasy'},
    {'code': 'mk', 'name': 'Macedonian', 'native': '\u043c\u0430\u043a\u0435\u0434\u043e\u043d\u0441\u043a\u0438'},
    {'code': 'ms', 'name': 'Malay', 'native': 'Bahasa Melayu'},
    {'code': 'my', 'name': 'Burmese', 'native': '\u1019\u103C\u1014\u103A\u1019\u102C'},
    {'code': 'nb_NO', 'name': 'Norwegian', 'native': 'Norsk bokm\u00e5l'},
    {'code': 'nl', 'name': 'Dutch', 'native': 'Nederlands'},
    {'code': 'pl', 'name': 'Polish', 'native': 'Polski'},
    {'code': 'ps', 'name': 'Pashto', 'native': '\u067e\u069a\u062a\u0648'},
    {'code': 'pt_BR', 'name': 'Portuguese (Brazil)', 'native': 'Portugu\u00eas (Brasil)'},
    {'code': 'pt_PT', 'name': 'Portuguese', 'native': 'Portugu\u00eas'},
    {'code': 'ro', 'name': 'Romanian', 'native': 'Rom\u00e2n\u0103'},
    {'code': 'ru', 'name': 'Russian', 'native': '\u0420\u0443\u0441\u0441\u043a\u0438\u0439'},
    {'code': 'sk', 'name': 'Slovak', 'native': 'Sloven\u010dina'},
    {'code': 'sl_SI', 'name': 'Slovenian', 'native': 'Sloven\u0161\u010dina'},
    {'code': 'sq', 'name': 'Albanian', 'native': 'Shqip'},
    {'code': 'sr_ME', 'name': 'Serbian (Montenegro)', 'native': '\u0441\u0440\u043f\u0441\u043a\u0438\u0020\u0028\u045b\u0438\u0440\u0438\u043b\u0438\u0446\u0430\u002c\u0020\u0426\u0440\u043d\u0430\u0020\u0413\u043e\u0440\u0430\u0029'},
    {'code': 'sr_ME@latin', 'name': 'Serbian (latin, Montenegro)', 'native': 'Srpski (latinica, Crna Gora)'},
    {'code': 'sr_RS', 'name': 'Serbian', 'native': '\u0441\u0440\u043f\u0441\u043a\u0438\u0020\u0028\u045b\u0438\u0440\u0438\u043b\u0438\u0446\u0430\u002c\u0020\u0421\u0440\u0431\u0438\u0458\u0430\u0029'},
    {'code': 'sr_RS@latin', 'name': 'Serbian (latin)', 'native': 'Srpski (latinica)'},
    {'code': 'sv', 'name': 'Swedish', 'native': 'Svenska'},
    {'code': 'sw', 'name': 'Swahili', 'native': 'Kiswahili'},
    {'code': 'ta', 'name': 'Tamil', 'native': '\u0ba4\u0bae\u0bbf\u0bb4\u0bcd'},
    {'code': 'tg', 'name': 'Tajik', 'native': '\u0442\u043e\u04b7\u0438\u043a\u04e3'},
    {'code': 'th', 'name': 'Thai', 'native': '\u0e44\u0e17\u0e22'},
    {'code': 'tk', 'name': 'Turkmen', 'native': '\u0054\u00fc\u0072\u006b\u006d\u0065\u006e\u0020\u0064\u0069\u006c\u0069'},
    {'code': 'tr', 'name': 'Turkish', 'native': '\u0054\u00fc\u0072\u006b\u00e7\u0065'},
    {'code': 'tt', 'name': 'Tatar', 'native': '\u0442\u0430\u0442\u0430\u0440'},
    {'code': 'ug', 'name': 'Uyghur', 'native': '\u0626\u06c7\u064a\u063a\u06c7\u0631\u0686\u06d5'},
    {'code': 'ug@Latin', 'name': 'Uyghur (Latin)', 'native': 'Uyghurche'},
    {'code': 'ug@Cyrl', 'name': 'Uyghur (Cyrillic)', 'native': '\u0423\u0439\u0493\u0443\u0440\u0071\u0259'},
    {'code': 'uk', 'name': 'Ukrainian', 'native': '\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430'},
    {'code': 'ur', 'name': 'Urdu', 'native': '\u0627\u0631\u062f\u0648'},
    {'code': 'uz', 'name': 'Uzbek', 'native': '\u004f\u2018\u007a\u0062\u0065\u006b'},
    {'code': 'vi', 'name': 'Vietnamese', 'native': 'Ti\u1ebfng Vi\u1ec7t'},
    {'code': 'zh_CN', 'name': 'Simplified Chinese', 'native': '\u7b80\u4f53\u4e2d\u6587'},
    {'code': 'zh_HK', 'name': 'Traditional Chinese', 'native': '\u7e41\u9ad4\u4e2d\u6587'},
    {'code': 'zh_TW', 'name': 'Traditional Chinese (Taiwan)', 'native': '\u7e41\u9ad4\u4e2d\u6587 (\u4e2d\u570b\u9999\u6e2f\u7279\u5225\u884c\u653f\u5340)'}
]

# Sorting the list of dict using the key 'code'
LANGUAGES_SUPPORTED.sort(key=operator.itemgetter('name'))

# Creating LANGUAGES_SUPPORTED_CODES form the ordered LANGUAGES_SUPPORTED
LANGUAGES_SUPPORTED_CODES = {i['code'] for i in LANGUAGES_SUPPORTED}

# Versioning for exported questionnaire's
QUESTIONNAIRE_EXPORT_VERSION = '0.0.1'

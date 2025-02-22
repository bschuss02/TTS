# -*- coding: utf-8 -*-

import re
from packaging import version
import phonemizer
from phonemizer.phonemize import phonemize
from TTS.utils.text import cleaners
from TTS.utils.text.symbols import make_symbols, symbols, phonemes, _phoneme_punctuations, _bos, \
    _eos

# Mappings from symbol to numeric ID and vice versa:
_symbol_to_id = {s: i for i, s in enumerate(symbols)}
_id_to_symbol = {i: s for i, s in enumerate(symbols)}

_phonemes_to_id = {s: i for i, s in enumerate(phonemes)}
_id_to_phonemes = {i: s for i, s in enumerate(phonemes)}

# Regular expression matching text enclosed in curly braces:
_CURLY_RE = re.compile(r'(.*?)\{(.+?)\}(.*)')

# Regular expression matching punctuations, ignoring empty space
PHONEME_PUNCTUATION_PATTERN = r'['+_phoneme_punctuations+']+'


def text2phone(text, language):
    return text

    # # fuck
    # # print("text:", text)

    # # save phonemes from text to be re inserted later
    # token_list = []
    # token = ""
    # is_token_growing = False
    # for i, character in enumerate(text):
    #     if is_token_growing:
    #         token = token + character
    #     if character == "$":
    #         if is_token_growing:
    #             token_list.append((token, i - len(token)))
    #             token = ""
    #         is_token_growing = not is_token_growing

    # # print("token_list: ", token_list)

    # # remove phonemes from text
    # text_without_phonemes = ""
    # is_deleting = False
    # for i, character in enumerate(text):
    #     if character == "$":
    #         is_deleting = not is_deleting

    #     if not is_deleting:
    #         text_without_phonemes += character

    # text_without_phonemes = text_without_phonemes.replace("$", "")
    # text = text_without_phonemes
    # print("text_without_phonemes: ", text_without_phonemes)
    # return text
    '''
    Convert graphemes to phonemes.
    '''
    seperator = phonemizer.separator.Separator(' |', '', '|')
    # try:
    punctuations = re.findall(PHONEME_PUNCTUATION_PATTERN, text)
    if version.parse(phonemizer.__version__) < version.parse('2.1'):
        ph = phonemize(text, separator=seperator, strip=False,
                       njobs=1, backend='espeak', language=language)
        ph = ph[:-1].strip()  # skip the last empty character
        # phonemizer does not tackle punctuations. Here we do.
        # Replace \n with matching punctuations.
        if punctuations:
            # if text ends with a punctuation.
            if text[-1] == punctuations[-1]:
                for punct in punctuations[:-1]:
                    ph = ph.replace('| |\n', '|'+punct+'| |', 1)
                    ph = ph + punctuations[-1]
            else:
                for punct in punctuations:
                    ph = ph.replace('| |\n', '|'+punct+'| |', 1)
    elif version.parse(phonemizer.__version__) >= version.parse('2.1'):
        ph = phonemize(text, separator=seperator, strip=False, njobs=1,
                       backend='espeak', language=language, preserve_punctuation=True)
        # this is a simple fix for phonemizer.
        # https://github.com/bootphon/phonemizer/issues/32
        if punctuations:
            for punctuation in punctuations:
                ph = ph.replace(f"| |{punctuation} ", f"|{punctuation}| |").replace(
                    f"| |{punctuation}", f"|{punctuation}| |")
            ph = ph[:-3]
    else:
        raise RuntimeError(" [!] Use 'phonemizer' version 2.1 or older.")

    print('PRINTING FROM TTS -> ph', ph)

    return ph
    # joined_text = ph
    # displacement = 0
    # for phoneme_text, i in token_list:
    #     joined_text = joined_text[:i+displacement] + \
    #         phoneme_text + joined_text[i+displacement:]
    #     displacement += len(phoneme_text)

    # # print("joined_text: ", joined_text)

    # return joined_text
    # print("fuck")
    # print('text: ', text)
    # print('language: ', language)
    # print("ph: ", ph)
    # return ph


def pad_with_eos_bos(phoneme_sequence, tp=None):
    # pylint: disable=global-statement
    global _phonemes_to_id, _bos, _eos
    if tp:
        _bos = tp['bos']
        _eos = tp['eos']
        _, _phonemes = make_symbols(**tp)
        _phonemes_to_id = {s: i for i, s in enumerate(_phonemes)}

    return [_phonemes_to_id[_bos]] + list(phoneme_sequence) + [_phonemes_to_id[_eos]]


def phoneme_to_sequence(text, cleaner_names, language, enable_eos_bos=False, tp=None):
    # pylint: disable=global-statement
    global _phonemes_to_id
    if tp:
        _, _phonemes = make_symbols(**tp)
        _phonemes_to_id = {s: i for i, s in enumerate(_phonemes)}

    sequence = []
    clean_text = _clean_text(text, cleaner_names)

    # I CHANGED THIS to text from clean_text
    to_phonemes = text2phone(text, language)
    if to_phonemes is None:
        print("!! After phoneme conversion the result is None. -- {} ".format(clean_text))
    # iterate by skipping empty strings - NOTE: might be useful to keep it to have a better intonation.
    for phoneme in filter(None, to_phonemes.split('|')):
        sequence += _phoneme_to_sequence(phoneme)
    # Append EOS char
    if enable_eos_bos:
        sequence = pad_with_eos_bos(sequence, tp=tp)
    return sequence


def sequence_to_phoneme(sequence, tp=None):
    # pylint: disable=global-statement
    '''Converts a sequence of IDs back to a string'''
    global _id_to_phonemes
    result = ''
    if tp:
        _, _phonemes = make_symbols(**tp)
        _id_to_phonemes = {i: s for i, s in enumerate(_phonemes)}

    for symbol_id in sequence:
        if symbol_id in _id_to_phonemes:
            s = _id_to_phonemes[symbol_id]
            result += s
    return result.replace('}{', ' ')


def text_to_sequence(text, cleaner_names, tp=None):
    '''Converts a string of text to a sequence of IDs corresponding to the symbols in the text.

      The text can optionally have ARPAbet sequences enclosed in curly braces embedded
      in it. For example, "Turn left on {HH AW1 S S T AH0 N} Street."

      Args:
        text: string to convert to a sequence
        cleaner_names: names of the cleaner functions to run the text through

      Returns:
        List of integers corresponding to the symbols in the text
    '''
    # pylint: disable=global-statement
    global _symbol_to_id
    if tp:
        _symbols, _ = make_symbols(**tp)
        _symbol_to_id = {s: i for i, s in enumerate(_symbols)}

    sequence = []
    # Check for curly braces and treat their contents as ARPAbet:
    while text:
        m = _CURLY_RE.match(text)
        if not m:
            sequence += _symbols_to_sequence(_clean_text(text, cleaner_names))
            break
        sequence += _symbols_to_sequence(
            _clean_text(m.group(1), cleaner_names))
        sequence += _arpabet_to_sequence(m.group(2))
        text = m.group(3)
    return sequence


def sequence_to_text(sequence, tp=None):
    '''Converts a sequence of IDs back to a string'''
    # pylint: disable=global-statement
    global _id_to_symbol
    if tp:
        _symbols, _ = make_symbols(**tp)
        _id_to_symbol = {i: s for i, s in enumerate(_symbols)}

    result = ''
    for symbol_id in sequence:
        if symbol_id in _id_to_symbol:
            s = _id_to_symbol[symbol_id]
            # Enclose ARPAbet back in curly braces:
            if len(s) > 1 and s[0] == '@':
                s = '{%s}' % s[1:]
            result += s
    return result.replace('}{', ' ')


def _clean_text(text, cleaner_names):
    for name in cleaner_names:
        cleaner = getattr(cleaners, name)
        if not cleaner:
            raise Exception('Unknown cleaner: %s' % name)
        text = cleaner(text)
    return text


def _symbols_to_sequence(syms):
    return [_symbol_to_id[s] for s in syms if _should_keep_symbol(s)]


def _phoneme_to_sequence(phons):
    return [_phonemes_to_id[s] for s in list(phons) if _should_keep_phoneme(s)]


def _arpabet_to_sequence(text):
    return _symbols_to_sequence(['@' + s for s in text.split()])


def _should_keep_symbol(s):
    return s in _symbol_to_id and s not in ['~', '^', '_']


def _should_keep_phoneme(p):
    return p in _phonemes_to_id and p not in ['~', '^', '_']

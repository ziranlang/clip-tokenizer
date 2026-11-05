"""Test-only independent HuggingFace goldens; never imported by the package.

Use the existing Photos test venv. The pinned public tokenizer is the only
model input; no owner library, network or Python tokenizer reimplementation.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer

PIN = 'f7f3b7af117d467b58374797691a6438d3e6b9e9cef800dfd5dced7f697a90cd'
TEXTS = [
    'a photo of a cat', 'Hello, world!', ' café ', 'cafe\u0301',
    'Ångström A\u030angstro\u0308m', 'İSTANBUL ẞ Straße ﬃ',
    'ΟΣ', 'ΟΣΑ', "AΣ\u0301 A'Σ! A.Σ", 'Σ\u0345 AΣ\u0345',
    'Ελληνικά ἀνθρώπων', 'Привет, мир!', '中文照片 日本語の写真',
    '한국어 사진 각', 'مرحبا بالعالم', 'नमस्ते दुनिया',
    '🙂🚀👩\u200d💻 ❤️', '𐐀𐐧 𐐨𐑏', 'a\u00a0b\u2003c\u2028d\u3000e',
    'a\tb\nc\rd\ve\ff\u0085g\u1680h\u2029i\u202fj\u205fk',
    'a\x1cb\x1dc\x1ed\x1fe', '\x1c A \x1f', 'a\u200bb\ufeffc',
    '123 １２３ ١٢٣ Ⅳ ² ⅓ 𐅁', "I'm you're we've they'll she'd isn't can't I'd",
    "foo!!!'s a'b !!!??___+-=", 'foo—bar…“quoted”',
    '<|startoftext|>', '<|endoftext|>', '<|STARTOFTEXT|>', '<|ENDOFTEXT|>',
    'a<|endoftext|>b', 'a<|startoftext|>b', '!!!<|ENDOFTEXT|>!!!',
    '<|startoftext|><|endoftext|><|STARTOFTEXT|><|ENDOFTEXT|>',
    'abc xyz aaa aaaa', 'a ' * 180, 'x' * 512, 'é' * 256,
    '\u0344' * 200, '𝅘𝅥𝅮' * 100, 'a\u0315\u0300 a\u0300\u0315',
    'ﬃ① ÅΩK', 'a\u034fb', 'x\u202ey', '\u0301\u0323a',
]


def goldens(source, texts, photos=False):
    tokenizer = Tokenizer.from_str(source)
    tokenizer.enable_truncation(max_length=77)
    eos = tokenizer.token_to_id('<|endoftext|>')
    tokenizer.enable_padding(length=77, pad_id=eos, pad_token='<|endoftext|>')
    cases = []
    for text in texts:
        if photos:
            assert 0 < len(text.encode('utf-8')) <= 512 and text.strip() and '\0' not in text
        ids = tokenizer.encode(text.strip() if photos else text).ids
        assert len(ids) == 77
        cases.append({'text': text, 'ids': ids})
    return cases


def tiny_model(actual):
    tiny = copy.deepcopy(actual)
    vocab = {}
    points = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    next_point = 256
    by_byte = {}
    for byte in range(256):
        if byte in points:
            point = byte
        else:
            point = next_point
            next_point += 1
        by_byte[byte] = chr(point)
    for suffix in ('', '</w>'):
        for byte in range(256):
            vocab[by_byte[byte] + suffix] = len(vocab)
    merges = ['b c</w>', 'a b', 'ab c</w>', 'x y', 'y z</w>', 'xy z</w>', 'a a', 'aa a</w>']
    for merge in merges:
        vocab[''.join(merge.split(' '))] = len(vocab)
    for special in ('<|startoftext|>', '<|endoftext|>'):
        vocab[special] = len(vocab)
    tiny['model']['vocab'] = vocab
    tiny['model']['merges'] = merges
    tiny['post_processor']['cls'][1] = vocab['<|startoftext|>']
    tiny['post_processor']['sep'][1] = vocab['<|endoftext|>']
    for token in tiny['added_tokens']:
        token['id'] = vocab[token['content']]
    tiny['truncation'] = None
    tiny['padding'] = None
    return tiny


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('model', type=Path)
    parser.add_argument('--photos-output', type=Path)
    args = parser.parse_args()
    raw = args.model.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == PIN, 'unexpected actual model'
    actual = json.loads(raw)
    root = Path(__file__).resolve().parent
    tiny = tiny_model(actual)
    source = json.dumps(tiny, ensure_ascii=True, separators=(',', ':'))
    cases = goldens(source, TEXTS + ['', ' \t\n', '\0', 'a\0b', 'x' * 513])
    write_json(root / 'fixtures/tiny.json', tiny)
    write_json(root / 'fixtures/tiny-goldens.json', cases)
    # Embed the exact independently encoded fixture for all portable targets.
    embedded = '// Generated test-only HuggingFace fixtures; see oracle.py.\n'
    for name, value in [('Tiny', tiny), ('Goldens', cases)]:
        wire = json.dumps(value, ensure_ascii=True, separators=(',', ':'))
        chunks = [wire[i:i+512] for i in range(0, len(wire), 512)]
        embedded += name + ' :: (index: s32) -> string {\n    if index == {\n'
        for index, chunk in enumerate(chunks):
            embedded += f'        case {index}; return ' + json.dumps(chunk) + '\n'
        embedded += '    }\n    return ""\n}\n' + name + 'Count :: ' + str(len(chunks)) + ';\n'
    (root / 'fixtures.zi').write_text(embedded)
    if args.photos_output:
        write_json(args.photos_output, {'sha256': PIN, 'oracle': 'HuggingFace tokenizers',
            'oracle_version': __import__('tokenizers').__version__, 'cases': goldens(raw.decode(), TEXTS, photos=True)})
    print(f'Wrote {len(cases)} independent tiny-model and actual-model HF goldens')


if __name__ == '__main__':
    main()

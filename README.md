# CLIP tokenizer

Portable Ziran byte-level BPE for CLIP's 77-token text input. It uses canonical
Unicode 17 NFC/lowercase and exact L/N/White_Space properties from `std/unicode`.
There is no Python runtime, host regex, filesystem assumption, network access,
platform Unicode library or process-global model cache.

```zi
T :: #import "clip_tokenizer/Tokenizer";
model: T.Model
defer { T.Close(*model) }
if !T.LoadJSON(*model, tokenizer_json) { /* invalid/unsupported model */ }
ids: [77]s64
if !T.Encode77(*model, "a photo of a cat", ids[:]) { /* invalid input */ }
```

`LoadJSON(model, text) -> bool` copies its source and builds owned vocabulary
and merge caches once. The caller can release `text` immediately. The exact
pipeline is checked: NFC, Unicode-whitespace collapse, lowercase; CLIP's
inverted Split pattern followed by ByteLevel; BPE with `</w>`; normalized BOS
and non-normalized EOS added tokens; RobertaProcessing. Unsupported pipelines,
missing byte alphabet, duplicate vocabulary IDs/keys or merge pairs, missing
merge results and dependencies on later-ranked merges fail closed. Vocabulary
IDs must be dense. Merge ranking is integer order in the supplied array.
Padding/truncation settings in the JSON are overridden by the explicit
`Encode77` contract. Model IDs are read from the vocabulary/postprocessor,
rather than assuming the public model's 49406/49407 IDs.

`Close` releases every model allocation and is idempotent. Reload first closes
the old model; failure leaves it closed and reusable. Do not copy a `Model`,
mutate its fields or reload/close while another call uses it. All source bytes
and derived tables have stable owned storage until `Close`. Independent
`Encode77` calls can share a loaded model with separate output slices.

`Encode77(model, text, output: []s64) -> bool` requires exactly 77 caller-owned
signed 64-bit elements. It emits BOS, at most 75 body IDs, EOS, then EOS padding.
It handles added special tokens before/after normalization according to their
flags; an uppercase EOS spelling is ordinary text, while uppercase BOS is a
normalized special token. It neither trims Python whitespace nor rejects NUL
or empty strings. Those are application policies. On any failure, all supplied
output elements are zeroed, including when its length is wrong. No returned
view or per-call allocation escapes the call.

HF's lowercase normalizer maps each Unicode scalar independently. The package
therefore applies the reusable standard lowercase API to each scalar: Greek
`ΟΣ` becomes `οσ`, as the independent HF oracle requires. Whole-string
`std/unicode.LowerInto` retains its contextual final-sigma behavior (`ος`).

The bounded API rejects malformed UTF-8, over 4096 original input bytes,
models over 8 MiB, over 65,536 tokens, over 100,000 merges, token spellings over
4096 bytes, JSON nesting over 32, or over 400,000 structural JSON items. Model
parsing and all vector growth are fallible. A conservative normalization bound
uses Unicode17's maximum four canonical-decomposition scalars, three lowercase
scalars and four UTF-8 bytes per scalar. Generic std Unicode APIs have no such
application-specific ceiling. BPE processes bounded byte pieces using ranked
adjacent pairs, then stops generating body IDs after truncation.

Photos applies its existing adapter rules **before** calling this package:
reject over 512 original UTF-8 bytes, NUL, malformed UTF-8 or a Python-whitespace
blank query, then trim Python `str.strip` whitespace (`IsSpace`, including
U+001C..U+001F). Internal controls are ordinary tokenizer bytes; HF's regex
whitespace uses `IsWhiteSpace` instead. The Photos integration unit compares
this boundary against the actual pinned public tokenizer.

Run local tests from this canonical package, using the current canonical
toolchain (no dependency checkout/fetch):

```sh
build-queue -- make check
```

The tiny public synthetic model and frozen goldens are independently encoded
by HuggingFace `tokenizers` 0.23.2. Source and saved IR run on C, Go and both VM
runners. Cases cover canonical accents, sigma contexts, Unicode scripts,
emoji/joiners, whitespace/numbers, contractions, special-token flags, ranking,
padding/truncation, invalid input/model handling and repeated reuse/close.
The native allocator harness additionally proves zero retained per-call bytes
after 2000 encodes and 50 reloads, and injects failure at every allocation of
both encode and tiny-model load. Every failure clears outputs/model state and
releases partial storage; successful subsequent operations remain usable.

`tests/oracle.py` is test-only fixture generation, using the existing Photos
test venv and cached pinned tokenizer. It neither implements the algorithm nor
belongs to the package runtime. Regenerate explicitly with:

```sh
/mnt/storage/Projects/waozixyz/photos/build/venv/bin/python tests/oracle.py \
  /mnt/storage/Projects/waozixyz/photos/build/models/tokenizer.json \
  --photos-output /mnt/storage/Projects/waozixyz/photos/tests/fixtures/golden/clip-tokenizer.json
```

Code is BSD-3-Clause, matching Ziran. The tiny model is synthetic. Actual model
weights/vocabulary are not redistributed here; Photos preserves the upstream
CLIP license with its existing model cache. Unicode tables live in canonical
Ziran under its retained Unicode License V3.

# Visual fixture contract

Generated fixtures are design/test inputs, not archive records.

Every incoming-letter fixture must have:

- a stable fixture id;
- the prompt and generation date;
- provider/model or `manual fixture` provenance;
- a statement that it is fictional;
- source-reference notes that identify visual inspiration without claiming derivation or authenticity;
- an original generation asset outside Git when it exceeds the storage policy;
- deterministic crops/pads for both render profiles;
- a checksum for every checked-in derivative.

Never include a real accession number, copied signature, actual personal name, museum logo, or a seal that could make the generated artifact look authenticated. The fixture may use invented family names and historically plausible themes.

The first generation prompt is in [`incoming-qiaopi.prompt.md`](incoming-qiaopi.prompt.md).
The Ferrari-specific generated fixture uses the separately pinned exact prompt in
[`incoming-qiaopi-ferrari.prompt.md`](incoming-qiaopi-ferrari.prompt.md). The
checked-in incoming fixtures and the two deterministic blank huipi stationery
profiles are documented in [`fixtures/README.md`](../../fixtures/README.md).
Page 3 uses the same reply stationery plus structured annotation overlays, so
neither page 2 nor page 3 requires another generative image.

The reply-review policy is in [`reply-review.prompt.md`](reply-review.prompt.md).
Its fixture voice is a supportive Chinese-language teacher offering one concise,
uncertainty-aware reading, not an authoritative grader. [`contracts/review.example.json`](../../contracts/review.example.json)
is a redacted synthetic example: its identifiers, language, anchors, and
comments are fixture data, not participant ink or a provider response.

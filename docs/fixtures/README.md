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

The first generation prompt is in [`incoming-qiaopi.prompt.md`](incoming-qiaopi.prompt.md). The blank page is programmatic. Page 3 uses the same paper field plus structured annotation overlays, so it does not require a second generative image.

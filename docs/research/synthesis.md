# Research synthesis and design implications

## Local sources reviewed

- The final `If Letters Home Could Sing` paper and its Markdown working source.
- Qiao pi images for accessions `2000-06963-004` and `2000-06965-002` as visual/material references.
- The heart-rate system diagram from the earlier installation concept.
- The reMarkable backup and recovery README, active runtime snapshots, tested CJK installer, QMLDiff payloads, fake-device tests, and live-trial records.
- The repository's earlier letter-reveal, Web Bluetooth, WHOOP, handwriting, and heartbeat/audio code.

The paper is used as a conceptual source, not a publication-ready authority: the local final PDF still contains visible editorial notes and incomplete references.

## Historical reading

The local paper's strongest contribution is its insistence on family-scale histories: money received, siblings' education, a mother's health, tonics, distance, and a hoped-for visit. These ordinary concerns complicate nationalist readings of overseas Chinese correspondence.

Shuhua Chen's cosmopolitan reading of qiao pi reinforces three design requirements:

- avoid flattening the material into a single heritage label;
- preserve silence, uncertainty, mediation, and what is lost in transit;
- let a contemporary reader re-enact the act of writing without claiming to recover the historical writer's interiority.

The history of `daixie` (dictated or proxy-written letters) is especially important. Handwriting is not reliable proof of direct authorship; generated handwriting must never be presented as an authentic writer's hand.

Hong Liu and Huimei Zhang describe qiao pi as a remittance-letter system and Singapore as a migration/communication hub. Their discussion of `huipi`—the acknowledgement or reply—supports making reciprocity, not passive viewing, the centre of this experience.

## Device findings

- Paper Pro / Chiappa: `2160 × 1620`, 11.8-inch 4:3 display.
- Paper Pro Move / Ferrari: `1696 × 954`, 7.3-inch 16:9 display.
- Both project devices are on OS `3.28.0.162` and have verified full backups.
- Both have Wi-Fi and USB-C but no Bluetooth.
- Xochitl is proprietary; reMarkable does not promise custom patch compatibility between releases.
- Existing Xovi/QMLDiff CJK patches are exact-version/hash pinned and rollback protected.
- Xovi is not currently boot-persistent on these devices.
- The stock screenshot helper must not be used under Xovi because an observed signal interaction restarted Xochitl.

These facts favour a minimal QMLDiff launcher plus an isolated AppLoad app, with exact-version preflight and hardware work held behind approval.

## Provider findings

### OpenAI images

The current official image guide identifies `gpt-image-2` as the latest GPT Image model and recommends the Image API for a single prompt-to-image request. Its custom-size limits drive the render profiles in this repo. Provider access and organisation verification may still be required for the live adapter, but fixtures and all portable work must run without a live key.

### WHOOP

WHOOP's public OAuth API provides profile and aggregate cycle/recovery/workout/sleep records. It does not provide continuous live heart rate. A WHOOP can broadcast the BLE Heart Rate Service; therefore the live path is:

`WHOOP strap → phone/edge BLE listener → session gateway → tablet session`

OAuth remains useful for explicit account connection and aggregate context. It is not the transport for first-ink-to-submit samples.

## Privacy findings

Singapore's PDPA duties translate into a plain product rule: tell the participant what is captured and why, obtain meaningful consent, collect only what the encounter needs, secure it, stop retaining it when no longer needed, and permit withdrawal/deletion. A participant must be able to write and receive marginalia without linking WHOOP.

## Primary technical references

- [OpenAI image generation guide](https://developers.openai.com/api/docs/guides/image-generation)
- [reMarkable developer documentation](https://developer.remarkable.com/documentation/)
- [AppLoad](https://github.com/asivery/rm-appload)
- [QMLDiff](https://github.com/asivery/qmldiff)
- [WHOOP developer documentation](https://developer.whoop.com/docs/)
- [WHOOP heart-rate broadcast support](https://support.whoop.com/s/article/Heart-Rate-Broadcast)
- [Singapore PDPC obligations](https://www.pdpc.gov.sg/overview-of-pdpa/the-legislation/personal-data-protection-act/data-protection-obligations)

## Unresolved reference

No local file or unambiguous public result identified the specific `Dear You` work in the brief. A link, creator, or image is still needed before borrowing anything more specific than the broad correspondence-as-ritual idea.

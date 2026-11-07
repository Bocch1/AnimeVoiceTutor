# Third-party components and media

AnimeVoiceTutor's application code is distributed under the [MIT License](LICENSE). Other software, models and media retain their own license terms; an application-code license does not grant rights to those assets.

- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR): optional speech-recognition engine/model family. Check the upstream code license and the specific downloaded model's license and model card.
- [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS): optional speech-synthesis engine. Check its upstream license, dependencies and distribution requirements.
- PyTorch, uv, FFmpeg, Web dependencies and fonts: distributed or downloaded under their respective licenses.
- Character packs: portraits, image-derived animation points, names, recordings, reference clips, generated greetings and fine-tuned voice weights may be subject to distinct copyright, performer, privacy, model-license or contractual restrictions.

**Core does not include** character artwork, trained voice weights, reference recordings, third-party engine source, or provider credentials. An optional pack is a separate distribution and requires authorization for every included item. The existence of a pack-building tool does not authorize redistribution or voice impersonation.

## Optional upstream downloads

The first-run wizard offers to download GPT-SoVITS source from its original repository (`https://github.com/RVC-Boss/GPT-SoVITS`), subject to its own MIT license and separate third-party model resource terms. Qwen3-ASR model downloads are obtained separately from the official Qwen model repository under the license indicated in its model card. No trained character weights, artwork or reference media are included in this Core repository. A takedown/contact statement is not redistribution authorization.


## Optional first-run third-party downloads

- GPT-SoVITS source: `https://github.com/RVC-Boss/GPT-SoVITS` (separate upstream license). A candidate Git revision is listed in `release/install_specs/voice_baseline.json`.
- GPT-SoVITS pretrained archive: `https://huggingface.co/XXXXRT/GPT-SoVITS-Pretrained` (upstream license and model restrictions apply). Download is optional and requires a separate provenance review before public redistribution.
- FFmpeg: optional winget package `Gyan.FFmpeg`; FFmpeg and the distributor have separate license obligations.
- Qwen3-ASR: optional model downloaded from its publisher; check its model-card terms.

The Core ZIP does not contain any of the above binaries or model weights.

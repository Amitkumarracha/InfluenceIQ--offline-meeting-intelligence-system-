# Third-party runtime and model notices

InfluenceIQ's native implementation reuses these upstream components and pretrained models. They were not trained by this project.

- whisper.cpp v1.7.6: https://github.com/ggml-org/whisper.cpp/tree/v1.7.6 — MIT; see Whisper-MIT.txt. The imported GGML speech model is selected by the user; the tested model is multilingual Whisper base.
- sherpa-onnx v1.13.8: https://github.com/k2-fsa/sherpa-onnx/releases/tag/v1.13.8 — Apache-2.0; see Sherpa-Apache-2.0.txt.
- Bundled ONNX Runtime reports version 1.28.2: https://github.com/microsoft/onnxruntime/tree/v1.28.2 — see ONNXRuntime-MIT.txt and ONNXRuntime-ThirdPartyNotices.txt from that tag.
- Speaker segmentation is the Sherpa ONNX conversion of pyannote/segmentation-3.0: https://huggingface.co/pyannote/segmentation-3.0. Its model card lists MIT; the upstream pyannote.audio MIT notice is included in Pyannote-MIT.txt.
- Speaker embeddings use the public converted 3D-Speaker ERes2Net model: https://github.com/modelscope/3D-Speaker. The upstream toolkit is Apache-2.0. The full Apache license is included in Sherpa-Apache-2.0.txt.

Conversion/model sources and checksums are documented in the research handbook, chapter 19, and scripts/setup_android_speakers.py. These notices accompany the development APK; no AMI corpus audio is bundled.

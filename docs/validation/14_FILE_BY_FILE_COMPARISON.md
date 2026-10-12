# File-by-file older/current comparison

[Handbook index](../handbook/README.md)

Audit date: **7 October 2026**. Exact source/config/documentation scan: **147 current files**, **81 older files**, **49 identical**, **32 modified**, **66 current-only**, **0 older-only**. A modified empty placeholder is a modification, not a newly absent filename.

## Scope and interpretation

Root first-party text/config files plus `src/`, `scripts/`, `tests/`, `frontend/`, `android/`, and `notebooks/` were compared. Included extensions: Python, shell, Markdown, YAML/TOML/text/JSON, JS/JSX/TS/TSX/CJS/CSS/HTML, Java/C++/headers/XML, Gradle/KTS/properties/CMake. Root `.gitignore` and `.env.example` are included; secrets are excluded.

Excluded: this new handbook folder; hidden directory trees including `.git`, `.cxx`, `.venv`, `.runtime`, `.bootstrap`; node_modules, vendor, build, dist, design screenshots, datasets, model weights, outputs, databases, bundled JRE, machine-home state, and binary artifacts. Extensionless historical `terminal output ` was inspected separately, not counted as source. The root README checksum includes the navigation link added in this documentation task.

“Identical” means identical bytes, not just similar logic. SHA-256 is over raw bytes, including newline differences. Counts are for this defined first-party scope, not all filesystem files and not Git-tracked-only files. Android alternate Gradle configuration is included; generated `.cxx` trees are not.

## Changes that matter most

The older `src/pipeline/orchestrator.py`, `src/utils/cache.py`, and `scripts/validate_setup.py` are empty placeholders; current versions implement those responsibilities. PPT modules, semantic/temporal alignment, evidence linking, evaluation baselines and ablations are identical. See [01](../research/01_PROJECT_HISTORY_AND_COMPARISON.md) for meaning and [11](../research/11_EVALUATION_BASELINES_AND_ABLATIONS.md) for inherited evaluator limitations.

## Modified files (32)

| File | Older bytes / lines | Current bytes / lines | Older SHA-256 | Current SHA-256 |
| --- | ---: | ---: | --- | --- |
| [.env.example](../../config/.env.example) | 300 / 6 | 309 / 7 | `ef7df110a9390acc3696320acaa13127351ad14a93bb0f183c75500a4a22ca46` | `4bc5f6bcf9272259693d86e9679c43a807181f23f261b5e8f5f7e1cffd36f5cf` |
| [.gitignore](../../.gitignore) | 626 / 50 | 971 / 72 | `916988a5a9e9c9ff8a3d4092751e9f49b0e0b7081fa85d492b869aefcd3f2054` | `75ec6771354767290801095e1121b04439f7d645e895aa52c6efdbbe8d6b1a30` |
| [README.md](../guides/QUICK_START.md) | 8333 / 179 | 11321 / 145 | `ad649a7a856e2d0e84e5c59077644b58915bdc490e1c0785d6af3e1db54d8eb7` | `55478e71bd98dbf00d2b632c501e0641d48ce30e9712bec5d35426d79307f815` |
| [api.py](../../backend/api.py) | 11680 / 284 | 24052 / 544 | `cab97c737d07f99f56440cea9b6a4c14f79e0a332b894b0791f55bf908862023` | `11468483c7d4d7dd3ba2f087fdc1a69aa394facd81268c4ad1cc77eea387ae2c` |
| [config.yaml](../../config/config.yaml) | 4867 / 171 | 5396 / 184 | `ee2f2f84c7534d5d2a63f288dca39acdc856ae727bcdaa0f9933c6ab40e99fb2` | `facd6fc3d2bbf7f3feb52ac839e7d38183828ae0f2e4aab8b4d998ddec7825f3` |
| [frontend/src/App.jsx](../../frontend/src/App.jsx) | 46185 / 706 | 64332 / 868 | `c616d4a6719acb5247db5b2833146506e1bf7d5aeb714203987c2321a4f74591` | `06e6a150647c1587c869a2f535f7555dc4bac1978be18b20a9b9f866c89a0af0` |
| [frontend/src/index.css](../../frontend/src/index.css) | 337 / 11 | 900 / 23 | `19f826c494dfe56c19d84999692c273acca7b9ffcf72b4ad870371a053cda155` | `b73e5e6adb6ae3672564ab83a747e266e11ec31c217467af6f29eb4cea3410b5` |
| [frontend/vite.config.js](../../frontend/vite.config.js) | 161 / 7 | 220 / 9 | `e1eefd0ed1639c88d1213884ef760516884db9e168190e223fee6b063ad3e088` | `97135dc9917afd1e3678e05b0b466f7c523454d7e8b9b944361c620074010aaf` |
| [requirements.txt](../../environment/requirements.txt) | 158 / 14 | 628 / 29 | `ca584d47a6a8aec98a4c75e065fa0343b1341d105d0c12b02fa1c29043184238` | `97303feb79fa2f6ed55b10543073525790575291cd780edd8f095a9dfc851e75` |
| [scripts/process_new_meeting.sh](../../scripts/process_new_meeting.sh) | 3051 / 73 | 344 / 9 | `53ce3e8d15f65aa70ac99cc9d75cbc39ce3be97f25bfe0aacbb7ffe32cf63a16` | `a43fdfa4c5ed0a58b608ec4801f8ebafb83c928c1c65bf8fe3ead6c22e03c6ee` |
| [scripts/run_pipeline.py](../../scripts/run_pipeline.py) | 22101 / 549 | 22686 / 558 | `263ed96126c93d55ac42cd328b19df43fbcd50b941271d0dc3f54f0d68ad91d1` | `fdb689770d4d4a75e983670806b2fb9754efdbf359bb91ae5e2fc5d937e31b51` |
| [scripts/validate_setup.py](../../scripts/validate_setup.py) | 0 / 0 | 2616 / 51 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `5300169d01c26d884216b1945acc11e027f72e2b1ee527ec6c6d43ac3ec729f2` |
| [src/audio/asr.py](../../src/audio/asr.py) | 13252 / 374 | 21236 / 478 | `dd841a0fb860e9d40fd4fb57df361248e7d6b1b9a96a4d245bf30cca19c689d7` | `17176d0643e835707635c7ef41a27c796f95a1132b4f95bbe381860003d670aa` |
| [src/audio/diarization.py](../../src/audio/diarization.py) | 10798 / 322 | 10620 / 300 | `f5018d1d2b091b5bcd2bd435c1bd9fb3294d7ace4ae40a9d066e1b58468cda64` | `6be8262075c1a81513539d2e109746678d04673a6f26b2d2884e3f2e6204c0f6` |
| [src/audio/preprocess.py](../../src/audio/preprocess.py) | 3061 / 98 | 3308 / 70 | `a8c96404913295bd80c3aec57fc022192d05c1d93fbc9bdab21865fd2c555480` | `4aa67b83e8be9d7ecf8e21954647e475fb13f04e3ea020f78a02b66b06db77eb` |
| [src/audio/vad.py](../../src/audio/vad.py) | 3805 / 130 | 2540 / 57 | `39f2d411b81fa6fd9e02de53ffe0bc72475c761bf70992935c5fb27b2d860890` | `73aec9ad5bcb405d5c9f1d8abf2e88a1e3078faafa90ce8ddba6fe9cf0a62253` |
| [src/evaluation/metrics.py](../../src/evaluation/metrics.py) | 26136 / 752 | 25392 / 715 | `d64e674d9e7f110e7f4835236963386ac3f2e61f6664cd678a573f9e33e8956c` | `01190a0ea8a83875cdeeffcf382d62f9cad8ae5d2b2bb26bfaf1f2a37b6c17fc` |
| [src/fusion/multimodal_representation.py](../../src/fusion/multimodal_representation.py) | 16015 / 467 | 16901 / 478 | `2315d20ffe8b13c15984aaa8078fa3b5029cab180eee2bd39c1beeae01dde312` | `4a602a7446c9b8c00f996c443fef2bd2fce30d0689ad7f27b4f470bd6539b6b2` |
| [src/meeting/decisions.py](../../src/meeting/decisions.py) | 29986 / 807 | 30549 / 812 | `5a4252c6ce2ead2c40c9e4968c713123f7ddc6ab94d5650d9f4f09aa4302c3b6` | `d3336edebca2e6c39833171b8a05b92a1b3fa224992a5744d7c1e3c029381f61` |
| [src/meeting/events.py](../../src/meeting/events.py) | 17890 / 474 | 21427 / 509 | `45c23c659d4fca9f449f9aa247b63c88f4214e3ae84cfa18c6aa7c4859414627` | `d911195cd12d0403e094d0c34ef4594c2053164ed58bb48da12a1dd8e15160d6` |
| [src/meeting/influence.py](../../src/meeting/influence.py) | 40832 / 1068 | 41564 / 1078 | `37fa9b4ef1ea2e9e61fe5cbc018ee88d6ccfb9a257b0498975611c706094a477` | `1b4f5f3590b536be98a481f9da700c63e0e1846b22c66f77686a8f16834bb45b` |
| [src/meeting/interaction.py](../../src/meeting/interaction.py) | 23274 / 627 | 23938 / 634 | `b34be407714158f1d13ced061bce9ea6a737940af8171726521161a0c0492087` | `ed430ce82ecfa055dd5b5c6992bc063e5d7d417b8c2ba96a88fe106c73632392` |
| [src/pipeline/orchestrator.py](../../src/pipeline/orchestrator.py) | 0 / 0 | 7464 / 130 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `7e4fbff3fc3b02cb64622bf7edf7eeebabb4e91a631c2cb837af7761a3e12b0c` |
| [src/report/exporter.py](../../src/report/exporter.py) | 34535 / 829 | 35044 / 838 | `7247dad0d81bd4e5598ca91128d93c5a53fa1ad367d7fdc660380d9515fbb01c` | `bed2fa61decdb8c33f38a587e51363c25946db87ebc66e5c73c8c26c7265f0ec` |
| [src/report/generator.py](../../src/report/generator.py) | 29538 / 792 | 30166 / 801 | `22d7489b0f021f899428a94a048971b52eab42ea728741f4a94482b2d3e1f37d` | `7e1336e47c81ac16eb3cb7589f062ca52a7a2b8b6848eecba02d524a7e567441` |
| [src/utils/cache.py](../../src/utils/cache.py) | 0 / 0 | 1154 / 37 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `6a8aabdf951ad7e500419c2796bc31ac37942db36b8e59bf38f4a858f2512c8d` |
| [src/utils/checkpointing.py](../../src/utils/checkpointing.py) | 3618 / 98 | 3624 / 99 | `3eac8503e9b913ebd95edf662ceb93cc9af313e974abf1a54168b5cbc5d79c95` | `dbc56d61000e2cdc4f19810d45e7199744d4e154eb3a5f10b6dd76dd23b8e778` |
| [src/utils/config.py](../../src/utils/config.py) | 1775 / 57 | 2334 / 66 | `b49f656fae2d308bb688c9171728f38fde747f26f7e0c9fc5ecf2a23116909b4` | `19c40ce5c815e03f3a8f9aa5a9f31a504d92a26e9fd36fdff360a358e733ec38` |
| [start_app.sh](../../scripts/start_app.sh) | 564 / 23 | 420 / 9 | `04352ba8bb2973e9e45b37437f46d9eeab5655d193ec4955f08ea5672764a830` | `df22026fa9823efc4c3ffd874cb868b2ef4f0dbeccdc8151025666f49f747a33` |
| [tests/test_alignment.py](../../tests/test_alignment.py) | 22868 / 569 | 22906 / 570 | `3bf772098dc0e1fefefb2549759e7553df7b4b7213c86b3d5895f6b76144e1a4` | `d2add83f19289c3cf0bb41acc12275754fe46dc310deb353a0f700d2b1bed12c` |
| [tests/test_audio.py](../../tests/test_audio.py) | 25954 / 601 | 26043 / 602 | `ae4813d7292ccedbf76e84c4c05de4be8fc318b7ef447829eab5616046cffd28` | `2703274c65beac053a632995a5f065c488e094e432802e014777cdb2ee1559ed` |
| [tests/test_evaluation.py](../../tests/test_evaluation.py) | 29032 / 725 | 29076 / 725 | `831f05bed98fb20b4ad8a28ddf0035305e660bf0437434239e3dca0d9fcdc066` | `bd588fd32b0d5d1ce38a1dd2415eb784701bf1ab0b491db8debe65e9f4d47bb7` |

## Current-only files (66)

| File | Older bytes / lines | Current bytes / lines | Older SHA-256 | Current SHA-256 |
| --- | ---: | ---: | --- | --- |
| [EFFICIENCY_IMPROVEMENTS.md](EFFICIENCY_IMPROVEMENTS.md) | — | 8274 / 64 | `absent` | `b376577098363befed37f965c12ede73cc16601911d76d12a567a000489760ed` |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | — | 18794 / 163 | `absent` | `9c7a4a687336010647fcf9c1c46ab5fa2994d70202005edf3fcf5f7f783e09b1` |
| [REPOSITORY_REVIEW.md](../history/REPOSITORY_REVIEW.md) | — | 5427 / 27 | `absent` | `c3850451b63b42a6c79ca9b7363d2c3ba4c69b749ce3f4b1e1800eeb9bd5334d` |
| [RUN_MANUALLY.md](../guides/RUN_MANUALLY.md) | — | 9026 / 159 | `absent` | `c5a79adfc7e3ee80f59bcbf09d86cdad066f3090017e9e633bac36e38f5a168b` |
| [android/DESIGN.md](../android/DESIGN.md) | — | 10285 / 101 | `absent` | `bca605853ddafc371e29371535b8ecd0503f2314be0ddf017485b5abc2e25342` |
| [android/README.md](../android/README.md) | — | 5868 / 67 | `absent` | `f93ba3e314122d470d88e7319c6726ab7b99d033fa8366819844db53442cef1b` |
| [android/app/build.gradle.kts](../../android/app/build.gradle.kts) | — | 976 / 46 | `absent` | `b7618bf7bd3e48fd94f7eeea075e7e38c26bb057db3f90f15229b3a9a68a6a49` |
| [android/app/src/main/AndroidManifest.xml](../../android/app/src/main/AndroidManifest.xml) | — | 1459 / 19 | `absent` | `fbd7990e4c30d9f5ff86368d159b7b9b51c33e270e75b97b6998824c0d31844d` |
| [android/app/src/main/assets/event_blockers.json](../../android/app/src/main/assets/event_blockers.json) | — | 1228 / 20 | `absent` | `8291d8fb75a6a812555032acb736d898fc3b617cf5db75548f79aaaf2d9c9898` |
| [android/app/src/main/assets/event_patterns.json](../../android/app/src/main/assets/event_patterns.json) | — | 6295 / 154 | `absent` | `b40516dd72b780ed30b3009fbf6219a7df4dd1453f0339b52dd6f1e87fff018a` |
| [android/app/src/main/cpp/CMakeLists.txt](../../android/app/src/main/cpp/CMakeLists.txt) | — | 673 / 14 | `absent` | `f46342222e535c8d7b2e9abdfadeec57615f5f971f3803d13e818c23102d01d7` |
| [android/app/src/main/cpp/whisper_jni.cpp](../../android/app/src/main/cpp/whisper_jni.cpp) | — | 4681 / 92 | `absent` | `848ef7e67d2105c8eb2ba6ccb42877d1f893bd9e51ac3b8885435c2bf0926275` |
| [android/app/src/main/java/org/meetiq/offline/AudioPlaybackController.java](../../android/app/src/main/java/org/meetiq/offline/AudioPlaybackController.java) | — | 2329 / 41 | `absent` | `3b6e80b6d5bdc05f0cc7f3e03c15f2d75932616d11f94bc6df99ff466d3327b9` |
| [android/app/src/main/java/org/meetiq/offline/EventRules.java](../../android/app/src/main/java/org/meetiq/offline/EventRules.java) | — | 1664 / 39 | `absent` | `af240abba152d0f27551e3ecbb2e350641682069fb86553da42735ccfa37c714` |
| [android/app/src/main/java/org/meetiq/offline/LocalTransfers.java](../../android/app/src/main/java/org/meetiq/offline/LocalTransfers.java) | — | 5026 / 79 | `absent` | `85e1fd7b3a13edc9ff0e1c1eb18669491540bce99b0d2e780b2f3b6c78c23d6f` |
| [android/app/src/main/java/org/meetiq/offline/MainActivity.java](../../android/app/src/main/java/org/meetiq/offline/MainActivity.java) | — | 46571 / 503 | `absent` | `ab81267426ddfdd458b443007b64b6bdfaae7096f104c17ba775791751739dc3` |
| [android/app/src/main/java/org/meetiq/offline/MeetingProgress.java](../../android/app/src/main/java/org/meetiq/offline/MeetingProgress.java) | — | 1280 / 25 | `absent` | `f0ed0e00e64b6f9f6bd0cd7e4e8520604ae477b6217b80e78502e8e628e406cc` |
| [android/app/src/main/java/org/meetiq/offline/MeetingRepository.java](../../android/app/src/main/java/org/meetiq/offline/MeetingRepository.java) | — | 7104 / 115 | `absent` | `e445104e268b22623fb0c4ac17571306c00efcf8eb596407badb955856a173ed` |
| [android/app/src/main/java/org/meetiq/offline/MeetingService.java](../../android/app/src/main/java/org/meetiq/offline/MeetingService.java) | — | 15460 / 241 | `absent` | `aaf5821d0639fb2a578cdc4f5c98729af9bcb7ec71e5db173ae534b71bfd1e9e` |
| [android/app/src/main/java/org/meetiq/offline/NativeWhisper.java](../../android/app/src/main/java/org/meetiq/offline/NativeWhisper.java) | — | 536 / 13 | `absent` | `daa3da8523a8d0e5f17951950a027fc6630c363ef78a708ef9113b9399f02789` |
| [android/app/src/main/java/org/meetiq/offline/Ui.java](../../android/app/src/main/java/org/meetiq/offline/Ui.java) | — | 11250 / 140 | `absent` | `011cabe332ad8e19c95e164df8494bf3d977c8512a392aa622812277e03e4b94` |
| [android/app/src/main/java/org/meetiq/offline/WavAudio.java](../../android/app/src/main/java/org/meetiq/offline/WavAudio.java) | — | 3674 / 61 | `absent` | `20d5a9a2ba5df3f3f136e3c398472647031d212f78b9c4847c51c22f108ee01a` |
| [android/app/src/main/java/org/meetiq/offline/json/Json.java](../../android/app/src/main/java/org/meetiq/offline/json/Json.java) | — | 9673 / 268 | `absent` | `54a546772db02f19967ae8dbfee9ec6c61cf35bd2459854d0e9290cf5fbc8d83` |
| [android/app/src/main/res/drawable/ic_launcher.xml](../../android/app/src/main/res/drawable/ic_launcher.xml) | — | 732 / 8 | `absent` | `39ae4809a24c25e676b70877a863a15094afb23a36f5aa499aa2f292bbc6e583` |
| [android/app/src/main/res/values-night/styles.xml](../../android/app/src/main/res/values-night/styles.xml) | — | 708 / 13 | `absent` | `b658c11dc2460164c46af514c2d942418854136271f7bb1da0327e808f9380de` |
| [android/app/src/main/res/values/styles.xml](../../android/app/src/main/res/values/styles.xml) | — | 712 / 13 | `absent` | `2dab1a9fd2a343e78252b4f030b840b168bf0e2b4b6ed52974febd14b418d02c` |
| [android/build.gradle.kts](../../android/build.gradle.kts) | — | 74 / 3 | `absent` | `06f540df4fff0ab59875015d3b5d083c51e7952d848a094c969b92fd5418d773` |
| [android/build.sh](../../android/build.sh) | — | 2705 / 48 | `absent` | `356429ab72acfa85cd21dd4aea08ea01615b588e3b263ae072f9c921b309fa87` |
| [android/gradle.properties](../../android/gradle.properties) | — | 334 / 9 | `absent` | `3a7ea0fd6663124def0023dd660c27bdc9a766a7c6a4919c804db231fa75afff` |
| [android/gradle/wrapper/gradle-wrapper.properties](../../android/gradle/wrapper/gradle-wrapper.properties) | — | 200 / 5 | `absent` | `55fbb41e499214b5efbabf03bcdb440d93296665570bf6688f4cd44c320d9e5e` |
| [android/local.properties](../../android/local.properties) | — | 340 / 8 | `absent` | `72c51629f05ad0e6f4039c72f8f3bb22ebb0377fdc70d55a7cf8366cc1bd2906` |
| [android/settings.gradle.kts](../../android/settings.gradle.kts) | — | 536 / 24 | `absent` | `d0ea24a2452d895effcfb4bd49a0b2fe149c3586e70f5b5d934b72cdcb991e4b` |
| [android/setup.sh](../../android/setup.sh) | — | 1805 / 37 | `absent` | `5f9598721abec842fd014d990601b5e1b9a115eb055e0c5b7f5b7126a505766e` |
| [android/test.sh](../../android/test.sh) | — | 1347 / 22 | `absent` | `61b0759e501148b18df8f77539819990884dc31c928add393d8bba8d7a57b99f` |
| [android/test/EventRulesTest.java](../../android/test/EventRulesTest.java) | — | 2007 / 35 | `absent` | `b437ee9df6a687e64e9f27a59b3425d41dbf030610f42befd22951c67e4c9bc6` |
| [android/test/MeetingProgressTest.java](../../android/test/MeetingProgressTest.java) | — | 1215 / 20 | `absent` | `0834e35363d472f72cf2a94f641e3636dbe471e69b82b2deccfa107d9facc875` |
| [android/test/WavAudioTest.java](../../android/test/WavAudioTest.java) | — | 2431 / 42 | `absent` | `14e4cece47ec9a6d735f529448dd2713f6e5b87a4a8c67efd09364096baf4218` |
| [efficiency-results.json](../../outputs/evaluation/efficiency-results.json) | — | 4567 / 147 | `absent` | `abb4c981ff849dc6db09943ade45c781c6f5f14128f019f7781c26f012237e8d` |
| frontend/src/MeetingNotes.jsx (historical; removed in chapter 18) | — | 5270 / 61 | `absent` | `816317b40a1167e371c9e8e129a3407bc122bc5c2ad05e8269c3e1deff572bf5` |
| [frontend/src/recordingStore.js](../../frontend/src/recordingStore.js) | — | 1497 / 29 | `absent` | `3871c7cfaa2a5ff09106d74029912e144b03949a1b40b7b01ba6877fcf8eea10` |
| [requirements-lock.txt](../../environment/requirements-lock.txt) | — | 2268 / 125 | `absent` | `18283eb1c4e2c3d5aeddb7f3b84839d50180497439ee1cf00e748001d8c99592` |
| [scripts/benchmark_ami.py](../../scripts/benchmark_ami.py) | — | 4266 / 81 | `absent` | `9ca14355fe54325deb5d51a754f02cfd5ad8832c40f2a5e7f9e5fa29aa16abec` |
| [scripts/check_android_design.py](../../scripts/check_android_design.py) | — | 3510 / 83 | `absent` | `aea942ed1a7bdf9ce446876bd317a5c34cce5073e23ad44eec40fa8b41486e98` |
| [scripts/download_models.py](../../scripts/download_models.py) | — | 1462 / 36 | `absent` | `0413927353b4b0270974a7f903974feaf9453c20a327b60be63c53473efcad66` |
| [scripts/evaluate_recordings.py](../../scripts/evaluate_recordings.py) | — | 3988 / 76 | `absent` | `68f8a07ef05cedf8059622e31bb28a461ea4cd8ba06ad15b0148a5346e54055e` |
| [scripts/export_event_rules.py](../../scripts/export_event_rules.py) | — | 844 / 20 | `absent` | `3d591405bb810a9d23a0e1e2502f62266bf6c20b8be93a40fa14596332838229` |
| [scripts/process_meeting.py](../../scripts/process_meeting.py) | — | 735 / 16 | `absent` | `69f74bb2678d07c8d49f8d2bae2d96f3762b37636ae60a207bfb232e0f1125ce` |
| [scripts/reset_password.py](../../scripts/reset_password.py) | — | 770 / 20 | `absent` | `837880f7813a8fe154cb7daa197e4d9a0174cadddba5dda1c3af8e5b96e20516` |
| [scripts/setup.sh](../../scripts/setup.sh) | — | 874 / 17 | `absent` | `48da9ead9450e4ad9d2f1d28921d78df54dd17c2266011f21698b5f9c7e84972` |
| [scripts/smoke_long_offline.py](../../scripts/smoke_long_offline.py) | — | 2471 / 55 | `absent` | `4080791051042e39ac807356ed9ed40d52c6cbc9675e0332c7622ddaa0d955ae` |
| [scripts/test_browser.cjs](../../scripts/test_browser.cjs) | — | 2164 / 28 | `absent` | `6898a8a3c722d6194a9175a7b45f565df1ecff54c7f1c605ac24d8bbd606cfff` |
| [scripts/test_browser_offline.cjs](../../scripts/test_browser_offline.cjs) | — | 8322 / 91 | `absent` | `b29e00b7c48504fa8c2dd8933467bbd3c6dceac3b964df478b38651848765264` |
| [scripts/test_browser_recording.cjs](../../scripts/test_browser_recording.cjs) | — | 1882 / 25 | `absent` | `f65395374188136325dcedbb7f8ea468210db563f67b220fbc4e60f145947b47` |
| [src/audio/onnx_diarization.py](../../src/audio/onnx_diarization.py) | — | 2474 / 46 | `absent` | `6aa3ec6e93101040171402470e7f19499c97140ac1a3107cb9d4be73673484dc` |
| [src/audio/parts.py](../../src/audio/parts.py) | — | 2540 / 51 | `absent` | `0fc6e8ee7da7a739da9625c00e769e437400782752ee8d49c78a6bfbcf68c015` |
| [src/fusion/lexical_alignment.py](../../src/fusion/lexical_alignment.py) | — | 1329 / 30 | `absent` | `0b9770f501b95c1cf59e6cf91ec9671406b609b967b19b7a369075fb8c56bfa3` |
| [src/meeting/language_rules.py](../../src/meeting/language_rules.py) | — | 1369 / 21 | `absent` | `a2647c012f771c54b1be76af264afdad95f71f93241f512250cb2da4c7526696` |
| src/meeting/local_notes.py (historical; removed in chapter 18) | — | 9277 / 182 | `absent` | `66a257c1ea9d0e53b8cc27c9b488ab31b38622a4f925c4e608dced558c0172f0` |
| [src/meeting/search.py](../../src/meeting/search.py) | — | 1251 / 29 | `absent` | `c4a05806f0a991aea8bd314bd66a27011fc6656c6d4a983229cb6ab000ff9a9f` |
| [src/report/transcript_export.py](../../src/report/transcript_export.py) | — | 2830 / 52 | `absent` | `dbcf9e37e27bfbe4adfcf927801903fbce4d6713bd01a3ed853d97dea7029b64` |
| [src/utils/text.py](../../src/utils/text.py) | — | 651 / 20 | `absent` | `7477249402d5095f74ac1945f472860290dc14e168cd4f93c4815a98321d78ed` |
| [tests/test_api.py](../../tests/test_api.py) | — | 4569 / 93 | `absent` | `86f02b4179d41dd8bf652d2864e72d30a2b511f3eb4b3ed4c4f697141e96732c` |
| [tests/test_efficiency.py](../../tests/test_efficiency.py) | — | 11968 / 192 | `absent` | `3644a65b2f45954f04152b757f8d4e8330b0aad689eadd6e1bd5eab8ac98eddb` |
| [tests/test_laptop_workflow.py](../../tests/test_laptop_workflow.py) | — | 6722 / 131 | `absent` | `2466ce98617b57f545f7a3bd5dafa2505748ce82c3fc8a0e0b78929b282fbabb` |
| tests/test_local_notes.py (historical; removed in chapter 18) | — | 9805 / 171 | `absent` | `68f17ed67555f69dae8d84723f8ea3148b1d270dbee759a37af3828b7c04e6ef` |
| [validation-results.json](../../outputs/evaluation/validation-results.json) | — | 2900 / 96 | `absent` | `4ad1c6bed600bb73f28c4d540facfb7b3a84bcfbae464904541c8b24269bd5fb` |

## Byte-identical files (49)

| File | Older bytes / lines | Current bytes / lines | Older SHA-256 | Current SHA-256 |
| --- | ---: | ---: | --- | --- |
| [AUDIO_ONLY_CONVERSION_GUIDE.md](../history/AUDIO_ONLY_CONVERSION_GUIDE.md) | 4001 / 81 | 4001 / 81 | `178aae462c06aa84f67d1b1efb7498a5e352b77120e305c3c4857ecfe7e01c28` | `178aae462c06aa84f67d1b1efb7498a5e352b77120e305c3c4857ecfe7e01c28` |
| [NEXT_STEPS.md](../history/NEXT_STEPS.md) | 2241 / 46 | 2241 / 46 | `c48697314b7eb285efb63a78fcb41a3c0c0581fe02a98a2cd0992dc02496fa02` | `c48697314b7eb285efb63a78fcb41a3c0c0581fe02a98a2cd0992dc02496fa02` |
| [PROJECT_EXECUTION_GUIDE.md](../history/PROJECT_EXECUTION_GUIDE.md) | 9155 / 282 | 9155 / 282 | `ff1162802f1d956157a4b51fe8ca2d6d86cfd6c2178fe9c38d9e796a0bb5cf69` | `ff1162802f1d956157a4b51fe8ca2d6d86cfd6c2178fe9c38d9e796a0bb5cf69` |
| [create_test_samples.py](../../scripts/create_test_samples.py) | 1461 / 45 | 1461 / 45 | `4df766e178fae96bc702a3881afabf7ae68158352ab5903fa84e7551d1333d74` | `4df766e178fae96bc702a3881afabf7ae68158352ab5903fa84e7551d1333d74` |
| [frontend/.gitignore](../../frontend/.gitignore) | 253 / 24 | 253 / 24 | `fe718e7babb14f3cbad2d97f08889b9ce5215ed3fe0e43b2b8cfbfb3b9b844e8` | `fe718e7babb14f3cbad2d97f08889b9ce5215ed3fe0e43b2b8cfbfb3b9b844e8` |
| [frontend/.oxlintrc.json](../../frontend/.oxlintrc.json) | 231 / 8 | 231 / 8 | `1be899e45c49b2a2edc715bc3bfb31d8ed8e866ed7ebab2065ff6e55e88c2396` | `1be899e45c49b2a2edc715bc3bfb31d8ed8e866ed7ebab2065ff6e55e88c2396` |
| [frontend/README.md](../../frontend/README.md) | 1009 / 16 | 1009 / 16 | `1f8fa46483b514305f44e34a47e85e88428c3a667c9494e1583628ef18d7bc79` | `1f8fa46483b514305f44e34a47e85e88428c3a667c9494e1583628ef18d7bc79` |
| [frontend/index.html](../../frontend/index.html) | 328 / 12 | 328 / 12 | `7a13aa49d3705cddc8801d4cb698134f599d831536dc91ba0c26701f54158bda` | `7a13aa49d3705cddc8801d4cb698134f599d831536dc91ba0c26701f54158bda` |
| [frontend/package-lock.json](../../frontend/package-lock.json) | 96894 / 2876 | 96894 / 2876 | `0bba032daef4c2894e81d3418a3bd403610f9c74a9ddd209c5b0462ff197ee91` | `0bba032daef4c2894e81d3418a3bd403610f9c74a9ddd209c5b0462ff197ee91` |
| [frontend/package.json](../../frontend/package.json) | 665 / 30 | 665 / 30 | `379a7f98493d3ef2dfc6a9a0bedf8c27cba9c33d38e138d72f0cef057ef0a13b` | `379a7f98493d3ef2dfc6a9a0bedf8c27cba9c33d38e138d72f0cef057ef0a13b` |
| [frontend/postcss.config.js](../../frontend/postcss.config.js) | 92 / 7 | 92 / 7 | `2b1257bcf4f22379b3b7060c633371e95fd1eb17a2b271ec40c8099eea1eb234` | `2b1257bcf4f22379b3b7060c633371e95fd1eb17a2b271ec40c8099eea1eb234` |
| [frontend/src/App.css](../../frontend/src/App.css) | 2891 / 184 | 2891 / 184 | `6e25a776d3e8102da5bacb3cb99f4a5fc662a2e01e6143140671a556d28c3d5c` | `6e25a776d3e8102da5bacb3cb99f4a5fc662a2e01e6143140671a556d28c3d5c` |
| [frontend/src/main.jsx](../../frontend/src/main.jsx) | 229 / 10 | 229 / 10 | `4b4b864dbe45253425d0c925337180ec07e204295179f80f59551216f466f618` | `4b4b864dbe45253425d0c925337180ec07e204295179f80f59551216f466f618` |
| [frontend/tailwind.config.js](../../frontend/tailwind.config.js) | 182 / 11 | 182 / 11 | `2248bf828c19499e4a34a9d6696bc862cd53989239b7b4a61a76eef20bfacb79` | `2248bf828c19499e4a34a9d6696bc862cd53989239b7b4a61a76eef20bfacb79` |
| [notebooks/README.md](../development/NOTEBOOKS.md) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [run_resume_pipeline.sh](../../archive/legacy_tools/run_resume_pipeline.sh) | 2192 / 79 | 2192 / 79 | `f1d5775f117fe083bb1168dd8ea12549fff7368562975192f9a3c0e42b2b3797` | `f1d5775f117fe083bb1168dd8ea12549fff7368562975192f9a3c0e42b2b3797` |
| [run_single_test.sh](../../archive/legacy_tools/run_single_test.sh) | 471 / 25 | 471 / 25 | `172523af72c82d1ebc090f2e646ca2051bba4b38e0a83c6b97354051871442be` | `172523af72c82d1ebc090f2e646ca2051bba4b38e0a83c6b97354051871442be` |
| [run_small_chunk.py](../../archive/legacy_tools/run_small_chunk.py) | 2765 / 92 | 2765 / 92 | `9d9c8b07d03868f77774cc5adb567ffdab29a50a14b8cbba283d762c6949d74f` | `9d9c8b07d03868f77774cc5adb567ffdab29a50a14b8cbba283d762c6949d74f` |
| [scripts/generate_dummy_ppt.py](../../scripts/generate_dummy_ppt.py) | 779 / 22 | 779 / 22 | `8fe87719330faeb184b708e93ec2c8c5aefb707accd21626706feb3c867eab8c` | `8fe87719330faeb184b708e93ec2c8c5aefb707accd21626706feb3c867eab8c` |
| [scripts/generate_report.py](../../scripts/generate_report.py) | 3193 / 86 | 3193 / 86 | `c1307b2ea252189aa80f37629cad194c076b42ee2e6d2d2b6b08675f35ce9b34` | `c1307b2ea252189aa80f37629cad194c076b42ee2e6d2d2b6b08675f35ce9b34` |
| [scripts/generate_test_audio.py](../../scripts/generate_test_audio.py) | 1117 / 40 | 1117 / 40 | `2570b2ca87d77f5286711f5c6036dd2f02a1f73bbede1e6aac2e05051e502ebc` | `2570b2ca87d77f5286711f5c6036dd2f02a1f73bbede1e6aac2e05051e502ebc` |
| [scripts/generate_test_meeting.py](../../scripts/generate_test_meeting.py) | 2952 / 74 | 2952 / 74 | `14047db1abdfa38e9c3de22a63521a5ad9f6a2d85956e8598ded9e924a9e6d3d` | `14047db1abdfa38e9c3de22a63521a5ad9f6a2d85956e8598ded9e924a9e6d3d` |
| [scripts/prepare_batch_data.py](../../scripts/prepare_batch_data.py) | 1747 / 47 | 1747 / 47 | `03193634a054c020b5ca6df47356b7140085c0d2d3050cad5bd98cacf857cd0c` | `03193634a054c020b5ca6df47356b7140085c0d2d3050cad5bd98cacf857cd0c` |
| [scripts/run_evaluation.py](../../scripts/run_evaluation.py) | 13592 / 346 | 13592 / 346 | `5c89dedd86a6efaca1fd79b7c4e71239259388cfd40d601bc4bb08cb5415f30f` | `5c89dedd86a6efaca1fd79b7c4e71239259388cfd40d601bc4bb08cb5415f30f` |
| [src/__init__.py](../../src/__init__.py) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [src/audio/__init__.py](../../src/audio/__init__.py) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [src/evaluation/__init__.py](../../src/evaluation/__init__.py) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [src/evaluation/ablation.py](../../src/evaluation/ablation.py) | 7704 / 232 | 7704 / 232 | `09b4e48873413574a6ea0334811cc60a69405efbab24dd212e4f2285713e1e68` | `09b4e48873413574a6ea0334811cc60a69405efbab24dd212e4f2285713e1e68` |
| [src/evaluation/baselines.py](../../src/evaluation/baselines.py) | 13123 / 354 | 13123 / 354 | `2c740172aa08c12e6fe741448e0c77bcebe082eb436b04867cb2a30b09c5253b` | `2c740172aa08c12e6fe741448e0c77bcebe082eb436b04867cb2a30b09c5253b` |
| [src/fusion/__init__.py](../../src/fusion/__init__.py) | 1233 / 42 | 1233 / 42 | `51f6647d0df57c1a457cee39df688e26a03de402a4da3d4200dd936ac3cb44d6` | `51f6647d0df57c1a457cee39df688e26a03de402a4da3d4200dd936ac3cb44d6` |
| [src/fusion/semantic_alignment.py](../../src/fusion/semantic_alignment.py) | 5422 / 163 | 5422 / 163 | `6e0d641a3f5f4ce9b0ef0bef4ce2250e78b6a1ae609c7496236b87fedf5c6a82` | `6e0d641a3f5f4ce9b0ef0bef4ce2250e78b6a1ae609c7496236b87fedf5c6a82` |
| [src/fusion/temporal_alignment.py](../../src/fusion/temporal_alignment.py) | 5174 / 164 | 5174 / 164 | `1466230ac269f2c7d04e912e6f2f8070bafb768d6ffc48d22982807ab2ef2baa` | `1466230ac269f2c7d04e912e6f2f8070bafb768d6ffc48d22982807ab2ef2baa` |
| [src/meeting/__init__.py](../../src/meeting/__init__.py) | 1644 / 53 | 1644 / 53 | `0a8df76d9cd9815289f7c80dd2bf3ccd035f45579122a6bb8902467dab6b81c1` | `0a8df76d9cd9815289f7c80dd2bf3ccd035f45579122a6bb8902467dab6b81c1` |
| [src/meeting/evidence.py](../../src/meeting/evidence.py) | 12532 / 357 | 12532 / 357 | `1e5a4461fc6c6531bc8dc70212e9d51fe8a3c0bcc2fa0ae307dbdfb70b9111d0` | `1e5a4461fc6c6531bc8dc70212e9d51fe8a3c0bcc2fa0ae307dbdfb70b9111d0` |
| [src/pipeline/__init__.py](../../src/pipeline/__init__.py) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [src/ppt/__init__.py](../../src/ppt/__init__.py) | 634 / 29 | 634 / 29 | `64b4409eb14c99d51c4647ba239a7b1bfcf8507594d0401c3bd70b146236e0f0` | `64b4409eb14c99d51c4647ba239a7b1bfcf8507594d0401c3bd70b146236e0f0` |
| [src/ppt/embeddings.py](../../src/ppt/embeddings.py) | 4445 / 144 | 4445 / 144 | `80c605dee5f09f78613badf473631c58108c65ac7faaad2780c18b9e2c76e849` | `80c605dee5f09f78613badf473631c58108c65ac7faaad2780c18b9e2c76e849` |
| [src/ppt/extract.py](../../src/ppt/extract.py) | 11211 / 324 | 11211 / 324 | `1018fd55960bf78c480add9b54e2c6521b84ca2694444639f11ebdccc6d4f270` | `1018fd55960bf78c480add9b54e2c6521b84ca2694444639f11ebdccc6d4f270` |
| [src/ppt/features.py](../../src/ppt/features.py) | 3259 / 94 | 3259 / 94 | `a023ec87011f199141aa8511803110571ee0a34cc5a080599760ea34753efe2e` | `a023ec87011f199141aa8511803110571ee0a34cc5a080599760ea34753efe2e` |
| [src/ppt/io.py](../../src/ppt/io.py) | 2600 / 83 | 2600 / 83 | `bb9938441495fdd433db6aab08aaefc68ccf4211b13528e1d269e551c054700e` | `bb9938441495fdd433db6aab08aaefc68ccf4211b13528e1d269e551c054700e` |
| [src/ppt/ocr.py](../../src/ppt/ocr.py) | 4427 / 137 | 4427 / 137 | `c55e5fbaaa4a3d223dcd4498c280e74ca4b0bdbee8b2803f446d053be4f4a89b` | `c55e5fbaaa4a3d223dcd4498c280e74ca4b0bdbee8b2803f446d053be4f4a89b` |
| [src/report/__init__.py](../../src/report/__init__.py) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [src/utils/__init__.py](../../src/utils/__init__.py) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [src/utils/logging.py](../../src/utils/logging.py) | 649 / 23 | 649 / 23 | `3e40c8672e63d043e79c39a87302a6fd6c4fd8a2a877ef121b687a08ae2c780a` | `3e40c8672e63d043e79c39a87302a6fd6c4fd8a2a877ef121b687a08ae2c780a` |
| [src/utils/paths.py](../../src/utils/paths.py) | 615 / 22 | 615 / 22 | `9f3d13f84a61089b038820239711fc78197590f9c7010f728a382d880ecca67b` | `9f3d13f84a61089b038820239711fc78197590f9c7010f728a382d880ecca67b` |
| [tests/__init__.py](../../tests/__init__.py) | 0 / 0 | 0 / 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| [tests/test_meeting.py](../../tests/test_meeting.py) | 84730 / 2045 | 84730 / 2045 | `c5a6ceb3a21534fcda359876121d1de4159c0326638697744c91516ad38627ec` | `c5a6ceb3a21534fcda359876121d1de4159c0326638697744c91516ad38627ec` |
| [tests/test_ppt.py](../../tests/test_ppt.py) | 12760 / 360 | 12760 / 360 | `6070995ada6134ece5f421461bafa310e565d1ec7d18eeec04daaa4abb4aa5bb` | `6070995ada6134ece5f421461bafa310e565d1ec7d18eeec04daaa4abb4aa5bb` |
| [tests/test_report.py](../../tests/test_report.py) | 28632 / 705 | 28632 / 705 | `eb11cc1ca8bf346fd2128dbeabf7fa0920092dc0ebf3fa3d909cbcf12ed76d99` | `eb11cc1ca8bf346fd2128dbeabf7fa0920092dc0ebf3fa3d909cbcf12ed76d99` |

## Older-only files (0)

None in the scoped first-party inventory.

## Non-source artifacts compared separately

`outputs/reports/`: 645 current / 561 older / 561 shared identical / 84 current-only. `outputs/evaluation/`: 8 current / 2 older JSONs, both shared identical. Databases were retained but account/private contents were not audited or reproduced. The absent old data/venv/model payload prevents complete workstation equivalence certification.

The manifest is a snapshot. Regenerate a release manifest after source changes; do not assume these hashes describe future code.

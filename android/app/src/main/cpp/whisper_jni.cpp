#include <jni.h>
#include <string>
#include <sstream>
#include <vector>
#include <algorithm>
#include <unistd.h>
#include "whisper.h"

static std::string quote(const char *value) {
    std::string out = "\"";
    for (const unsigned char *p = (const unsigned char *)value; *p; ++p) {
        if (*p == '"' || *p == '\\') { out += '\\'; out += *p; }
        else if (*p < 32) { char escaped[7]; snprintf(escaped, sizeof(escaped), "\\u%04x", *p); out += escaped; }
        else out += *p;
    }
    return out + '"';
}
static void fail(JNIEnv *env, const char *message) {
    env->ThrowNew(env->FindClass("java/lang/IllegalStateException"), message);
}
extern "C" JNIEXPORT jlong JNICALL Java_org_meetiq_offline_NativeWhisper_open(JNIEnv *env, jclass, jstring path) {
    const char *model = env->GetStringUTFChars(path, nullptr);
    auto params = whisper_context_default_params();
    params.use_gpu = false;
    auto *ctx = whisper_init_from_file_with_params(model, params);
    env->ReleaseStringUTFChars(path, model);
    if (!ctx) fail(env, "Invalid or unsupported Whisper model. Import a multilingual GGML model.");
    return reinterpret_cast<jlong>(ctx);
}
extern "C" JNIEXPORT jbyteArray JNICALL Java_org_meetiq_offline_NativeWhisper_transcribe(JNIEnv *env, jclass, jlong handle, jfloatArray audio, jstring language, jstring vocabulary) {
    auto *ctx = reinterpret_cast<whisper_context *>(handle);
    if (!ctx) { fail(env, "Speech model is not loaded"); return nullptr; }
    const int size = env->GetArrayLength(audio);
    float *samples = env->GetFloatArrayElements(audio, nullptr);
    bool silent = true;
    for (int i = 0; i < size; ++i) if (samples[i] != 0.0f) { silent = false; break; }
    if (silent) {
        env->ReleaseFloatArrayElements(audio, samples, JNI_ABORT);
        jbyteArray empty = env->NewByteArray(2);
        env->SetByteArrayRegion(empty, 0, 2, reinterpret_cast<const jbyte *>("[]"));
        return empty;
    }
    auto params = whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
    params.n_threads = std::max(1, std::min(4, static_cast<int>(sysconf(_SC_NPROCESSORS_ONLN))));
    // The requested product scope is Hindi/English; unconstrained detection
    // can choose an unrelated language from noisy room audio.
    const char *requested = env->GetStringUTFChars(language, nullptr);
    std::string selected(requested);
    env->ReleaseStringUTFChars(language, requested);
    const char *hint = env->GetStringUTFChars(vocabulary, nullptr);
    std::string prompt(hint);
    env->ReleaseStringUTFChars(vocabulary, hint);
    if (selected == "auto") {
        std::vector<float> probabilities(whisper_lang_max_id() + 1, 0.0f);
        if (whisper_pcm_to_mel(ctx, samples, size, params.n_threads) != 0 ||
            whisper_lang_auto_detect(ctx, 0, params.n_threads, probabilities.data()) < 0) {
            env->ReleaseFloatArrayElements(audio, samples, JNI_ABORT);
            fail(env, "Language detection failed"); return nullptr;
        }
        selected = probabilities[whisper_lang_id("hi")] > probabilities[whisper_lang_id("en")] ? "hi" : "en";
    }
    if (selected != "en" && !whisper_is_multilingual(ctx)) {
        env->ReleaseFloatArrayElements(audio, samples, JNI_ABORT);
        fail(env, "Import a multilingual model for Hindi meetings"); return nullptr;
    }
    params.language = selected.c_str();
    params.initial_prompt = prompt.empty() ? nullptr : prompt.c_str();
    params.translate = false;
    params.no_context = true;
    params.print_progress = params.print_realtime = params.print_timestamps = params.print_special = false;
    params.suppress_nst = true;
    const int result = whisper_full(ctx, params, samples, size);
    env->ReleaseFloatArrayElements(audio, samples, JNI_ABORT);
    if (result != 0) { fail(env, "Local transcription failed"); return nullptr; }
    std::ostringstream json;
    json << '[';
    const int count = whisper_full_n_segments(ctx);
    for (int i = 0; i < count; ++i) {
        if (i) json << ',';
        json << "{\"start\":" << whisper_full_get_segment_t0(ctx, i) / 100.0
             << ",\"end\":" << whisper_full_get_segment_t1(ctx, i) / 100.0
             << ",\"text\":" << quote(whisper_full_get_segment_text(ctx, i)) << '}';
    }
    json << ']';
    std::string output = json.str();
    jbyteArray bytes = env->NewByteArray(output.size());
    env->SetByteArrayRegion(bytes, 0, output.size(), reinterpret_cast<const jbyte *>(output.data()));
    return bytes;
}
extern "C" JNIEXPORT void JNICALL Java_org_meetiq_offline_NativeWhisper_close(JNIEnv *, jclass, jlong handle) {
    if (handle) whisper_free(reinterpret_cast<whisper_context *>(handle));
}

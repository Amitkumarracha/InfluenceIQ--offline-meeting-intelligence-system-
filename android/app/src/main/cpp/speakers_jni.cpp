#include <jni.h>
#include <fstream>
#include <sstream>
#include <vector>
#include <memory>
#include <algorithm>
#include <exception>
#include "c-api.h"

static void fail(JNIEnv *env,const char *message) {
    env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),message);
}
static std::string path(JNIEnv *env,jstring value) {
    const char *bytes=env->GetStringUTFChars(value,nullptr);
    std::string result(bytes); env->ReleaseStringUTFChars(value,bytes); return result;
}
struct Progress { JNIEnv *env; jclass type; jmethodID callback; };
static int32_t progress(int32_t done,int32_t total,void *argument) {
    auto *p=static_cast<Progress *>(argument);
    p->env->CallStaticVoidMethod(p->type,p->callback,done,total);
    return 0;
}
extern "C" JNIEXPORT jbyteArray JNICALL Java_org_meetiq_offline_NativeSpeakers_diarize(
    JNIEnv *env,jclass type,jstring audio,jstring segmentation,jstring embedding,jint speakers) {
    try {
    std::string seg=path(env,segmentation),emb=path(env,embedding);
    std::ifstream wav(path(env,audio),std::ios::binary|std::ios::ate);
    auto length=wav.tellg();
    // Native PCM buffer avoids duplicate large Java arrays. All inputs have
    // the application's canonical 44-byte PCM16 WAV header.
    if(!wav || length<=44 || length>44+32000LL*3600) { fail(env,"Speaker analysis supports recordings up to one hour on this device"); return nullptr; }
    size_t count=(static_cast<long long>(length)-44)/2;
    std::vector<float> samples(count); wav.seekg(44);
    unsigned char block[65536]; size_t offset=0;
    while(offset<count) {
        size_t n=std::min(count-offset,sizeof(block)/2); wav.read(reinterpret_cast<char *>(block),n*2);
        if(!wav) { fail(env,"Cannot read saved PCM audio"); return nullptr; }
        for(size_t i=0;i<n;++i) samples[offset+i]=static_cast<int16_t>(block[2*i]|(block[2*i+1]<<8))/32768.0f;
        offset+=n;
    }
    SherpaOnnxOfflineSpeakerDiarizationConfig config{};
    config.segmentation.pyannote.model=seg.c_str(); config.segmentation.num_threads=2; config.segmentation.provider="cpu";
    config.embedding.model=emb.c_str(); config.embedding.num_threads=2; config.embedding.provider="cpu";
    config.clustering.num_clusters=speakers>0?speakers:-1; config.clustering.threshold=.5;
    config.min_duration_on=.3; config.min_duration_off=.5;
    auto destroy=SherpaOnnxDestroyOfflineSpeakerDiarization;
    std::unique_ptr<const SherpaOnnxOfflineSpeakerDiarization,decltype(destroy)> engine(SherpaOnnxCreateOfflineSpeakerDiarization(&config),destroy);
    if(!engine) { fail(env,"Cannot load local speaker models"); return nullptr; }
    Progress p{env,type,env->GetStaticMethodID(type,"progress","(II)V")};
    auto release=SherpaOnnxOfflineSpeakerDiarizationDestroyResult;
    std::unique_ptr<const SherpaOnnxOfflineSpeakerDiarizationResult,decltype(release)> result(
        SherpaOnnxOfflineSpeakerDiarizationProcessWithCallback(engine.get(),samples.data(),count,progress,&p),release);
    if(!result) { fail(env,"Local speaker analysis failed"); return nullptr; }
    int n=SherpaOnnxOfflineSpeakerDiarizationResultGetNumSegments(result.get());
    auto freeSegments=SherpaOnnxOfflineSpeakerDiarizationDestroySegment;
    std::unique_ptr<const SherpaOnnxOfflineSpeakerDiarizationSegment,decltype(freeSegments)> turns(
        SherpaOnnxOfflineSpeakerDiarizationResultSortByStartTime(result.get()),freeSegments);
    std::ostringstream json; json<<'[';
    for(int i=0;i<n;++i) { if(i) json<<','; json<<"{\"start\":"<<turns.get()[i].start<<",\"end\":"<<turns.get()[i].end<<",\"cluster\":"<<turns.get()[i].speaker<<'}'; }
    json<<']'; std::string bytes=json.str(); jbyteArray output=env->NewByteArray(bytes.size());
    env->SetByteArrayRegion(output,0,bytes.size(),reinterpret_cast<const jbyte *>(bytes.data())); return output;
    } catch(const std::exception &error) {
        fail(env,error.what()); return nullptr;
    }
}

package org.meetiq.offline;

/** Reserve most available system memory for ONNX, application state and Android. */
final class SpeakerBudget {
    static final long MAX_PCM_BYTES=512L*1024*1024;
    static long seconds(long availableBytes,boolean lowMemory) {
        return lowMemory?0:Math.min(MAX_PCM_BYTES,Math.max(0,availableBytes)/4)/(16000*4);
    }
}

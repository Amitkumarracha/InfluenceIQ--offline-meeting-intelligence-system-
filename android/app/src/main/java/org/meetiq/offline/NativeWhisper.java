package org.meetiq.offline;

import java.nio.charset.StandardCharsets;

final class NativeWhisper {
    static { System.loadLibrary("meetiq"); }
    static native long open(String modelPath);
    static native byte[] transcribe(long context, float[] audio);
    static native void close(long context);
    static String run(long context, float[] audio) {
        return new String(transcribe(context, audio), StandardCharsets.UTF_8);
    }
}

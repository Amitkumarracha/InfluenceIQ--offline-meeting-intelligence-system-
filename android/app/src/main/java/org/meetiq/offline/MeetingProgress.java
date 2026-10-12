package org.meetiq.offline;

/** Immutable UI snapshot; it does not change stored transcripts/checkpoints. */
public final class MeetingProgress {
    public final String operation, meetingId, stage, error;
    public final long completedSeconds, totalSeconds;
    public final float microphoneLevel;

    public MeetingProgress(String operation, String meetingId, String stage, long completed, long total, float level, String error) {
        this.operation = operation; this.meetingId = meetingId; this.stage = stage;
        completedSeconds = Math.max(0, completed); totalSeconds = Math.max(0, total);
        microphoneLevel = Math.max(0, Math.min(1, level)); this.error = error;
    }
    public int percent() { return totalSeconds == 0 ? 0 : (int)Math.min(100, completedSeconds * 100 / totalSeconds); }
    public boolean recording() { return operation.equals("record"); }
    public static float amplitude(byte[] pcm, int count) {
        if (count <= 0 || count % 2 != 0 || count > pcm.length) return 0;
        long squares = 0;
        for (int i=0; i<count; i+=2) {
            int sample = (short)((pcm[i] & 255) | (pcm[i+1] << 8));
            squares += (long)sample * sample;
        }
        return (float)(Math.sqrt(squares / (count / 2.0)) / 32768.0);
    }
}

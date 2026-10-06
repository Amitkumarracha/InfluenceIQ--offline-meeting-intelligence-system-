package org.meetiq.offline;

import android.app.*;
import android.content.*;
import android.content.pm.ServiceInfo;
import android.media.*;
import android.os.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.*;

public class MeetingService extends Service {
    static volatile String status = "Ready. Audio and reports stay on this phone.";
    static volatile boolean busy = false;
    private volatile boolean stopping = false;
    private PowerManager.WakeLock wakeLock;
    private Thread worker;
    private EventRules eventRules;
    private JSONArray eventCandidates = new JSONArray();
    private int analysedSegments = 0;

    public IBinder onBind(Intent intent) { return null; }
    public void onCreate() {
        super.onCreate();
        getSystemService(NotificationManager.class).createNotificationChannel(
            new NotificationChannel("meeting", "Meeting recording and analysis", NotificationManager.IMPORTANCE_LOW));
    }
    public int onStartCommand(Intent intent, int flags, int id) {
        if (intent == null) { stopSelf(); return START_NOT_STICKY; }
        if ("stop".equals(intent.getAction())) { stopping = true; return START_NOT_STICKY; }
        if (busy) return START_NOT_STICKY;
        final boolean record = "record".equals(intent.getAction());
        busy = true; stopping = false;
        Intent stop = new Intent(this, MeetingService.class).setAction("stop");
        PendingIntent stopIntent = PendingIntent.getService(this, 1, stop, PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(this, "meeting")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle("Meet IQ Offline")
            .setContentText(record ? "Recording meeting — tap Stop when finished" : "Analysing locally")
            .setOngoing(true).addAction(new Notification.Action.Builder(null, "Stop", stopIntent).build()).build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(1, notification,
            record ? ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE : ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
        else startForeground(1, notification);
        wakeLock = getSystemService(PowerManager.class).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "meetiq:meeting");
        wakeLock.acquire(6 * 60 * 60 * 1000L);
        final String meeting = intent.getStringExtra("meeting");
        final String language = intent.getStringExtra("language");
        final String vocabulary = intent.getStringExtra("vocabulary");
        worker = new Thread(() -> {
            try {
                if (record) recordMeeting(); else analyse(meeting, language, vocabulary);
            } catch (Exception | LinkageError error) {
                status = "Stopped: " + error.getMessage() + ". Saved audio and completed chunks are retained.";
            } finally {
                busy = false;
                if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
                stopForeground(STOP_FOREGROUND_REMOVE);
                stopSelf();
            }
        }, "local-meeting");
        worker.start();
        return START_NOT_STICKY;
    }
    public void onDestroy() { stopping = true; super.onDestroy(); }

    private void recordMeeting() throws Exception {
        File directory = new File(getFilesDir(), "meetings/" + System.currentTimeMillis());
        if (!directory.mkdirs()) throw new IOException("Cannot create meeting folder");
        int minimum = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT);
        if (minimum <= 0) throw new IOException("16 kHz microphone capture unsupported");
        AudioRecord recorder = new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, 16000,
            AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, Math.max(minimum * 2, 32000));
        try (RandomAccessFile output = new RandomAccessFile(new File(directory, "audio.wav"), "rw")) {
            WavAudio.writeHeader(output, 0);
            if (recorder.getState() != AudioRecord.STATE_INITIALIZED) throw new IOException("Microphone could not initialize");
            recorder.startRecording();
            byte[] buffer = new byte[32000];
            long bytes = 0;
            while (!stopping && bytes < 32000L * 6 * 60 * 60) {
                int count = recorder.read(buffer, 0, buffer.length);
                if (count < 0) throw new IOException("Microphone interrupted: " + count);
                if (count == 0) continue;
                if (count % 2 != 0) throw new IOException("Incomplete microphone sample");
                if (directory.getUsableSpace() < count + 1024 * 1024) throw new IOException("Phone storage is full");
                output.write(buffer, 0, count); bytes += count;
                WavAudio.writeHeader(output, bytes); // Update WAV length; recoverable after process death.
                output.getFD().sync();
                status = "Recording " + (bytes / 32000) + " seconds. Keep the phone close to the speakers.";
            }
            status = "Recording saved. Select the meeting and tap Analyse.";
        } finally {
            try { recorder.stop(); } catch (IllegalStateException ignored) { }
            recorder.release();
        }
    }

    private void analyse(String meeting, String requestedLanguage, String requestedVocabulary) throws Exception {
        analysedSegments = 0; eventCandidates = new JSONArray();
        if (meeting == null || !meeting.matches("[0-9]+")) throw new IOException("Select a meeting");
        File directory = new File(getFilesDir(), "meetings/" + meeting);
        File audio = new File(directory, "audio.wav");
        File model = new File(getFilesDir(), "model.bin");
        if (!model.isFile()) throw new IOException("Import a multilingual GGML model first");
        String language = requestedLanguage == null ? "auto" : requestedLanguage;
        if (!Arrays.asList("auto", "en", "hi").contains(language)) throw new IOException("Invalid language");
        String vocabulary = requestedVocabulary == null ? "" : requestedVocabulary.trim();
        if (vocabulary.length() > 1000) throw new IOException("Vocabulary must be under 1000 characters");
        String identity = "v3:" + sha256(model) + ":" + sha256(audio) + ":" + language + ":" + vocabulary;
        File checkpoint = new File(directory, "checkpoint.json");
        JSONObject saved = checkpoint.exists() ? new JSONObject(new String(Files.readAllBytes(checkpoint.toPath()), StandardCharsets.UTF_8)) : new JSONObject();
        JSONArray segments = identity.equals(saved.optString("identity")) ? saved.getJSONArray("segments") : new JSONArray();
        int completed = identity.equals(saved.optString("identity")) ? saved.optInt("completed") : 0;
        long samples = Math.max(0, (audio.length() - 44) / 2);
        if (samples == 0) throw new IOException("Recording contains no audio");
        int chunk = 120 * 16000;
        saveReport(directory, segments, samples / 16000.0, completed * (long)chunk >= samples, language);
        if (completed * (long)chunk >= samples) { status = "Completed transcript recovered from saved chunks."; return; }
        status = "Loading local speech model…";
        long context = 0;
        try (RandomAccessFile input = new RandomAccessFile(audio, "r")) {
            for (long start = (long)completed * chunk; start < samples && !stopping; start += chunk) {
                long offset = Math.max(0, start - 2 * 16000);
                int count = (int)(Math.min(samples, start + chunk + 2 * 16000) - offset);
                byte[] pcm = new byte[count * 2];
                input.seek(44 + offset * 2); input.readFully(pcm);
                float[] values = new float[count];
                boolean digitalSilence = true;
                for (int i=0; i<count; i++) {
                    values[i] = (short)((pcm[i*2] & 255) | (pcm[i*2+1] << 8)) / 32768f;
                    if (values[i] != 0) digitalSilence = false;
                }
                status = "Transcribing " + (start / 16000) + " / " + (samples / 16000) + " seconds locally…";
                JSONArray found = new JSONArray();
                if (!digitalSilence) {
                    if (context == 0) context = NativeWhisper.open(model.getAbsolutePath());
                    found = new JSONArray(NativeWhisper.run(context, values, language, vocabulary));
                }
                for (int i=0; i<found.length(); i++) {
                    JSONObject item = found.getJSONObject(i);
                    String text = item.getString("text").trim();
                    double a = Math.max(0, item.getDouble("start") + offset / 16000.0);
                    double b = Math.min(samples / 16000.0, item.getDouble("end") + offset / 16000.0);
                    double midpoint = (a + b) / 2;
                    if (midpoint < start / 16000.0 || midpoint >= Math.min(samples, start + chunk) / 16000.0) continue;
                    if (text.isEmpty() || b <= a) continue;
                    item.put("start", a).put("end", b).put("text", text)
                        .put("speaker", "UNKNOWN").put("segment_id", segments.length() + 1);
                    segments.put(item);
                }
                completed++;
                atomic(checkpoint, new JSONObject().put("identity", identity).put("completed", completed).put("segments", segments));
                saveReport(directory, segments, samples / 16000.0, false, language);
            }
            saveReport(directory, segments, samples / 16000.0, completed * (long)chunk >= samples, language);
            status = stopping ? "Analysis paused. Tap Analyse to resume." : "Report saved. Review transcript and event candidates before using them.";
        } finally { NativeWhisper.close(context); }
    }

    private void saveReport(File directory, JSONArray segments, double duration, boolean complete, String language) throws Exception {
        JSONObject report = new JSONObject().put("transcript_segments", segments)
            .put("duration", duration).put("completed", complete).put("language", language)
            .put("analysis_method", "Keyword candidates; verify against source audio. Speaker separation unavailable.")
            .put("events", events(segments)).put("accuracy_measured", false);
        atomic(new File(directory, "report.json"), report);
    }

    private Map<String,List<String>> ruleAsset(String file) throws Exception {
        String raw;
        try (InputStream stream = getAssets().open(file)) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream(); byte[] block = new byte[8192]; int count;
            while ((count = stream.read(block)) != -1) bytes.write(block, 0, count);
            raw = new String(bytes.toByteArray(), StandardCharsets.UTF_8);
        }
        JSONObject bank = new JSONObject(raw);
        Map<String,List<String>> result = new LinkedHashMap<>();
        for (Iterator<String> keys=bank.keys(); keys.hasNext();) {
            String type = keys.next(); JSONArray items = bank.getJSONArray(type); List<String> patterns = new ArrayList<>();
            for (int i=0; i<items.length(); i++) patterns.add(items.getString(i));
            result.put(type, patterns);
        }
        return result;
    }

    private JSONArray events(JSONArray segments) throws Exception {
        if (eventRules == null) eventRules = new EventRules(ruleAsset("event_patterns.json"), ruleAsset("event_blockers.json"));
        if (segments.length() < analysedSegments) { analysedSegments = 0; eventCandidates = new JSONArray(); }
        // Completed transcript parts are immutable within an analysis run.
        // Compile once and analyse only new passages, rather than rescanning all history.
        for (int i=analysedSegments; i<segments.length(); i++) {
            JSONObject seg = segments.getJSONObject(i); String text = seg.getString("text");
            for (String type : eventRules.eventTypes(text)) {
                eventCandidates.put(new JSONObject().put("event_type", type).put("text", text)
                    .put("start", seg.getDouble("start")).put("end", seg.getDouble("end"))
                    .put("source_segment_id", seg.getInt("segment_id")).put("requires_review", true));
            }
        }
        analysedSegments = segments.length();
        return eventCandidates;
    }
    private static String sha256(File file) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = new FileInputStream(file)) {
            byte[] block = new byte[1024 * 1024]; int count;
            while ((count = input.read(block)) != -1) digest.update(block, 0, count);
        }
        StringBuilder result = new StringBuilder();
        for (byte value : digest.digest()) result.append(String.format("%02x", value));
        return result.toString();
    }

    static void atomic(File destination, JSONObject value) throws Exception {
        File temp = new File(destination.getParentFile(), destination.getName() + ".tmp");
        try (FileOutputStream output = new FileOutputStream(temp)) {
            output.write(value.toString(2).getBytes(StandardCharsets.UTF_8)); output.getFD().sync();
        }
        if (!temp.renameTo(destination)) throw new IOException("Cannot save meeting checkpoint");
    }
}

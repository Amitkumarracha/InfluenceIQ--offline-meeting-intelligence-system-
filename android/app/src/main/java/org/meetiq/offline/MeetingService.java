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
import java.util.regex.Pattern;

public class MeetingService extends Service {
    static volatile String status = "Ready. Audio and reports stay on this phone.";
    static volatile boolean busy = false;
    private volatile boolean stopping = false;
    private PowerManager.WakeLock wakeLock;
    private Thread worker;

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
        worker = new Thread(() -> {
            try {
                if (record) recordMeeting(); else analyse(meeting);
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
            header(output, 0);
            if (recorder.getState() != AudioRecord.STATE_INITIALIZED) throw new IOException("Microphone could not initialize");
            recorder.startRecording();
            byte[] buffer = new byte[32000];
            long bytes = 0;
            while (!stopping && bytes < 32000L * 6 * 60 * 60) {
                int count = recorder.read(buffer, 0, buffer.length);
                if (count < 0) throw new IOException("Microphone interrupted: " + count);
                if (count == 0) continue;
                output.write(buffer, 0, count); bytes += count;
                header(output, bytes); // Update WAV length; recoverable after process death.
                output.getFD().sync();
                status = "Recording " + (bytes / 32000) + " seconds. Keep the phone close to the speakers.";
            }
            status = "Recording saved. Select the meeting and tap Analyse.";
        } finally {
            try { recorder.stop(); } catch (IllegalStateException ignored) { }
            recorder.release();
        }
    }

    static void header(RandomAccessFile output, long bytes) throws IOException {
        output.seek(0);
        output.writeBytes("RIFF"); output.writeInt(Integer.reverseBytes((int)(bytes + 36)));
        output.writeBytes("WAVEfmt "); output.writeInt(Integer.reverseBytes(16));
        output.writeShort(Short.reverseBytes((short)1)); output.writeShort(Short.reverseBytes((short)1));
        output.writeInt(Integer.reverseBytes(16000)); output.writeInt(Integer.reverseBytes(32000));
        output.writeShort(Short.reverseBytes((short)2)); output.writeShort(Short.reverseBytes((short)16));
        output.writeBytes("data"); output.writeInt(Integer.reverseBytes((int)bytes));
        output.seek(bytes + 44);
    }

    private void analyse(String meeting) throws Exception {
        if (meeting == null || !meeting.matches("[0-9]+")) throw new IOException("Select a meeting");
        File directory = new File(getFilesDir(), "meetings/" + meeting);
        File audio = new File(directory, "audio.wav");
        File model = new File(getFilesDir(), "model.bin");
        if (!model.isFile()) throw new IOException("Import a multilingual GGML model first");
        String identity = "v2:" + sha256(model) + ":" + sha256(audio);
        File checkpoint = new File(directory, "checkpoint.json");
        JSONObject saved = checkpoint.exists() ? new JSONObject(new String(Files.readAllBytes(checkpoint.toPath()), StandardCharsets.UTF_8)) : new JSONObject();
        JSONArray segments = identity.equals(saved.optString("identity")) ? saved.getJSONArray("segments") : new JSONArray();
        int completed = identity.equals(saved.optString("identity")) ? saved.optInt("completed") : 0;
        status = "Loading local speech model…";
        long context = NativeWhisper.open(model.getAbsolutePath());
        try (RandomAccessFile input = new RandomAccessFile(audio, "r")) {
            long samples = Math.max(0, (input.length() - 44) / 2);
            if (samples == 0) throw new IOException("Recording contains no audio");
            int chunk = 120 * 16000;
            for (long start = (long)completed * chunk; start < samples && !stopping; start += chunk) {
                int count = (int)Math.min(chunk, samples - start);
                byte[] pcm = new byte[count * 2];
                input.seek(44 + start * 2); input.readFully(pcm);
                float[] values = new float[count];
                for (int i=0; i<count; i++) values[i] = (short)((pcm[i*2] & 255) | (pcm[i*2+1] << 8)) / 32768f;
                status = "Transcribing " + (start / 16000) + " / " + (samples / 16000) + " seconds locally…";
                JSONArray found = new JSONArray(NativeWhisper.run(context, values));
                for (int i=0; i<found.length(); i++) {
                    JSONObject item = found.getJSONObject(i);
                    String text = item.getString("text").trim();
                    double a = item.getDouble("start") + start / 16000.0;
                    double b = Math.min(samples / 16000.0, item.getDouble("end") + start / 16000.0);
                    if (text.isEmpty() || b <= a) continue;
                    item.put("start", a).put("end", b).put("text", text)
                        .put("speaker", "UNKNOWN").put("segment_id", segments.length() + 1);
                    segments.put(item);
                }
                completed++;
                atomic(checkpoint, new JSONObject().put("identity", identity).put("completed", completed).put("segments", segments));
            }
            JSONObject report = new JSONObject().put("transcript_segments", segments)
                .put("duration", samples / 16000.0).put("completed", !stopping)
                .put("analysis_method", "Keyword candidates; verify against source audio. Speaker separation unavailable.")
                .put("events", events(segments)).put("accuracy_measured", false);
            atomic(new File(directory, "report.json"), report);
            status = stopping ? "Analysis paused. Tap Analyse to resume." : "Report saved. Review transcript and event candidates before using them.";
        } finally { NativeWhisper.close(context); }
    }

    private JSONArray events(JSONArray segments) throws Exception {
        String raw;
        try (InputStream stream = getAssets().open("event_patterns.json")) {
            ByteArrayOutputStream bytes = new ByteArrayOutputStream(); byte[] block = new byte[8192]; int count;
            while ((count = stream.read(block)) != -1) bytes.write(block, 0, count);
            raw = new String(bytes.toByteArray(), StandardCharsets.UTF_8);
        }
        JSONObject bank = new JSONObject(raw); JSONArray result = new JSONArray();
        Map<String,List<Pattern>> patterns = new LinkedHashMap<>();
        for (Iterator<String> keys=bank.keys(); keys.hasNext();) {
            String type = keys.next(); JSONArray items = bank.getJSONArray(type); List<Pattern> compiled = new ArrayList<>();
            for (int i=0; i<items.length(); i++) compiled.add(Pattern.compile(items.getString(i), Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE));
            patterns.put(type, compiled);
        }
        for (int i=0; i<segments.length(); i++) {
            JSONObject seg = segments.getJSONObject(i); String text = seg.getString("text");
            for (Map.Entry<String,List<Pattern>> entry : patterns.entrySet()) {
                if (entry.getKey().equals("decision") && Pattern.compile("not\\s+(yet\\s+)?decided|निर्णय नहीं|फैसला नहीं|तय नहीं|decide nahi", Pattern.CASE_INSENSITIVE).matcher(text).find()) continue;
                for (Pattern pattern : entry.getValue()) if (pattern.matcher(text).find()) {
                    result.put(new JSONObject().put("event_type", entry.getKey()).put("text", text)
                        .put("start", seg.getDouble("start")).put("end", seg.getDouble("end"))
                        .put("source_segment_id", seg.getInt("segment_id")).put("requires_review", true)); break;
                }
            }
        }
        return result;
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

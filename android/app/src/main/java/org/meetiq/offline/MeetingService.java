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
    static volatile MeetingProgress progress = new MeetingProgress("idle", null, "ready", 0, 0, 0, null);
    private void publish(String stage, String id, long completed, long total, float level, String error) {
        progress = new MeetingProgress(progress.operation, id, stage, completed, total, level, error);
    }
    private volatile boolean stopping = false;
    private PowerManager.WakeLock wakeLock;
    private Thread worker;
    private EventRules eventRules;
    private JSONArray eventCandidates = new JSONArray();
    private int analysedSegments = 0;
    private String speechModelHash;

    public IBinder onBind(Intent intent) { return null; }
    public void onCreate() {
        super.onCreate();
        getSystemService(NotificationManager.class).createNotificationChannel(
            new NotificationChannel("meeting", "Meeting recording and analysis", NotificationManager.IMPORTANCE_LOW));
    }
    public int onStartCommand(Intent intent, int flags, int id) {
        if (intent == null) { stopSelf(); return START_NOT_STICKY; }
        if ("stop".equals(intent.getAction())) {
            stopping = true;
            if (busy) publish(progress.recording() ? "saving" : "pausing", progress.meetingId,
                progress.completedSeconds, progress.totalSeconds, progress.microphoneLevel, null);
            return START_NOT_STICKY;
        }
        if (busy) return START_NOT_STICKY;
        final boolean record = "record".equals(intent.getAction());
        busy = true; stopping = false;
        progress = new MeetingProgress(record ? "record" : "analyse", intent.getStringExtra("meeting"), "starting", 0, 0, 0, null);
        Intent stop = new Intent(this, MeetingService.class).setAction("stop");
        PendingIntent stopIntent = PendingIntent.getService(this, 1, stop, PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(this, "meeting")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle("InfluenceIQ")
            .setContentText(record ? "Recording meeting — tap Stop when finished" : "Analysing locally")
            .setContentIntent(PendingIntent.getActivity(this, 2, new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE))
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
                android.util.Log.e("InfluenceIQ","Local analysis failed",error);
                Throwable cause=error; while(cause.getCause()!=null) cause=cause.getCause();
                String reason = cause.getMessage() == null ? cause.getClass().getSimpleName() : cause.getMessage();
                status = "Stopped: " + reason + ". Saved audio and completed chunks are retained.";
                publish("failed", progress.meetingId, progress.completedSeconds, progress.totalSeconds, 0, reason);
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
        atomic(new File(directory,"metadata.json"),new JSONObject()
            .put("analysis_language",new String[]{"auto","en","hi"}[Math.max(0,Math.min(2,getSharedPreferences("transcription",MODE_PRIVATE).getInt("language",0)))])
            .put("vocabulary",getSharedPreferences("transcription",MODE_PRIVATE).getString("vocabulary","")));
        LocalTransfers.attachDraft(this,directory);
        publish("recording", directory.getName(), 0, 0, 0, null);
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
                publish(stopping ? "saving" : "recording", directory.getName(), bytes / 32000, 0, MeetingProgress.amplitude(buffer, count), null);
            }
            status = "Recording saved. Ready to analyse locally.";
            publish("saved", directory.getName(), bytes / 32000, bytes / 32000, 0, null);
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
        speechModelHash=sha256(model);
        String identity = "v4:" + speechModelHash + ":" + sha256(audio) + ":" + language + ":" + vocabulary;
        File checkpoint = new File(directory, "checkpoint.json");
        JSONObject saved = checkpoint.exists() ? new JSONObject(new String(Files.readAllBytes(checkpoint.toPath()), StandardCharsets.UTF_8)) : new JSONObject();
        JSONArray segments = identity.equals(saved.optString("identity")) ? saved.getJSONArray("segments") : new JSONArray();
        int completed = identity.equals(saved.optString("identity")) ? saved.optInt("completed") : 0;
        long samples = Math.max(0, (audio.length() - 44) / 2);
        if (samples == 0) throw new IOException("Recording contains no audio");
        int chunk = 120 * 16000;
        saveReport(directory, segments, samples / 16000.0, false, language);
        publish("loading", meeting, Math.min(samples / 16000, completed * 120L), samples / 16000, 0, null);
        if (completed * (long)chunk >= samples) { finishAnalysis(directory,segments,samples/16000.0,language); return; }
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
                publish("transcribing", meeting, start / 16000, samples / 16000, 0, null);
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
                    JSONArray words=item.optJSONArray("words");
                    if(words!=null) for(int j=0;j<words.length();j++) {
                        JSONObject word=words.getJSONObject(j);
                        // Invalid native timestamps remain invalid for conservative fallback.
                        if(word.optDouble("start",-1)>=0) word.put("start",word.getDouble("start")+offset/16000.0);
                        if(word.optDouble("end",-1)>=0) word.put("end",word.getDouble("end")+offset/16000.0);
                    }
                    segments.put(item);
                }
                completed++;
                atomic(checkpoint, new JSONObject().put("identity", identity).put("completed", completed).put("segments", segments));
                saveReport(directory, segments, samples / 16000.0, false, language);
                publish(stopping ? "pausing" : "transcribing", meeting, Math.min(samples / 16000, completed * 120L), samples / 16000, 0, null);
            }
        } finally { NativeWhisper.close(context); }
        // Release the speech model before allocating the speaker model/audio buffer.
        if(completed*(long)chunk>=samples&&!stopping) finishAnalysis(directory,segments,samples/16000.0,language);
        else { status="Analysis paused. Tap Analyse to resume."; publish("paused",meeting,Math.min(samples/16000,completed*120L),samples/16000,0,null); }
    }

    private void finishAnalysis(File directory,JSONArray raw,double duration,String language) throws Exception {
        String id=directory.getName(); JSONArray turns=new JSONArray(); String problem=null;
        int expected=getSharedPreferences("transcription",MODE_PRIVATE).getInt("speakers",0);
        if(expected<0||expected>20) expected=0;
        publish("speakers",id,(long)duration,(long)duration,0,null); status="Identifying speakers locally…";
        if(duration>3600) problem="On-device speaker analysis supports up to one hour. The full transcript remains available.";
        else try {
            File segmentation=NativeSpeakers.model(this,"segmentation.onnx"), embedding=NativeSpeakers.model(this,"embedding.onnx");
            String identity="sherpa-1.13.8:"+sha256(new File(directory,"audio.wav"))+":"+sha256(segmentation)+":"+sha256(embedding)+":"+expected+":0.5";
            File cache=new File(directory,"speaker-turns.json"); JSONObject saved=cache.isFile()?MeetingRepository.read(cache):new JSONObject();
            if(identity.equals(saved.optString("identity"))) turns=saved.getJSONArray("turns");
            else { turns=new JSONArray(NativeSpeakers.run(new File(directory,"audio.wav"),segmentation,embedding,expected)); atomic(cache,new JSONObject().put("identity",identity).put("turns",turns)); }
        } catch(Exception|LinkageError error) { problem="Speaker analysis unavailable: "+error.getMessage(); }
        // Upstream inference cannot cancel mid-stage; its completed cache is retained.
        if(stopping) { status="Analysis paused after speaker processing. Resume to finish."; publish("paused",id,(long)duration,(long)duration,0,null); return; }
        JSONArray attributed=SpeakerReports.assign(raw,turns);
        analysedSegments=0; eventCandidates=new JSONArray();
        publish("fusion",id,(long)duration,(long)duration,0,null); status="Matching slide text and analysing contributions…";
        JSONObject report=baseReport(attributed,duration,true,language);
        report.put("diarization",new JSONObject().put("backend","sherpa-onnx-1.13.8").put("expected_speakers",expected).put("threshold",.5)
            .put("turns",turns).put("error",problem==null?JSONObject.NULL:problem).put("accuracy_measured",false));
        JSONArray slides=new JSONArray(); File source=new File(directory,"presentation.json"); if(source.isFile()) slides=MeetingRepository.read(source).getJSONArray("slides");
        MeetingAnalysis.analyse(report,events(attributed),slides);
        atomic(new File(directory,"report.json"),report);
        status=problem==null?"Analysis saved. Review speakers, influence and slide matches.":problem;
        publish("completed",id,(long)duration,(long)duration,0,null);
    }

    private void saveReport(File directory, JSONArray segments, double duration, boolean complete, String language) throws Exception {
        atomic(new File(directory, "report.json"),baseReport(segments,duration,complete,language));
    }
    private JSONObject baseReport(JSONArray segments,double duration,boolean complete,String language) throws Exception {
        List<String> texts=new ArrayList<>(); for(int i=0;i<segments.length();i++) texts.add(segments.getJSONObject(i).optString("text"));
        Set<String> detected=new LinkedHashSet<>(); for(int i=0;i<segments.length();i++) { String code=segments.getJSONObject(i).optString("detected_language"); if(code.equals("hi")||code.equals("en")) detected.add(code); }
        JSONObject report = new JSONObject().put("transcript_segments", segments)
            .put("duration", duration).put("completed", complete).put("language",detected.size()==1?detected.iterator().next():language)
            .put("requested_language",language).put("detected_languages",new JSONArray(detected))
            .put("processing",new JSONObject().put("offline",true).put("generative_notes_chat",false).put("asr_backend","whisper.cpp-1.7.6")
                .put("asr_model_sha256",speechModelHash).put("checkpoint_version",4).put("device","cpu"))
            .put("analysis_method", "Keyword candidates; full speaker and fusion analysis follows transcription.")
            .put("events", events(segments)).put("accuracy_measured", false)
            .put("vocabulary_suggestions",new JSONArray(Vocabulary.suggest(texts)));
        return report;
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
                    .put("speaker",seg.optString("speaker","UNKNOWN"))
                    .put("source_segment_id", seg.getInt("segment_id")).put("requires_review", true));
            }
        }
        analysedSegments = segments.length();
        return eventCandidates;
    }
    static String sha256(File file) throws Exception {
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

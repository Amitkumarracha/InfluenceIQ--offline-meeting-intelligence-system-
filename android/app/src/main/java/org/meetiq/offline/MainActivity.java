package org.meetiq.offline;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.media.MediaPlayer;
import android.os.*;
import android.text.*;
import android.text.method.LinkMovementMethod;
import android.text.style.ClickableSpan;
import android.view.View;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.*;

public class MainActivity extends Activity {
    private TextView state, report;
    private Spinner meetings;
    private Spinner language;
    private EditText vocabulary, search;
    private MediaPlayer player;
    private int page, maxPage;
    private String[] ids = new String[0];
    private final Handler handler = new Handler(Looper.getMainLooper());
    private volatile boolean importing;
    private File exportFile;
    private final Runnable refresh = new Runnable() {
        public void run() { state.setText(MeetingService.status); updateMeetings(); handler.postDelayed(this, 1500); }
    };

    public void onCreate(Bundle saved) {
        super.onCreate(saved);
        LinearLayout layout = new LinearLayout(this); layout.setOrientation(LinearLayout.VERTICAL);
        final int padding = (int)(16 * getResources().getDisplayMetrics().density);
        layout.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(padding, padding + insets.getSystemWindowInsetTop(), padding, padding + insets.getSystemWindowInsetBottom());
            return insets;
        });
        ScrollView scroll = new ScrollView(this); scroll.addView(layout); setContentView(scroll);
        TextView heading = new TextView(this); heading.setText("Meet IQ Offline"); heading.setTextSize(28); layout.addView(heading);
        TextView description = new TextView(this);
        description.setText("Record and analyse Hindi–English meetings on this phone. No internet permission, account, or server.\n\nPrototype: verify transcripts and event candidates. Speaker separation is not yet available. Obtain participants’ consent before recording.");
        description.setTextSize(16); layout.addView(description);
        state = new TextView(this); state.setPadding(0, 24, 0, 16); layout.addView(state);
        button(layout, "1. Import multilingual Whisper model (.bin)", () -> {
            if (MeetingService.busy || importing) { message("Stop the active operation first"); return; }
            Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(Intent.CATEGORY_OPENABLE);
            startActivityForResult(intent, 10);
        });
        button(layout, "2. Record meeting", () -> {
            if (MeetingService.busy || importing) { message("An operation is already running"); return; }
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1); return;
            }
            startForegroundService(new Intent(this, MeetingService.class).setAction("record"));
        });
        button(layout, "Stop recording / pause analysis", () -> {
            if (MeetingService.busy) startService(new Intent(this, MeetingService.class).setAction("stop"));
        });
        button(layout, "Import a recording (16 kHz mono PCM WAV)", () -> {
            if (MeetingService.busy || importing) { message("Stop the active operation first"); return; }
            startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType("audio/*").addCategory(Intent.CATEGORY_OPENABLE), 12);
        });
        meetings = new Spinner(this); layout.addView(meetings);
        TextView settings = new TextView(this); settings.setText("Transcription language and spelling hints"); layout.addView(settings);
        language = new Spinner(this); language.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, new String[]{"Hindi / English automatic", "English", "Hindi"})); layout.addView(language);
        vocabulary = new EditText(this); vocabulary.setHint("Names, acronyms and technical vocabulary (optional)"); vocabulary.setFilters(new InputFilter[]{new InputFilter.LengthFilter(1000)}); layout.addView(vocabulary);
        android.content.SharedPreferences preferences = getSharedPreferences("transcription", MODE_PRIVATE);
        language.setSelection(preferences.getInt("language", 0)); vocabulary.setText(preferences.getString("vocabulary", ""));
        button(layout, "3. Analyse selected meeting / resume", () -> {
            if (MeetingService.busy || importing) { message("An operation is already running"); return; }
            String id = selected(); if (id == null) return;
            int choice = language.getSelectedItemPosition();
            preferences.edit().putInt("language", choice).putString("vocabulary", vocabulary.getText().toString()).apply();
            startForegroundService(new Intent(this, MeetingService.class).setAction("analyse").putExtra("meeting", id)
                .putExtra("language", new String[]{"auto", "en", "hi"}[choice]).putExtra("vocabulary", vocabulary.getText().toString()));
        });
        button(layout, "Rename selected meeting", this::renameMeeting);
        button(layout, "Play selected recording", () -> { String id = selected(); if (id != null) play(id, 0); });
        button(layout, "Stop playback", this::stopPlayback);
        search = new EditText(this); search.setHint("Search transcript words…"); layout.addView(search);
        button(layout, "View transcript and candidates", this::viewReport);
        button(layout, "Previous transcript page", () -> { if (page > 0) { page--; viewReport(); } });
        button(layout, "Next transcript page", () -> { if (page < maxPage) { page++; viewReport(); } });
        button(layout, "Export report JSON", () -> export("report.json", "application/json"));
        button(layout, "Export meeting notes + transcript Markdown", () -> export("notes.md", "text/markdown"));
        button(layout, "Export original recording WAV", () -> export("audio.wav", "audio/wav"));
        report = new TextView(this); report.setMovementMethod(LinkMovementMethod.getInstance()); report.setTextSize(16); layout.addView(report);
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s, int a, int c, int f) { }
            public void onTextChanged(CharSequence s, int a, int b, int c) { page = 0; }
            public void afterTextChanged(Editable value) { }
        });
        meetings.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            public void onItemSelected(AdapterView<?> parent, View view, int position, long id) { page = 0; report.setText(""); stopPlayback(); }
            public void onNothingSelected(AdapterView<?> parent) { }
        });
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 2);
    }
    private void button(LinearLayout layout, String text, Runnable action) {
        Button button = new Button(this); button.setText(text); button.setAllCaps(false);
        button.setOnClickListener(view -> action.run()); layout.addView(button);
    }
    private void message(String value) { Toast.makeText(this, value, Toast.LENGTH_LONG).show(); }
    public void onResume() { super.onResume(); handler.post(refresh); }
    public void onPause() { handler.removeCallbacks(refresh); stopPlayback(); super.onPause(); }
    private String selected() {
        int position = meetings.getSelectedItemPosition();
        if (position < 0 || position >= ids.length) { message("Record a meeting first"); return null; }
        return ids[position];
    }
    private void updateMeetings() {
        File parent = new File(getFilesDir(), "meetings");
        String[] found = parent.list((dir, name) -> name.matches("[0-9]+"));
        if (found == null) found = new String[0];
        Arrays.sort(found, Collections.reverseOrder());
        if (!Arrays.equals(ids, found)) {
            ids = found; String[] labels = new String[ids.length];
            for (int i=0; i<ids.length; i++) labels[i] = title(ids[i]);
            meetings.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, labels));
        }
    }
    private void viewReport() {
        String id = selected(); if (id == null) return;
        try {
            File file = new File(getFilesDir(), "meetings/" + id + "/report.json");
            JSONObject data = new JSONObject(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
            SpannableStringBuilder text = new SpannableStringBuilder(title(id) + (data.optBoolean("completed") ? "\n" : "\nPartial transcript — resume analysis for the rest.\n") + "Candidates — review against recording\n\n");
            String query = search.getText().toString().trim().toLowerCase(Locale.ROOT);
            JSONArray events = data.getJSONArray("events");
            int shown = 0;
            for (int i=0; i<events.length() && shown < 50; i++) {
                JSONObject item = events.getJSONObject(i);
                if (!item.getString("text").toLowerCase(Locale.ROOT).contains(query)) continue;
                shown++;
                text.append(item.getString("event_type")).append(" @ ");
                timestamp(text, id, item.getDouble("start")); text.append("\n").append(item.getString("text")).append("\n\n");
            }
            text.append("Transcript — speaker unknown. Tap timestamps to listen.\n\n");
            JSONArray segments = data.getJSONArray("transcript_segments");
            List<JSONObject> filtered = new ArrayList<>();
            for (int i=0; i<segments.length(); i++) {
                JSONObject item = segments.getJSONObject(i);
                if (item.getString("text").toLowerCase(Locale.ROOT).contains(query)) filtered.add(item);
            }
            maxPage = Math.max(0, (filtered.size() - 1) / 100); page = Math.min(page, maxPage);
            text.append("Page " + (page + 1) + " / " + (maxPage + 1) + " · " + filtered.size() + " matching passages\n\n");
            for (int i=page * 100; i<Math.min(filtered.size(), (page + 1) * 100); i++) {
                JSONObject item = filtered.get(i); timestamp(text, id, item.getDouble("start"));
                text.append("  ").append(item.getString("text")).append("\n\n");
            }
            if (events.length() > 50) text.append("Candidate preview is limited to 50 matches. Export includes all candidates.\n");
            report.setText(text);
        } catch (Exception error) { message("No report yet. Analyse this meeting first."); }
    }
    private void timestamp(SpannableStringBuilder text, String id, double seconds) {
        int start = text.length(); text.append(stamp(seconds));
        text.setSpan(new ClickableSpan() { public void onClick(View view) { play(id, seconds); } }, start, text.length(), Spanned.SPAN_EXCLUSIVE_EXCLUSIVE);
    }
    private void stopPlayback() { if (player != null) { player.release(); player = null; } }
    private void play(String id, double seconds) {
        if (MeetingService.busy || importing) { message("Stop the active operation before playback"); return; }
        stopPlayback();
        try {
            player = new MediaPlayer(); player.setDataSource(new File(getFilesDir(), "meetings/" + id + "/audio.wav").getAbsolutePath());
            player.setOnPreparedListener(media -> { media.seekTo((int)(seconds * 1000)); media.start(); });
            player.setOnCompletionListener(media -> stopPlayback());
            player.setOnErrorListener((media, what, extra) -> { stopPlayback(); message("Recording cannot be played"); return true; });
            player.prepareAsync();
        } catch (Exception error) { stopPlayback(); message("Recording cannot be played"); }
    }
    private String title(String id) {
        try { return new JSONObject(new String(Files.readAllBytes(new File(getFilesDir(), "meetings/" + id + "/metadata.json").toPath()), StandardCharsets.UTF_8)).getString("title"); }
        catch (Exception ignored) { return new java.text.SimpleDateFormat("dd MMM yyyy HH:mm:ss", Locale.getDefault()).format(new Date(Long.parseLong(id))); }
    }
    private void renameMeeting() {
        if (MeetingService.busy || importing) { message("Stop the active operation first"); return; }
        String id = selected(); if (id == null) return;
        EditText input = new EditText(this); input.setText(title(id)); input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(200)});
        new AlertDialog.Builder(this).setTitle("Meeting title").setView(input).setNegativeButton("Cancel", null).setPositiveButton("Save", (dialog, which) -> {
            try {
                String value = input.getText().toString().trim(); if (value.isEmpty()) throw new IOException("Enter a title");
                MeetingService.atomic(new File(getFilesDir(), "meetings/" + id + "/metadata.json"), new JSONObject().put("title", value));
                ids = new String[0]; updateMeetings(); meetings.setSelection(Arrays.asList(ids).indexOf(id));
            } catch (Exception error) { message("Could not save title: " + error.getMessage()); }
        }).show();
    }
    private String stamp(double seconds) {
        long s = (long)seconds; return String.format(Locale.ROOT, "%02d:%02d:%02d", s/3600, s/60%60, s%60);
    }
    private void export(String name, String type) {
        if (MeetingService.busy) { message("Stop recording or pause analysis before exporting"); return; }
        String id = selected(); if (id == null) return;
        exportFile = new File(getFilesDir(), "meetings/" + id + "/" + name);
        if (name.equals("notes.md")) {
            try {
                JSONObject data = new JSONObject(new String(Files.readAllBytes(new File(exportFile.getParentFile(), "report.json").toPath()), StandardCharsets.UTF_8));
                StringBuilder text = new StringBuilder("# " + title(id) + "\n\nOffline draft; verify against original audio. Speaker separation unavailable.\n");
                if (!data.optBoolean("completed")) text.append("\nPartial transcript — analysis is incomplete.\n");
                text.append("\n## Event candidates\n\n");
                JSONArray events = data.getJSONArray("events");
                for (int i=0; i<events.length(); i++) { JSONObject item = events.getJSONObject(i); text.append("- ").append(item.getString("event_type")).append(" [").append(stamp(item.getDouble("start"))).append("] ").append(item.getString("text")).append("\n"); }
                text.append("\n## Full transcript\n\n");
                JSONArray segments = data.getJSONArray("transcript_segments");
                for (int i=0; i<segments.length(); i++) { JSONObject item = segments.getJSONObject(i); text.append("[").append(stamp(item.getDouble("start"))).append("] UNKNOWN: ").append(item.getString("text")).append("\n\n"); }
                Files.write(exportFile.toPath(), text.toString().getBytes(StandardCharsets.UTF_8));
            } catch (Exception error) { message("Analyse the meeting before exporting notes"); return; }
        }
        if (!exportFile.exists()) { message("File not available yet"); return; }
        startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType(type)
            .addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE, id + "_" + name), 11);
    }
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (result != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        if (request == 10) {
            importing = true; MeetingService.status = "Importing model into private phone storage…";
            new Thread(() -> {
                File temp = new File(getFilesDir(), "model.tmp");
                try {
                    MessageDigest digest = MessageDigest.getInstance("SHA-256"); long total = 0;
                    try (InputStream in = getContentResolver().openInputStream(uri); FileOutputStream out = new FileOutputStream(temp)) {
                        byte[] block = new byte[1024*1024]; int count;
                        while ((count = in.read(block)) != -1) {
                            total += count; if (total > 2L*1024*1024*1024) throw new IOException("Use a tiny, base, or small model under 2 GB");
                            out.write(block, 0, count); digest.update(block, 0, count);
                        }
                        out.getFD().sync();
                    }
                    // Reject HTML/download error pages and non-GGML files before replacing a working model.
                    try (RandomAccessFile model = new RandomAccessFile(temp, "r")) {
                        if (Integer.reverseBytes(model.readInt()) != 0x67676d6c) throw new IOException("Not a GGML Whisper model");
                    }
                    File target = new File(getFilesDir(), "model.bin");
                    if (!temp.renameTo(target)) throw new IOException("Cannot install model");
                    StringBuilder hash = new StringBuilder(); for (byte b : digest.digest()) hash.append(String.format("%02x", b));
                    Files.write(new File(getFilesDir(), "model.sha256").toPath(), hash.toString().getBytes(StandardCharsets.UTF_8));
                    MeetingService.status = "Model installed. Ready for offline transcription.";
                } catch (Exception error) { temp.delete(); MeetingService.status = "Model import failed: " + error.getMessage(); }
                finally { importing = false; }
            }).start();
        } else if (request == 12) {
            importing = true; MeetingService.status = "Importing local recording…";
            new Thread(() -> {
                File temp = new File(getFilesDir(), "audio-import.tmp"), directory = null;
                try {
                    try (InputStream in = getContentResolver().openInputStream(uri); FileOutputStream out = new FileOutputStream(temp)) {
                        byte[] block = new byte[65536]; int count; long total = 0;
                        while ((count = in.read(block)) != -1) {
                            total += count;
                            if (total > 700L * 1024 * 1024 || temp.getParentFile().getUsableSpace() < count + 1024 * 1024) throw new IOException("Recording too large or phone storage full");
                            out.write(block, 0, count);
                        }
                    }
                    directory = new File(getFilesDir(), "meetings/" + System.currentTimeMillis());
                    if (!directory.mkdirs()) throw new IOException("Cannot create meeting folder");
                    WavAudio.normalize(temp, new File(directory, "audio.wav"));
                    MeetingService.status = "Recording imported. Select it and tap Analyse.";
                } catch (Exception error) {
                    if (directory != null) { new File(directory, "audio.wav").delete(); directory.delete(); }
                    MeetingService.status = "Recording import failed: " + error.getMessage();
                } finally { temp.delete(); importing = false; }
            }).start();
        } else if (request == 11 && exportFile != null) {
            final File source = exportFile;
            new Thread(() -> {
                try (InputStream in = new FileInputStream(source); OutputStream out = getContentResolver().openOutputStream(uri)) {
                    byte[] block = new byte[1024*1024]; int count;
                    while ((count = in.read(block)) != -1) out.write(block, 0, count);
                    runOnUiThread(() -> message("Export saved"));
                } catch (Exception error) { runOnUiThread(() -> message("Export failed: " + error.getMessage())); }
            }).start();
        }
    }
}

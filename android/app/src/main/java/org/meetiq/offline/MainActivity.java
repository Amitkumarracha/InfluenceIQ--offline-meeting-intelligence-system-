package org.meetiq.offline;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.*;
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
    private String[] ids = new String[0];
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean importing;
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
        meetings = new Spinner(this); layout.addView(meetings);
        button(layout, "3. Analyse selected meeting / resume", () -> {
            if (MeetingService.busy || importing) { message("An operation is already running"); return; }
            String id = selected(); if (id == null) return;
            startForegroundService(new Intent(this, MeetingService.class).setAction("analyse").putExtra("meeting", id));
        });
        button(layout, "View transcript and candidates", this::viewReport);
        button(layout, "Export report JSON", () -> export("report.json", "application/json"));
        button(layout, "Export original recording WAV", () -> export("audio.wav", "audio/wav"));
        report = new TextView(this); report.setTextIsSelectable(true); report.setTextSize(16); layout.addView(report);
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED)
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 2);
    }
    private void button(LinearLayout layout, String text, Runnable action) {
        Button button = new Button(this); button.setText(text); button.setAllCaps(false);
        button.setOnClickListener(view -> action.run()); layout.addView(button);
    }
    private void message(String value) { Toast.makeText(this, value, Toast.LENGTH_LONG).show(); }
    public void onResume() { super.onResume(); handler.post(refresh); }
    public void onPause() { handler.removeCallbacks(refresh); super.onPause(); }
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
            for (int i=0; i<ids.length; i++) labels[i] = new java.text.SimpleDateFormat("dd MMM yyyy HH:mm:ss", Locale.getDefault()).format(new Date(Long.parseLong(ids[i])));
            meetings.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, labels));
        }
    }
    private void viewReport() {
        String id = selected(); if (id == null) return;
        try {
            File file = new File(getFilesDir(), "meetings/" + id + "/report.json");
            JSONObject data = new JSONObject(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
            StringBuilder text = new StringBuilder("Candidates — review against recording\n\n");
            JSONArray events = data.getJSONArray("events");
            for (int i=0; i<events.length(); i++) {
                JSONObject item = events.getJSONObject(i);
                text.append(item.getString("event_type")).append(" @ ").append(stamp(item.getDouble("start"))).append("\n").append(item.getString("text")).append("\n\n");
            }
            text.append("Full transcript — speaker unknown\n\n");
            JSONArray segments = data.getJSONArray("transcript_segments");
            for (int i=0; i<segments.length(); i++) {
                JSONObject item = segments.getJSONObject(i);
                text.append(stamp(item.getDouble("start"))).append("  ").append(item.getString("text")).append("\n\n");
            }
            report.setText(text);
        } catch (Exception error) { message("No report yet. Analyse this meeting first."); }
    }
    private String stamp(double seconds) {
        long s = (long)seconds; return String.format(Locale.ROOT, "%02d:%02d:%02d", s/3600, s/60%60, s%60);
    }
    private void export(String name, String type) {
        if (MeetingService.busy) { message("Stop recording or pause analysis before exporting"); return; }
        String id = selected(); if (id == null) return;
        exportFile = new File(getFilesDir(), "meetings/" + id + "/" + name);
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

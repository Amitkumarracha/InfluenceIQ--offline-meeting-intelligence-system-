package org.meetiq.offline;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.net.Uri;
import android.os.*;
import android.text.*;
import android.text.style.*;
import android.view.*;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.text.Normalizer;
import java.util.*;
import java.util.concurrent.*;

/** Native screen navigation. Storage, playback and long-running processing stay separate. */
public class MainActivity extends Activity {
    private Ui ui;
    private final AccountView accountView=new AccountView();
    private String accountReturn="home";
    private long accountRevision=AccountSync.revision;
    private LinearLayout root, body, passageList;
    private ScrollView scroll;
    private TextView timer, progressTitle, progressClock, progressNote, pageLabel, audioClock, audioNote;
    private ProgressBar progressBar;
    private Button pauseAnalysis, audioButton, audioStop;
    private SeekBar audioSeek;
    private Ui.Waveform waveform;
    private EditText search;
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final ExecutorService io=Executors.newSingleThreadExecutor();
    private MeetingRepository repository;
    private AudioPlaybackController playback;
    private List<MeetingRepository.Meeting> meetings=new ArrayList<>();
    private JSONObject selectedReport;
    private JSONObject selectedMetadata=new JSONObject();
    private String screen="home", settingsReturn="home", selectedId, tab="Overview", query="", candidateFilter="All", exportName;
    private int page, maxPage, historyLimit=20;
    private boolean loading, resumed, pendingRecord, pendingStart, metadataLoaded;
    private String error, renderedKey;
    private MeetingProgress observed=MeetingService.progress;
    private long observedGeneration=MeetingService.generation;
    private boolean observedBusy;
    private long transferRevision=LocalTransfers.revision, lastWaveSecond=-1;
    private final Runnable tick=new Runnable() {
        public void run() {
            if (!resumed) return;
            MeetingProgress current=MeetingService.progress;
            long generation=MeetingService.generation;
            boolean busyChanged=observedBusy!=MeetingService.busy;
            boolean milestone=generation!=observedGeneration || !Objects.equals(current.meetingId,observed.meetingId) || !current.stage.equals(observed.stage)
                || (!current.recording() && current.completedSeconds!=observed.completedSeconds);
            if (MeetingService.busy || milestone) pendingStart=false;
            if (current.error!=null && !Objects.equals(current.error,observed.error)) { error=current.error; renderedKey=null; }
            if (observedBusy && !MeetingService.busy && current.recording() && "saved".equals(current.stage)) {
                selectedId=current.meetingId; selectedReport=null; selectedMetadata=new JSONObject(); metadataLoaded=false; screen="detail"; tab="Overview"; page=0; query="";
            }
            observed=current; observedBusy=MeetingService.busy; observedGeneration=generation;
            if (LocalTransfers.revision!=transferRevision) {
                transferRevision=LocalTransfers.revision;
                if (!LocalTransfers.busy) {
                    if (LocalTransfers.importedMeeting!=null) {
                        selectedId=LocalTransfers.importedMeeting; screen="detail"; tab="Overview"; selectedReport=null; selectedMetadata=new JSONObject(); metadataLoaded=false; query=""; page=0;
                    }
                    if (LocalTransfers.message.startsWith("Could not")) error=LocalTransfers.message; else message(LocalTransfers.message);
                    reload();
                }
                render();
            } else if (milestone || busyChanged) reload();
            if(accountRevision!=AccountSync.revision) {
                accountRevision=AccountSync.revision;
                if(!AccountSync.busy) {
                    if(AccountSync.message.startsWith("Could not")) error=AccountSync.message;
                    else if(!screen.equals("account")) message(AccountSync.message);
                    if(AccountSync.downloadedMeeting!=null) { openMeeting(AccountSync.downloadedMeeting); }
                    else reload();
                }
                render();
            }
            updateLive(); handler.postDelayed(this,500);
        }
    };

    public void onCreate(Bundle saved) {
        boolean dark=(getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK)==Configuration.UI_MODE_NIGHT_YES;
        super.onCreate(saved); ui=new Ui(this); repository=new MeetingRepository(getFilesDir());
        playback=new AudioPlaybackController(this::updateAudio);
        if (saved!=null) {
            screen=saved.getString("screen","home"); selectedId=saved.getString("meeting"); tab=saved.getString("tab","Overview");
            query=saved.getString("query",""); page=saved.getInt("page"); exportName=saved.getString("export");
            accountReturn=saved.getString("accountReturn","home");
            candidateFilter=saved.getString("filter","All"); settingsReturn=saved.getString("settingsReturn","home");
            pendingRecord=saved.getBoolean("pendingRecord"); error=saved.getString("error");
            transferRevision=saved.getLong("transferRevision",transferRevision);
        }
        root=ui.column(); root.setBackgroundColor(ui.background);
        getWindow().setStatusBarColor(ui.background); getWindow().setNavigationBarColor(ui.background);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE|View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            |View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION|(dark?0:View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR));
        root.setOnApplyWindowInsetsListener((view,insets) -> {
            int left,top,right,bottom;
            if (Build.VERSION.SDK_INT>=30) {
                android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());
                android.graphics.Insets keyboard=insets.getInsets(WindowInsets.Type.ime());
                left=bars.left; top=bars.top; right=bars.right; bottom=Math.max(bars.bottom,keyboard.bottom);
            } else { left=insets.getSystemWindowInsetLeft(); top=insets.getSystemWindowInsetTop(); right=insets.getSystemWindowInsetRight(); bottom=insets.getSystemWindowInsetBottom(); }
            view.setPadding(left,top,right,bottom); return insets;
        });
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);
        setContentView(root); root.requestApplyInsets();
        if (Build.VERSION.SDK_INT>=33) getOnBackInvokedDispatcher().registerOnBackInvokedCallback(android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,this::back);
        render(); reload();
    }
    public void onResume() {
        super.onResume(); resumed=true;
        MeetingProgress current=MeetingService.progress;
        if (MeetingService.busy && current.recording()) screen="recording";
        else if(screen.equals("recording")&&!pendingStart) {
            if(current.recording()&&current.stage.equals("saved")) {
                selectedId=current.meetingId; selectedReport=null; selectedMetadata=new JSONObject(); metadataLoaded=false; screen="detail"; tab="Overview"; query=""; page=0;
            } else { screen="home"; if(current.error!=null) error=current.error; }
        }
        handler.removeCallbacks(tick); handler.post(tick); reload();
    }
    public void onPause() { resumed=false; handler.removeCallbacks(tick); playback.release(); super.onPause(); }
    public void onDestroy() { io.shutdownNow(); playback.release(); super.onDestroy(); }
    protected void onSaveInstanceState(Bundle out) {
        out.putString("accountReturn",accountReturn); out.putString("screen",screen); out.putString("meeting",selectedId); out.putString("tab",tab); out.putString("query",query);
        out.putInt("page",page); out.putString("export",exportName); out.putString("filter",candidateFilter);
        out.putString("settingsReturn",settingsReturn); out.putBoolean("pendingRecord",pendingRecord);
        out.putString("error",error); out.putLong("transferRevision",transferRevision); super.onSaveInstanceState(out);
    }
    public void onBackPressed() { back(); }
    private void back() {
        if (screen.equals("home")) { moveTaskToBack(true); return; }
        screen=screen.equals("account")?accountReturn:screen.equals("settings")?settingsReturn:"home"; render();
    }
    private boolean locked() { return AccountSync.busy || MeetingService.busy || LocalTransfers.busy || pendingStart; }
    private boolean modelReady() { File model=new File(getFilesDir(),"model.bin"); return model.isFile() && model.length()>4; }
    private SharedPreferences preferences() { return getSharedPreferences("transcription",MODE_PRIVATE); }
    private String languageCode() { return new String[]{"auto","en","hi"}[Math.max(0,Math.min(2,preferences().getInt("language",0)))]; }
    private MeetingRepository.Meeting meeting() { for (MeetingRepository.Meeting item:meetings) if (item.id.equals(selectedId)) return item; return null; }
    private void reload() {
        if (loading || isDestroyed()) return; loading=true;
        String requested=selectedId;
        io.execute(() -> {
            List<MeetingRepository.Meeting> found; String issue=null;
            try { found=repository.list(); } catch(Exception failure) { found=new ArrayList<>(); issue="Could not read the meeting library. Your files remain stored locally."; }
            final List<MeetingRepository.Meeting> library=found; final String libraryError=issue; JSONObject data=null;
            if (requested!=null) try { data=repository.report(requested); } catch (Exception ignored) { }
            final JSONObject report=data;
            final JSONObject metadata=requested==null?new JSONObject():repository.metadata(requested);
            runOnUiThread(() -> {
                if (isDestroyed()) return; loading=false; meetings=library; if(libraryError!=null) error=libraryError;
                if (!Objects.equals(requested,selectedId)) { reload(); return; }
                selectedReport=report; selectedMetadata=metadata; metadataLoaded=true;
                if (screen.equals("detail") && passageList!=null && (tab.equals("Transcript")||tab.equals("Action items")||tab.equals("Decisions"))) { renderPassages(); updateLive(); }
                else if (!screen.equals("settings") || !LocalTransfers.busy) render();
            });
        });
    }
    private void openMeeting(String id) {
        if (MeetingService.busy && MeetingService.progress.recording() && id.equals(MeetingService.progress.meetingId)) { screen="recording"; render(); return; }
        playback.release(); selectedId=id; selectedReport=null; selectedMetadata=new JSONObject(); metadataLoaded=false; screen="detail"; tab="Overview"; query=""; page=0; render(); reload();
    }
    private void account() { accountReturn=screen; screen="account"; render(); }
    private void settings() { settingsReturn=screen; screen="settings"; render(); }
    private void render() {
        if (root==null || isDestroyed()) return;
        String key=screen+":"+selectedId+":"+tab;
        int position=Objects.equals(key,renderedKey)&&scroll!=null?scroll.getScrollY():0; renderedKey=key;
        timer=null; waveform=null; progressBar=null; progressTitle=null; progressClock=null; progressNote=null;
        pauseAnalysis=null; audioSeek=null; audioButton=null; audioStop=null; audioClock=null; audioNote=null; passageList=null; pageLabel=null; search=null;
        root.removeAllViews(); scroll=new ScrollView(this); scroll.setFillViewport(true); scroll.setClipToPadding(false);
        body=ui.column(); body.setPadding(ui.dp(18),ui.dp(12),ui.dp(18),ui.dp(24));
        scroll.addView(body,new ScrollView.LayoutParams(-1,-2)); root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));
        if (error!=null) {
            LinearLayout note=ui.notice("Something needs attention",error,true);
            ui.add(note,ui.button("Dismiss message",false,() -> { error=null; render(); }),0); ui.add(body,note,12);
        }
        if (screen.equals("recording")) recording(); else if (screen.equals("detail")) detail();
        else if (screen.equals("account")) accountView.render(this,ui,body,this::back,this::render);
        else if (screen.equals("settings")) modelSettings(); else if (screen.equals("library")) library(); else home();
        if(AccountSync.busy&&!screen.equals("account")) ui.add(body,ui.notice("Account sync",AccountSync.message,false),12);
        if (LocalTransfers.busy) ui.add(body,ui.notice("Working locally",LocalTransfers.message,false),12);
        updateLive(); scroll.post(() -> scroll.scrollTo(0,position));
    }
    private void toolbar(String title,Runnable backAction,boolean settingsButton) {
        LinearLayout header=ui.row(); header.addView(ui.iconButton("back","Back",backAction));
        TextView label=ui.text(title,20,ui.text,true); label.setMaxLines(2); label.setEllipsize(TextUtils.TruncateAt.END);
        header.addView(label,new LinearLayout.LayoutParams(0,-2,1));
        if (settingsButton) header.addView(ui.iconButton("settings","Settings",this::settings)); ui.add(body,header,20);
    }
    private void home() {
        LinearLayout header=ui.row(); TextView brand=ui.text("InfluenceIQ",26,ui.text,true);
        header.addView(brand,new LinearLayout.LayoutParams(0,-2,1)); header.addView(ui.iconButton("settings","Settings",this::settings)); ui.add(body,header,24);
        ui.add(body,ui.action("document","Account & sync",AccountSession.signedIn(this)?AccountSession.preferences(this).getString("email",""):"Use the same account as the website",false,this::account),18);
        ui.add(body,ui.text("Capture the conversation.",25,ui.text,true),8);
        ui.add(body,ui.text("Your transcript, actions and decisions — saved together.",15,ui.muted,false),24);
        if(MeetingService.busy) ui.add(body,ui.action(MeetingService.progress.recording()?"mic":"wave",MeetingService.progress.recording()?"Return to recording":"View analysis", "Your progress is saved",false,() -> {
            if(MeetingService.progress.recording()) { screen="recording"; render(); } else openMeeting(MeetingService.progress.meetingId);
        }),14);
        View record=ui.action("mic","Record meeting","Use your microphone",true,this::requestRecording); ui.enabled(record,!locked()); ui.add(body,record,12);
        View imported=ui.action("document","Upload audio","WAV, MP3, M4A and supported recordings",false,() -> picker(12,"audio/*")); ui.enabled(imported,!locked()); ui.add(body,imported,18);
        Button ppt=ui.button(new File(getFilesDir(),"draft-presentation.pptx").isFile()?"Replace PPT for next meeting":"Upload PPT (optional)",false,() -> picker(13,"application/vnd.openxmlformats-officedocument.presentationml.presentation")); ui.enabled(ppt,!locked()); ui.add(body,ppt,6);
        Button hints=ui.button("Vocabulary hints (optional)",false,() -> editVocabulary(false)); ui.enabled(hints,!locked()); ui.add(body,hints,16);
        if(!modelReady()) ui.add(body,ui.text("Recording works now. Set up local analysis in Settings when you’re ready.",13,ui.muted,false),16);
        LinearLayout heading=ui.row(); heading.addView(ui.text("Recent meetings",18,ui.text,true),new LinearLayout.LayoutParams(0,-2,1));
        Button all=ui.button("History",false,() -> { screen="library"; render(); }); all.setTextColor(ui.accent); all.setBackgroundColor(android.graphics.Color.TRANSPARENT);
        heading.addView(all,new LinearLayout.LayoutParams(-2,-2)); ui.add(body,heading,12);
        if(meetings.isEmpty()) ui.add(body,ui.text("Your first meeting starts here. Record or upload audio.",14,ui.muted,false),18);
        else for(int i=0;i<Math.min(3,meetings.size());i++) meetingCard(meetings.get(i));
        ui.add(body,ui.text("Private · stored on this device",12,ui.muted,false),0);
    }
    private void library() {
        toolbar("History",() -> { screen="home"; render(); },true);
        ui.add(body,ui.text(meetings.size()+" saved meetings",14,ui.muted,false),18);
        if (meetings.isEmpty()) empty("No meetings yet","Record your first meeting from the home screen.");
        for(int i=0;i<Math.min(historyLimit,meetings.size());i++) meetingCard(meetings.get(i));
        if (meetings.size()>historyLimit) ui.add(body,ui.button("Show more meetings",false,() -> { historyLimit+=20; render(); }),0);
    }
    private void meetingCard(MeetingRepository.Meeting meeting) {
        LinearLayout card=ui.card(), row=ui.row();
        Ui.Icon icon=new Ui.Icon(this,meeting.completed?"play":"document",ui.blue); row.addView(icon,new LinearLayout.LayoutParams(ui.dp(24),ui.dp(24)));
        LinearLayout labels=ui.column(); labels.setPadding(ui.dp(12),0,ui.dp(6),0);
        TextView title=ui.text(meeting.title,16,ui.text,true); title.setMaxLines(2); title.setEllipsize(TextUtils.TruncateAt.END); ui.add(labels,title,5);
        ui.add(labels,ui.text(meeting.date()+" · "+MeetingRepository.stamp(meeting.duration),12,ui.muted,false),6);

        row.addView(labels,new LinearLayout.LayoutParams(0,-2,1)); row.addView(new Ui.Icon(this,"chevron",ui.muted),new LinearLayout.LayoutParams(ui.dp(18),ui.dp(18)));
        ui.add(card,row,10); LinearLayout status=ui.row(); status.addView(ui.chip(meeting.status(),meeting.completed?ui.accent:ui.blue,ui.dark?0xFF183447:0xFFE9F2FA));

        ui.add(card,status,0); card.setBackground(ui.touch(ui.card,ui.border,18)); card.setContentDescription("Open meeting "+meeting.title); card.setFocusable(true);
        card.setOnClickListener(view -> openMeeting(meeting.id)); ui.add(body,card,12);
    }
    private void empty(String title,String description) { ui.add(body,ui.notice(title,description,false),16); }
    private void recording() {
        toolbar("Record meeting",() -> { screen="home"; render(); },false);
        TextView live=ui.text("●  Recording locally",19,ui.text,true); SpannableString indicator=new SpannableString("●  Recording locally"); indicator.setSpan(new ForegroundColorSpan(Ui.color("#FF5963")),0,1,0); live.setText(indicator); live.setGravity(Gravity.CENTER); ui.add(body,live,28);
        timer=ui.text("00:00:00",54,ui.text,true); timer.setGravity(Gravity.CENTER); timer.setTypeface(android.graphics.Typeface.MONOSPACE);
        timer.setAutoSizeTextTypeUniformWithConfiguration(24,54,1,android.util.TypedValue.COMPLEX_UNIT_SP); timer.setMinHeight(ui.dp(80)); ui.add(body,timer,8);
        TextView hint=ui.text("Hours : Minutes : Seconds",13,ui.muted,false); hint.setGravity(Gravity.CENTER); ui.add(body,hint,22);
        waveform=new Ui.Waveform(this,ui.accent); body.addView(waveform,new LinearLayout.LayoutParams(-1,ui.dp(96))); ui.space(body,24);
        ui.add(body,ui.text("Keep the phone close to the speakers for clearer audio.",14,ui.muted,false),24);
        Button stop=ui.button("Stop & save",true,this::stopOperation); stop.setTextColor(android.graphics.Color.WHITE);
        stop.setBackground(ui.touch(Ui.color("#D32F3E"),0,18)); ui.enabled(stop,MeetingService.busy&&!"saving".equals(MeetingService.progress.stage)); ui.add(body,stop,12);
        TextView note=ui.text("Your recording is kept when you leave this screen.",13,ui.muted,false); note.setGravity(Gravity.CENTER); ui.add(body,note,0);
    }
    private void detail() {
        MeetingRepository.Meeting meeting=meeting();
        LinearLayout header=ui.row(); header.addView(ui.iconButton("back","Back to meetings",() -> { screen="home"; render(); }));
        TextView title=ui.text(meeting==null?"Meeting":meeting.title,20,ui.text,true); title.setMaxLines(2); title.setEllipsize(TextUtils.TruncateAt.END); header.addView(title,new LinearLayout.LayoutParams(0,-2,1));
        View rename=ui.iconButton("more","Meeting options",this::meetingOptions); ui.enabled(rename,meeting!=null&&!locked()); header.addView(rename); ui.add(body,header,14);
        if (meeting==null) { empty("Opening your meeting","Loading local recording and saved report…"); return; }
        ui.add(body,ui.text(meeting.date()+" · "+MeetingRepository.stamp(meeting.duration),13,ui.muted,false),10);
        LinearLayout metadata=ui.row(); TextView language=ui.text(MeetingRepository.language(meeting.language),13,ui.muted,false); language.setPadding(0,0,ui.dp(10),0);
        metadata.addView(language,new LinearLayout.LayoutParams(0,-2,1));
        metadata.addView(ui.chip(meeting.status(),meeting.completed?ui.accent:ui.blue,ui.dark?0xFF17374A:0xFFE6F1F9)); ui.add(body,metadata,20);
        HorizontalScrollView tabs=new HorizontalScrollView(this); tabs.setHorizontalScrollBarEnabled(false); LinearLayout choices=ui.row();
        for(String section:new String[]{"Overview","Transcript","Participants","Action items","Decisions","Analysis","Presentation"}) {
            Button choice=ui.button(section,section.equals(tab),() -> { tab=section; query=""; page=0; render(); scroll.scrollTo(0,0); });
            choice.setTextSize(13); choice.setPadding(ui.dp(8),ui.dp(12),ui.dp(8),ui.dp(12)); LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-2,-2); params.rightMargin=ui.dp(5); choices.addView(choice,params);
            if(section.equals(tab)) choice.post(() -> tabs.smoothScrollTo(Math.max(0,choice.getLeft()-ui.dp(10)),0));
        }
        tabs.addView(choices); ui.add(body,tabs,18);
        if (meeting.problem!=null) ui.add(body,ui.notice("Report unavailable",meeting.problem,true),14);
        if (MeetingService.busy && !MeetingService.progress.recording() && meeting.id.equals(MeetingService.progress.meetingId)) analysisCard(meeting);
        if (tab.equals("Overview")) overview(meeting); else if (tab.equals("Transcript")||tab.equals("Action items")||tab.equals("Decisions")) passages(meeting);
        else if(tab.equals("Participants")) participants(); else if(tab.equals("Presentation")) slideMatches();
        else if(tab.equals("Analysis")) analysis(meeting); else if(tab.equals("Audio")) audio(meeting); else exports(meeting);
    }
    private void overview(MeetingRepository.Meeting meeting) {
        if(meeting.transcriptMissing) ui.add(body,ui.notice("Historical report","This saved report did not include a full transcript. The original recording is available. Run local analysis to transcribe it; publishing changes to the account remains your choice.",true),16);
        if(!meeting.completed) {
            if(!MeetingService.busy||!meeting.id.equals(MeetingService.progress.meetingId)) {
                Button analyse=ui.button(meeting.reportExists?"Resume analysis":"Analyse meeting",true,this::analyse);
                ui.enabled(analyse,!locked()&&metadataLoaded&&modelReady()&&meeting.audioExists); ui.add(body,analyse,12);
                if(!modelReady()) ui.add(body,ui.button("Set up local analysis",false,this::settings),12);
                ui.add(body,ui.text(meeting.reportExists?"Continue saved work. Changed settings or an app upgrade may require a fresh transcription.":"Your recording is saved. Analyse it when you’re ready.",14,ui.muted,false),20);
            }
        } else {
            LinearLayout card=ui.card(); ui.add(card,ui.text("At a glance",19,ui.text,true),16); LinearLayout stats=ui.row();
            stat(stats,"Duration",MeetingRepository.stamp(meeting.duration)); stat(stats,"Actions",String.valueOf(eventCount("action_item"))); stat(stats,"Decisions",String.valueOf(eventCount("decision"))); ui.add(card,stats,0); ui.add(body,card,18);
            ui.add(body,ui.text("Actions and decisions are candidates. Listen to the source before acting on them.",13,ui.muted,false),14);
            Button update=ui.button("Update analysis",false,this::analyse); ui.enabled(update,!locked()&&metadataLoaded&&modelReady()&&meeting.audioExists); ui.add(body,update,14);
        }
        LinearLayout vocabulary=ui.card(); ui.add(vocabulary,ui.text("Vocabulary",18,ui.text,true),8);
        String saved=selectedMetadata.optString("vocabulary");
        ui.add(vocabulary,ui.text(saved.isEmpty()?"Optional names and technical terms. You can leave this empty.":saved,14,ui.muted,false),12);
        JSONArray terms=selectedReport==null?null:selectedReport.optJSONArray("vocabulary_suggestions");
        if(terms!=null&&terms.length()>0) {
            ui.add(vocabulary,ui.text("Suggested from your transcript",12,ui.muted,false),6);
            List<String> words=new ArrayList<>(); for(int i=0;i<terms.length();i++) words.add(terms.optString(i));
            ui.add(vocabulary,ui.text(String.join(", ",words),14,ui.text,false),12);
        }
        Button edit=ui.button("Edit vocabulary",false,() -> editVocabulary(true)); ui.enabled(edit,!locked()&&metadataLoaded); ui.add(vocabulary,edit,0); ui.add(body,vocabulary,14);
        boolean attached=repository.file(meeting.id,"presentation.pptx").isFile();
        Button ppt=ui.button(attached?"View presentation":"Add PPT (optional)",false,() -> { if(attached) presentation(); else picker(13,"application/vnd.openxmlformats-officedocument.presentationml.presentation"); }); ui.enabled(ppt,!locked()); ui.add(body,ppt,12);
        if(meeting.completed) ui.add(body,ui.button("Read transcript",false,() -> { tab="Transcript"; query=""; page=0; render(); }),0);
    }
    private int eventCount(String type) {
        JSONArray events=selectedReport==null?null:selectedReport.optJSONArray("events"); int count=0;
        if(events!=null) for(int i=0;i<events.length();i++) if(type.equals(events.optJSONObject(i).optString("event_type"))) count++;
        return count;
    }
    private void analysis(MeetingRepository.Meeting meeting) {
        ui.add(body,ui.text("Analysis & accuracy",20,ui.text,true),12);
        ui.add(body,ui.text("Accuracy has not been measured for this meeting.",16,ui.text,true),8);
        ui.add(body,ui.text("Review the transcript and important candidates against the recording. No reference transcript is available to calculate accuracy.",14,ui.muted,false),20);
        ui.add(body,ui.text("Speakers & influence",18,ui.text,true),8);
        JSONArray scores=selectedReport==null?null:selectedReport.optJSONArray("influence");
        if(scores==null||scores.length()==0) ui.add(body,ui.text("Analyse this meeting to identify speakers. Unclear or overlapping speech stays unassigned.",14,ui.muted,false),14);
        else {
            ui.add(body,ui.text("Scores estimate candidate decision-linked contributions. They are not accuracy percentages. Prototype weights need human validation.",14,ui.muted,false),14);
            for(int i=0;i<scores.length();i++) {
                JSONObject score=scores.optJSONObject(i); String speaker=score.optString("participant"); LinearLayout card=ui.card();
                ui.add(card,ui.text(speakerLabel(speaker)+" · "+String.format(Locale.ROOT,"%.3f",score.optDouble("influence_score")),18,ui.text,true),8);
                JSONObject raw=score.optJSONObject("raw_features"); StringBuilder detail=new StringBuilder();
                if(raw!=null) for(String feature:MeetingAnalysis.FEATURES) detail.append(feature.replace('_',' ')).append(": ").append(raw.optInt(feature)).append("\n");
                ui.add(card,ui.text(detail.toString().trim(),13,ui.muted,false),10);
                JSONArray sources=score.optJSONArray("supporting_events");
                if(sources==null||sources.length()==0) ui.add(card,ui.text("Insufficient decision-linked evidence.",13,ui.muted,false),0);
                else { JSONArray events=selectedReport.optJSONArray("events"); Set<String> ids=new HashSet<>(); for(int n=0;n<sources.length();n++) ids.add(sources.optString(n));
                    if(events!=null) for(int n=0;n<events.length();n++) { JSONObject event=events.optJSONObject(n); if(!ids.contains(event.optString("event_id"))) continue;
                        double start=event.optDouble("start"); Button evidence=ui.button(event.optString("event_id")+" · "+event.optString("event_type")+" · "+MeetingRepository.stamp(start),false,() -> play(start)); ui.enabled(evidence,!locked()); ui.add(card,evidence,6);
                        ui.add(card,ui.text(event.optString("text"),14,ui.text,false),8);
                    }
                }
                ui.add(body,card,14);
            }
        }
        JSONObject diarization=selectedReport==null?null:selectedReport.optJSONObject("diarization");
        if(diarization!=null&&!diarization.isNull("error")) ui.add(body,ui.text(diarization.optString("error"),14,ui.muted,false),12);
        ui.add(body,ui.text("Language: "+MeetingRepository.language(meeting.language),14,ui.muted,false),12);
        Button audio=ui.button("Listen to recording",false,() -> { tab="Audio"; render(); }); ui.enabled(audio,!locked()); ui.add(body,audio,12);
    }
    private String speakerLabel(String id) { return MeetingRepository.speakerLabel(selectedMetadata,id); }
    private String speakerRole(String id) {
        JSONObject saved=selectedMetadata.optJSONObject("speaker_roles"); if(saved!=null&&!saved.optString(id).isEmpty()) return saved.optString(id);
        JSONArray participants=selectedReport==null?null:selectedReport.optJSONArray("participants");
        if(participants!=null) for(int i=0;i<participants.length();i++) { JSONObject participant=participants.optJSONObject(i); if(id.equals(participant.optString("speaker"))) {
            JSONArray roles=participant.optJSONArray("roles"); List<String> names=new ArrayList<>(); if(roles!=null) for(int j=0;j<roles.length();j++) names.add(roles.optString(j)); return String.join(", ",names);
        } }
        return "";
    }
    private void participants() {
        ui.add(body,ui.text("Participants",20,ui.text,true),12);
        ui.add(body,ui.text("Names are yours to edit. Suggested roles describe observed contributions, not job titles. Speaker identities apply within this meeting.",14,ui.muted,false),14);
        JSONArray participants=selectedReport==null?null:selectedReport.optJSONArray("participants");
        if(participants==null||participants.length()==0) { empty("No identified participants","Run analysis; unclear speech remains unassigned."); return; }
        for(int i=0;i<participants.length();i++) {
            JSONObject participant=participants.optJSONObject(i); String id=participant.optString("speaker"); LinearLayout card=ui.card();
            ui.add(card,ui.text(speakerLabel(id),18,ui.text,true),8); ui.add(card,ui.text(speakerRole(id),14,ui.muted,false),8);
            ui.add(card,ui.text("Attributed speech: "+MeetingRepository.stamp(participant.optDouble("speaking_time_s")),13,ui.muted,false),12);
            Button edit=ui.button("Edit name & role",false,() -> editSpeaker(id)); ui.enabled(edit,!locked()&&metadataLoaded); ui.add(card,edit,0); ui.add(body,card,14);
        }
    }
    private void editSpeaker(String speaker) {
        if(locked()||!metadataLoaded) return; final String meeting=selectedId;
        EditText name=ui.input("Speaker name","Speaker name",false),role=ui.input("Meeting role","Meeting role",false);
        name.setFilters(new InputFilter[]{new InputFilter.LengthFilter(200)}); role.setFilters(new InputFilter[]{new InputFilter.LengthFilter(200)});
        name.setText(speakerLabel(speaker)); role.setText(speakerRole(speaker));
        LinearLayout holder=ui.column(); holder.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),0); ui.add(holder,name,12); ui.add(holder,role,12);
        new AlertDialog.Builder(this).setTitle("Edit participant").setView(holder).setNegativeButton("Cancel",null).setPositiveButton("Save",(dialog,which) -> {
            String savedName=name.getText().toString(),savedRole=role.getText().toString();
            io.execute(() -> {
                try { repository.speaker(meeting,speaker,savedName,savedRole); runOnUiThread(this::reload); }
                catch(Exception failure) { runOnUiThread(() -> { error=failure.getMessage(); render(); }); }
            });
        }).show();
    }
    private void slideMatches() {
        ui.add(body,ui.text("Presentation matches",20,ui.text,true),12);
        ui.add(body,ui.text("Spoken passages matched to native PPT text using TF-IDF. Similarity scores need review. Image-only slides have no text match.",14,ui.muted,false),14);
        JSONArray slides=selectedReport==null?null:selectedReport.optJSONArray("slides"),matches=selectedReport==null?null:selectedReport.optJSONArray("aligned_segments");
        if(slides==null||slides.length()==0) { empty("No analysed presentation","Attach a PPT from meeting options and run analysis again. Completed transcription is reused."); return; }
        for(int i=0;i<slides.length();i++) {
            JSONObject slide=slides.optJSONObject(i); int number=slide.optInt("slide_number"); LinearLayout card=ui.card();
            ui.add(card,ui.text("Slide "+number,18,ui.text,true),8); ui.add(card,ui.text(slide.optString("text").isEmpty()?"No native text":slide.optString("text"),15,ui.text,false),12);
            int count=0;
            if(matches!=null) for(int j=0;j<matches.length();j++) { JSONObject match=matches.optJSONObject(j); if(match.optInt("selected_slide",-1)!=number) continue;
                count++; double start=match.optDouble("start");
                Button evidence=ui.button(speakerLabel(match.optString("speaker","UNKNOWN"))+" · "+MeetingRepository.stamp(start)+" · "+String.format(Locale.ROOT,"%.2f",match.optDouble("score")),false,() -> play(start)); ui.enabled(evidence,!locked()); ui.add(card,evidence,6);
                ui.add(card,ui.text(match.optString("text"),14,ui.muted,false),8);
            }
            if(count==0) ui.add(card,ui.text("No clear spoken match.",13,ui.muted,false),0); ui.add(body,card,14);
        }
    }
    private void editVocabulary(boolean perMeeting) {
        final String id=selectedId;
        if(perMeeting&&(id==null||!metadataLoaded)||locked()) return;
        EditText value=ui.input("Names, acronyms, useful terms…","Vocabulary hints",true); value.setFilters(new InputFilter[]{new InputFilter.LengthFilter(1000)});
        value.setText(perMeeting?selectedMetadata.optString("vocabulary",preferences().getString("vocabulary","")):preferences().getString("vocabulary",""));
        LinearLayout holder=ui.column(); holder.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),0); ui.add(holder,value,8);
        ui.add(holder,ui.text("Optional. Suggestions are observed words, not corrections. Saved edits stay with this meeting.",13,ui.muted,false),8);
        if(perMeeting&&selectedReport!=null&&selectedReport.optJSONArray("vocabulary_suggestions")!=null) {
            Button use=ui.button("Use transcript suggestions",false,() -> {
                JSONArray terms=selectedReport.optJSONArray("vocabulary_suggestions"); LinkedHashSet<String> words=new LinkedHashSet<>();
                for(String term:value.getText().toString().split(",")) if(!term.trim().isEmpty()) words.add(term.trim());
                for(int i=0;i<terms.length();i++) words.add(terms.optString(i)); value.setText(String.join(", ",words));
            }); ui.add(holder,use,8);
        }
        new AlertDialog.Builder(this).setTitle("Vocabulary hints").setView(holder).setNegativeButton("Cancel",null).setPositiveButton("Save",(dialog,which) -> {
            String text=value.getText().toString();
            if(!perMeeting) { preferences().edit().putString("vocabulary",text).apply(); message("Hints saved for your next meeting."); }
            else io.execute(() -> { try { repository.vocabulary(id,text); runOnUiThread(() -> { message("Vocabulary saved."); reload(); }); } catch(Exception failure) { runOnUiThread(() -> { error=failure.getMessage(); render(); }); } });
        }).show();
    }
    private void presentation() {
        final String id=selectedId;
        io.execute(() -> {
            try {
                JSONArray slides=MeetingRepository.read(repository.file(id,"presentation.json")).getJSONArray("slides"); StringBuilder text=new StringBuilder("Attached slide text. View Presentation matches after analysis for linked speech.\n\n");
                for(int i=0;i<slides.length();i++) text.append("Slide ").append(i+1).append("\n").append(slides.optString(i).isEmpty()?"No native text":slides.optString(i)).append("\n\n");
                runOnUiThread(() -> { if(isDestroyed()) return; ScrollView scroll=new ScrollView(this); TextView content=ui.text(text.toString(),15,ui.text,false); content.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),ui.dp(20)); content.setTextIsSelectable(true); scroll.addView(content);
                    new AlertDialog.Builder(this).setTitle("Presentation").setView(scroll).setPositiveButton("Done",null).show(); });
            } catch(Exception failure) { runOnUiThread(() -> { error="Could not read the presentation."; render(); }); }
        });
    }
    private void meetingOptions() {
        new AlertDialog.Builder(this).setTitle("Meeting options").setItems(new String[]{"Listen to recording","Export meeting","Rename meeting","Add or replace PPT","Publish to account"},(dialog,which) -> {
            if(which==0) { tab="Audio"; render(); } else if(which==1) { tab="Export"; render(); } else if(which==2) rename(); else if(which==4) publishAccount(); else picker(13,"application/vnd.openxmlformats-officedocument.presentationml.presentation");
        }).show();
    }
    private void stat(LinearLayout row,String label,String value) {
        LinearLayout stat=ui.column(); TextView number=ui.text(value,24,ui.text,true); number.setMinHeight(ui.dp(40));
        number.setAutoSizeTextTypeUniformWithConfiguration(14,24,1,android.util.TypedValue.COMPLEX_UNIT_SP);
        ui.add(stat,number,8); ui.add(stat,ui.text(label,12,ui.muted,false),0); row.addView(stat,new LinearLayout.LayoutParams(0,-2,1));
    }
    private void analysisCard(MeetingRepository.Meeting meeting) {
        LinearLayout card=ui.card(); progressTitle=ui.text("Analysing locally",17,ui.text,true); ui.add(card,progressTitle,15);
        progressBar=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal); progressBar.setMax(100); progressBar.setProgressTintList(android.content.res.ColorStateList.valueOf(ui.accent));
        progressBar.setProgressBackgroundTintList(android.content.res.ColorStateList.valueOf(ui.border)); card.addView(progressBar,new LinearLayout.LayoutParams(-1,ui.dp(12))); ui.space(card,12);
        progressClock=ui.text("",14,ui.text,true); ui.add(card,progressClock,8); progressNote=ui.text("",13,ui.muted,false); ui.add(card,progressNote,16);
        pauseAnalysis=ui.button("Pause analysis",false,this::stopOperation); ui.add(card,pauseAnalysis,0); ui.add(body,card,16);
    }
    private void passages(MeetingRepository.Meeting meeting) {
        boolean candidates=!tab.equals("Transcript");
        ui.add(body,ui.text(tab.equals("Decisions")?"Decision table":tab.equals("Action items")?"Action items":"Transcript",20,ui.text,true),12);
        ui.add(body,ui.text(candidates?"Detected from your transcript. Listen to verify each item.":"Tap a timestamp to listen to the source.",13,ui.muted,false),14);
        if(!meeting.reportExists||selectedReport==null) { empty("No transcript yet","Analyse the recording to see your results."); return; }
        LinearLayout searchRow=ui.row(); searchRow.setBackground(ui.shape(ui.card,ui.border,12)); searchRow.setPadding(ui.dp(10),0,0,0);
        searchRow.addView(new Ui.Icon(this,"search",ui.muted),new LinearLayout.LayoutParams(ui.dp(22),ui.dp(22)));
        search=ui.input(candidates?"Search candidates…":"Search transcript words…","Search "+(candidates?"candidates":"transcript"),false);
        search.setBackgroundColor(android.graphics.Color.TRANSPARENT); search.setText(query); searchRow.addView(search,new LinearLayout.LayoutParams(0,-2,1));
        searchRow.addView(ui.iconButton("close","Clear search",() -> search.setText(""))); ui.add(body,searchRow,14);
        search.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s,int a,int c,int f) { }
            public void onTextChanged(CharSequence s,int a,int b,int c) { query=s.toString(); page=0; renderPassages(); }
            public void afterTextChanged(Editable text) { }
        });
        passageList=ui.column(); ui.add(body,passageList,0); renderPassages();
    }
    private static String normalize(String value) { return Normalizer.normalize(value,Normalizer.Form.NFKC).toLowerCase(Locale.ROOT).trim(); }
    private void renderPassages() {
        if(passageList==null||selectedReport==null) return; passageList.removeAllViews();
        boolean candidates=!tab.equals("Transcript"); JSONArray source=selectedReport.optJSONArray(candidates?"events":"transcript_segments");
        Map<String,JSONObject> tasks=ActionReviews.candidates(selectedReport);
        List<JSONObject> matches=new ArrayList<>(); String term=normalize(query);
        if(source!=null) for(int i=0;i<source.length();i++) {
            JSONObject item=source.optJSONObject(i); if(item==null||!normalize(item.optString("text")).contains(term)) continue;
            String type=item.optString("event_type");
            if(candidates && !type.equals(tab.equals("Decisions")?"decision":"action_item")) continue;
            matches.add(item);
        }
        maxPage=Math.max(0,(matches.size()-1)/20); page=Math.min(page,maxPage);
        if(!term.isEmpty()) ui.add(passageList,ui.text(matches.size()+" matches",13,ui.muted,false),12);
        if(matches.isEmpty()&&selectedReport.optJSONObject("processing")!=null&&selectedReport.optJSONObject("processing").optBoolean("legacy_transcript_missing")) {
            ui.add(passageList,ui.notice("Historical transcript unavailable","The imported report has no saved full transcript. Transcribe its original recording from Overview.",true),12);
        } else if(matches.isEmpty()) ui.add(passageList,ui.notice("No matches",term.isEmpty()?(candidates?"No candidate events were detected in the saved transcript.":"No speech was transcribed. Listen to the recording and check the language or model before trying again."):"Try a word or phrase used in this meeting.",false),12);
        for(int i=page*20;i<Math.min(matches.size(),(page+1)*20);i++) {
            JSONObject item=matches.get(i); LinearLayout card=ui.card(), heading=ui.row(); double seconds=item.optDouble("start");
            View play=ui.iconButton("play","Play evidence at "+MeetingRepository.stamp(seconds),() -> play(seconds)); play.setBackground(ui.touch(ui.dark?0xFF194C71:0xFFE6F1FB,0,24)); ui.enabled(play,!locked());
            heading.addView(play); TextView time=ui.text(MeetingRepository.stamp(seconds),12,ui.blue,true); time.setPadding(ui.dp(8),0,ui.dp(10),0);
            time.setMinHeight(ui.dp(48)); time.setGravity(Gravity.CENTER_VERTICAL); time.setContentDescription("Play timestamp "+MeetingRepository.stamp(seconds));
            time.setOnClickListener(view -> play(seconds)); ui.enabled(time,!locked()); heading.addView(time);
            if(candidates) heading.addView(ui.chip(candidateLabel(item.optString("event_type")),ui.warningText,ui.warning),new LinearLayout.LayoutParams(0,-2,1)); ui.add(card,heading,12);
            String speaker=item.optString("speaker","UNKNOWN"); String role=speakerRole(speaker);
            ui.add(card,ui.text(speakerLabel(speaker)+(role.isEmpty()?"":" · "+role),13,ui.muted,true),8);
            TextView content=ui.text(item.optString("text"),16,ui.text,false); content.setText(highlight(item.optString("text"),term)); content.setTextIsSelectable(true); ui.add(card,content,0);
            if(candidates) { Button evidence=ui.button("Play evidence",false,() -> play(seconds)); ui.enabled(evidence,!locked()); ui.space(card,12); ui.add(card,evidence,0); }
            if(candidates&&item.optString("event_type").equals("action_item")&&tasks.containsKey(item.optString("event_id"))) {
                JSONObject task=tasks.get(item.optString("event_id")),review=ActionReviews.active(selectedReport,task);
                String status=review==null?"Unreviewed · owner and due date unassigned":"Reviewed · "+review.optString("state")+" · Owner: "+(review.optString("owner").isEmpty()?"Unassigned":review.optString("owner"))+" · Due: "+(review.optString("due_date").isEmpty()?"Not set":review.optString("due_date"));
                ui.add(card,ui.text(status,13,ui.muted,false),12);
                Button edit=ui.button(review==null?"Review follow-up":"Edit follow-up",false,() -> editAction(task)); ui.enabled(edit,!locked()&&metadataLoaded); ui.add(card,edit,0);
            }
            ui.add(passageList,card,12);
        }
        if(matches.size()<=20) return;
        LinearLayout pager=ui.row(); Button previous=ui.button("Previous",false,() -> { if(page>0) { page--; renderPassages(); } });
        ui.enabled(previous,page>0); pager.addView(previous,new LinearLayout.LayoutParams(0,-2,1));
        pageLabel=ui.text("Page "+(page+1)+" of "+(maxPage+1),12,ui.muted,false); pageLabel.setGravity(Gravity.CENTER); pager.addView(pageLabel,new LinearLayout.LayoutParams(0,-2,1));
        Button next=ui.button("Next",false,() -> { if(page<maxPage) { page++; renderPassages(); } }); ui.enabled(next,page<maxPage); pager.addView(next,new LinearLayout.LayoutParams(0,-2,1)); ui.add(passageList,pager,12);
    }
    private void editAction(JSONObject action) {
        if(locked()||!metadataLoaded) return; final String id=selectedId;
        JSONObject review=ActionReviews.active(selectedReport,action);
        LinearLayout holder=ui.column(); holder.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),ui.dp(12));
        ui.add(holder,ui.text("Confirm this task against the recording. The speaker is not automatically its owner.",14,ui.muted,false),12);
        EditText owner=ui.input("Owner (optional)","Task owner",false),due=ui.input("YYYY-MM-DD (optional)","Task due date",false);
        owner.setFilters(new InputFilter[]{new InputFilter.LengthFilter(100)}); owner.setText(review==null?"":review.optString("owner"));
        due.setText(review==null?"":review.optString("due_date")); due.setFocusable(false);
        due.setOnClickListener(view -> {
            java.time.LocalDate current;
            try { current=java.time.LocalDate.parse(due.getText().toString()); } catch(Exception ignored) { current=java.time.LocalDate.now(); }
            new DatePickerDialog(this,(picker,year,month,day) -> due.setText(String.format(Locale.ROOT,"%04d-%02d-%02d",year,month+1,day)),current.getYear(),current.getMonthValue()-1,current.getDayOfMonth()).show();
        });
        ui.add(holder,ui.text("Task owner",13,ui.muted,true),4); ui.add(holder,owner,12);
        ui.add(holder,ui.text("Due date",13,ui.muted,true),4); ui.add(holder,due,8); ui.add(holder,ui.button("Clear due date",false,() -> due.setText("")),12);
        Spinner state=new Spinner(this); state.setContentDescription("Task status");
        String[] values={"open","done","dismissed"}; state.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,new String[]{"Open","Done","Dismissed candidate"}));
        state.setSelection(review==null?0:Math.max(0,Arrays.asList(values).indexOf(review.optString("state"))));
        ui.add(holder,ui.text("Task status",13,ui.muted,true),4); ui.add(holder,state,12);
        TextView issue=ui.text("",14,ui.warningText,false); ui.add(holder,issue,8);
        ScrollView scroll=new ScrollView(this); scroll.addView(holder);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Review follow-up").setView(scroll).setNegativeButton("Cancel",null).setPositiveButton("Save follow-up",null).create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
            if(locked()) { issue.setText("Wait for the current operation to finish."); return; }
            String name=owner.getText().toString(),date=due.getText().toString(),status=values[state.getSelectedItemPosition()];
            try { ActionReviews.make(action,name,date,status); } catch(Exception failure) { issue.setText(failure.getMessage()); return; }
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(false);
            io.execute(() -> {
                try { repository.reviewAction(id,action,name,date,status); runOnUiThread(() -> { dialog.dismiss(); message("Follow-up saved on this device"); reload(); }); }
                catch(Exception failure) { runOnUiThread(() -> { issue.setText(failure.getMessage()); dialog.getButton(AlertDialog.BUTTON_POSITIVE).setEnabled(true); }); }
            });
        })); dialog.show();
    }
    private CharSequence highlight(String text,String term) {
        SpannableString result=new SpannableString(text); String normalized=normalize(text);
        if(term.isEmpty()||normalized.length()!=text.length()) return result;
        int first=0; while((first=normalized.indexOf(term,first))>=0) { result.setSpan(new ForegroundColorSpan(ui.blue),first,first+term.length(),0); result.setSpan(new StyleSpan(android.graphics.Typeface.BOLD),first,first+term.length(),0); first+=term.length(); }
        return result;
    }
    private String candidateLabel(String type) { return "decision".equals(type)?"Decision":"action_item".equals(type)?"Action item":type.replace('_',' ')+" candidate"; }
    private void audio(MeetingRepository.Meeting meeting) {
        LinearLayout player=ui.card(); ui.add(player,ui.text("Saved recording",19,ui.text,true),8); ui.add(player,ui.text("Listen locally and check the transcript against the source.",14,ui.muted,false),20);
        audioButton=ui.button("Play recording",true,() -> { if(!locked()) playback.toggle(repository.file(selectedId,"audio.wav")); }); ui.enabled(audioButton,meeting.audioExists&&!locked()); ui.add(player,audioButton,10);
        audioStop=ui.button("Stop playback",false,() -> { playback.release(); updateAudio(); }); ui.add(player,audioStop,12);
        audioSeek=new SeekBar(this); audioSeek.setMax((int)Math.min(Integer.MAX_VALUE,meeting.duration*1000)); audioSeek.setProgressTintList(android.content.res.ColorStateList.valueOf(ui.accent)); audioSeek.setThumbTintList(android.content.res.ColorStateList.valueOf(ui.accent)); audioSeek.setContentDescription("Seek recording");
        audioSeek.setMinimumHeight(ui.dp(48)); ui.enabled(audioSeek,meeting.audioExists&&!locked()); audioSeek.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            public void onProgressChanged(SeekBar bar,int position,boolean user) { if(user) playback.seek(position); }
            public void onStartTrackingTouch(SeekBar bar) { }
            public void onStopTrackingTouch(SeekBar bar) { updateAudio(); }
        }); ui.add(player,audioSeek,4);
        audioClock=ui.text("",14,ui.muted,false); ui.add(player,audioClock,12); audioNote=ui.text("",13,ui.muted,false); ui.add(player,audioNote,0); ui.add(body,player,16);
        if(locked()) ui.add(body,ui.notice("Playback is temporarily unavailable","Pause analysis or finish recording before playing the source audio.",false),12);
    }
    private static void setText(TextView view,CharSequence value) { if(!TextUtils.equals(view.getText(),value)) view.setText(value); }
    private void updateAudio() {
        if(audioButton==null) return; setText(audioButton,playback.playing()?"Pause playback":"Play recording"); audioButton.setContentDescription(audioButton.getText());
        ui.enabled(audioStop,playback.active()&&!locked());
        MeetingRepository.Meeting meeting=meeting(); if(meeting==null) return;
        int duration=playback.duration()>0?playback.duration():(int)(meeting.duration*1000);
        if(audioSeek!=null&&!audioSeek.isPressed()) { audioSeek.setMax(duration); audioSeek.setProgress(playback.position()); }
        if(audioClock!=null) setText(audioClock,MeetingRepository.stamp(playback.position()/1000.0)+" / "+MeetingRepository.stamp(duration/1000.0));
        if(audioNote!=null) setText(audioNote,playback.error!=null?playback.error:"16 kHz · mono · WAV · stored on this device");
    }
    private void play(double seconds) {
        MeetingRepository.Meeting meeting=meeting(); if(meeting==null||!meeting.audioExists||locked()) return;
        playback.play(repository.file(selectedId,"audio.wav"),seconds); message("Playing saved recording at "+MeetingRepository.stamp(seconds));
    }
    private void exports(MeetingRepository.Meeting meeting) {
        ui.add(body,ui.text("Export meeting",20,ui.text,true),8); ui.add(body,ui.text("Choose where to save a copy. Your local originals remain on this device.",14,ui.muted,false),20);
        exportRow("document","Meeting report","Markdown · analysis and source transcript","meeting-report.md","text/markdown",meeting.reportExists);
        exportRow("document","Reviewed task calendar","Open tasks with confirmed due dates · ICS","task-calendar.ics","text/calendar",meeting.completed);
        Button advanced=ui.button("Export structured data (JSON)",false,() -> export("report-export.json","application/json")); ui.enabled(advanced,meeting.reportExists&&!locked()); ui.add(body,advanced,12);
        if(repository.file(meeting.id,"presentation.pptx").isFile()) exportRow("document","Presentation","Attached PPTX","presentation.pptx","application/vnd.openxmlformats-officedocument.presentationml.presentation",true);
        exportRow("wave","Saved recording","WAV · saved recording","audio.wav","audio/wav",meeting.audioExists);
        if(!meeting.completed&&meeting.reportExists) ui.add(body,ui.notice("Partial report","This export contains the completed transcription chunks. Resume analysis for the remaining audio.",true),12);
        if(locked()) ui.add(body,ui.text("Pause analysis or finish recording to export saved files.",13,ui.muted,false),0);
    }
    private void exportRow(String icon,String label,String description,String name,String type,boolean available) {
        View row=ui.action(icon,label,description,false,() -> export(name,type)); ui.enabled(row,available&&!locked()); ui.add(body,row,12);
    }
    private void modelSettings() {
        toolbar("Settings",this::back,false);
        ui.add(body,ui.action("document","Account & sync","Shared sign-in, profile and meeting history",false,this::account),18);
        if(AccountSession.signedIn(this)) {
            ui.add(body,ui.text("Shared profile",20,ui.text,true),8);
            ui.add(body,ui.text(AccountSession.preferences(this).getString("email","")+" · Edit or refresh your website profile in Account & sync.",14,ui.muted,false),16);
        } else {
            ui.add(body,ui.text("Device profile",20,ui.text,true),12);
            ui.add(body,ui.text("Saved on this device. Sign in through Account & sync for a shared website profile.",13,ui.muted,false),12);
            profileInput("Name","profile_name"); profileInput("Your role","profile_role"); profileInput("Organisation","profile_organization");
        }
        ui.add(body,ui.text("Local analysis",20,ui.text,true),14);
        LinearLayout model=ui.card(); ui.add(model,ui.text(modelReady()?"Speech model installed":"Set up local analysis",17,ui.text,true),8);
        ui.add(model,ui.text(modelReady()?preferences().getString("model_name","Whisper GGML model")+" · "+modelSize():"Import your downloaded speech model once to analyse meetings offline.",14,ui.muted,false),16);
        Button replace=ui.button(modelReady()?"Manage speech model":"Set up analysis",true,() -> picker(10,"*/*")); ui.enabled(replace,!locked()); ui.add(model,replace,0); ui.add(body,model,24);
        ui.add(body,ui.text("Default transcription",20,ui.text,true),12);
        Spinner language=spinner(new String[]{"Automatic (recommended)","English","Hindi"},"Transcription language"); language.setSelection(preferences().getInt("language",0));
        language.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            public void onItemSelected(AdapterView<?> parent,View view,int position,long id) { preferences().edit().putInt("language",position).apply(); }
            public void onNothingSelected(AdapterView<?> parent) { }
        }); ui.add(body,language,18);
        ui.add(body,ui.notice("Offline & private","Recording and analysis stay on this device. Account sync is optional and sends only meetings you explicitly publish to your configured server.",false),14);
        ui.add(body,ui.text("Number of participants (optional)",16,ui.text,true),8);
        String[] counts=new String[21]; counts[0]="Detect automatically"; for(int i=1;i<=20;i++) counts[i]=String.valueOf(i);
        Spinner speakers=spinner(counts,"Number of participants"); speakers.setSelection(Math.max(0,Math.min(20,preferences().getInt("speakers",0))));
        speakers.setOnItemSelectedListener(new AdapterView.OnItemSelectedListener() {
            public void onItemSelected(AdapterView<?> parent,View view,int position,long id) { preferences().edit().putInt("speakers",position).apply(); }
            public void onNothingSelected(AdapterView<?> parent) { }
        }); ui.add(body,speakers,18);
        ui.add(body,ui.notice("About analysis","Speaker models are included. Check names after changing the participant count. Influence uses candidate evidence; PPT matching uses slide text. Recognition accuracy remains unmeasured.",false),14);
        ui.add(body,ui.text("InfluenceIQ · Offline Meeting Intelligence",13,ui.muted,false),0);
    }
    private void profileInput(String label,String key) {
        EditText input=ui.input(label,label,false); input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(200)}); input.setText(preferences().getString(key,""));
        input.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s,int a,int c,int f) { }
            public void onTextChanged(CharSequence s,int a,int b,int c) { preferences().edit().putString(key,s.toString()).apply(); }
            public void afterTextChanged(Editable text) { }
        }); ui.add(body,input,12);
    }
    private Spinner spinner(String[] values,String description) {
        Spinner spinner=new Spinner(this); spinner.setContentDescription(description); spinner.setPadding(ui.dp(4),ui.dp(4),ui.dp(4),ui.dp(4)); spinner.setMinimumHeight(ui.dp(52)); spinner.setBackground(ui.shape(ui.card,ui.border,12));
        spinner.setAdapter(new ArrayAdapter<String>(this,android.R.layout.simple_spinner_dropdown_item,values) {
            public View getView(int position,View recycled,ViewGroup parent) {
                LinearLayout row=ui.row(); TextView label=ui.text(getItem(position),15,ui.text,false); label.setPadding(ui.dp(10),ui.dp(12),ui.dp(10),ui.dp(12));
                row.addView(label,new LinearLayout.LayoutParams(0,-2,1)); Ui.Icon arrow=new Ui.Icon(MainActivity.this,"chevron",ui.muted); arrow.setRotation(90);
                row.addView(arrow,new LinearLayout.LayoutParams(ui.dp(18),ui.dp(18))); row.setPadding(0,0,ui.dp(12),0); return row;
            }
            public View getDropDownView(int position,View recycled,ViewGroup parent) { TextView label=ui.text(getItem(position),16,ui.text,false); label.setBackgroundColor(ui.card); label.setPadding(ui.dp(16),ui.dp(16),ui.dp(16),ui.dp(16)); label.setMinHeight(ui.dp(48)); return label; }
        }); return spinner;
    }
    private String modelSize() { return String.format(Locale.getDefault(),"%.1f MB",new File(getFilesDir(),"model.bin").length()/1000000.0); }
    private void updateLive() {
        MeetingProgress progress=MeetingService.progress;
        if(timer!=null) { setText(timer,MeetingRepository.stamp(progress.recording()?progress.completedSeconds:0)); if(waveform!=null&&lastWaveSecond!=progress.completedSeconds) { waveform.push(progress.microphoneLevel); lastWaveSecond=progress.completedSeconds; } }
        if(progressBar!=null) {
            boolean waiting=progress.stage.equals("starting")||progress.stage.equals("loading"); progressBar.setIndeterminate(waiting); progressBar.setProgress(progress.percent());
            boolean speakers=progress.stage.equals("speakers"),fusion=progress.stage.equals("fusion");
            setText(progressTitle,progress.stage.equals("pausing")?"Pausing after the current stage…":speakers?"Identifying speakers locally…":fusion?"Matching slides & contributions…":waiting?"Preparing local transcription…":"Transcribing locally");
            if(speakers) { progressBar.setIndeterminate(NativeSpeakers.total==0); if(NativeSpeakers.total>0) progressBar.setProgress(100*NativeSpeakers.done/NativeSpeakers.total); }
            setText(progressClock,MeetingRepository.stamp(progress.completedSeconds)+" / "+MeetingRepository.stamp(progress.totalSeconds)+" · "+progress.percent()+"%");
            setText(progressNote,speakers?"Your transcript is saved. Pausing waits for the speaker stage to finish; the result is cached.":"Your completed transcript is saved automatically. Pause and return whenever you need.");
            ui.enabled(pauseAnalysis,!progress.stage.equals("pausing")); setText(pauseAnalysis,progress.stage.equals("pausing")?"Finishing current chunk…":"Pause analysis");
        }
        updateAudio();
    }
    private void requestRecording() {
        if(locked()) return; pendingRecord=true;
        ArrayList<String> permissions=new ArrayList<>();
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED) permissions.add(Manifest.permission.RECORD_AUDIO);
        if(Build.VERSION.SDK_INT>=33&&checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED) permissions.add(Manifest.permission.POST_NOTIFICATIONS);
        if(!permissions.isEmpty()) requestPermissions(permissions.toArray(new String[0]),1); else beginRecording();
    }
    public void onRequestPermissionsResult(int request,String[] permissions,int[] results) {
        super.onRequestPermissionsResult(request,permissions,results);
        if(request==1&&pendingRecord) {
            if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED) beginRecording();
            else { pendingRecord=false; error="Microphone permission is needed to record. You can still import a local recording."; render(); }
        }
    }
    private void beginRecording() {
        pendingRecord=false; if(locked()) return; playback.release(); pendingStart=true; error=null; screen="recording"; lastWaveSecond=-1;
        try { startForegroundService(new Intent(this,MeetingService.class).setAction("record")); render(); }
        catch(Exception failure) { pendingStart=false; error="Recording could not start: "+failure.getMessage(); screen="home"; render(); }
    }
    private void analyse() {
        MeetingRepository.Meeting meeting=meeting(); if(locked()||!metadataLoaded||!modelReady()||meeting==null||!meeting.audioExists) return;
        playback.release(); pendingStart=true; error=null;
        try {
            startForegroundService(new Intent(this,MeetingService.class).setAction("analyse").putExtra("meeting",selectedId)
                .putExtra("language",selectedMetadata.optString("analysis_language",languageCode())).putExtra("vocabulary",selectedMetadata.optString("vocabulary",preferences().getString("vocabulary",""))));
            render();
        } catch(Exception failure) { pendingStart=false; error="Analysis could not start: "+failure.getMessage(); render(); }
    }
    private void stopOperation() { if(MeetingService.busy) { startService(new Intent(this,MeetingService.class).setAction("stop")); updateLive(); } }
    private void picker(int request,String type) {
        if(locked()) return;
        startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT).setType(type).addCategory(Intent.CATEGORY_OPENABLE),request);
    }
    private void rename() {
        MeetingRepository.Meeting meeting=meeting(); if(meeting==null||locked()) return;
        EditText title=ui.input("Meeting title","Meeting title",false); title.setText(meeting.title); title.setFilters(new InputFilter[]{new InputFilter.LengthFilter(200)});
        LinearLayout holder=ui.column(); holder.setPadding(ui.dp(20),ui.dp(12),ui.dp(20),0); ui.add(holder,title,0);
        AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Rename meeting").setView(holder).setNegativeButton("Cancel",null).setPositiveButton("Save",null).create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(view -> {
            String value=title.getText().toString().trim(); if(value.isEmpty()) { title.setError("Enter a meeting title"); return; }
            dialog.dismiss(); io.execute(() -> { try { repository.rename(meeting.id,value); runOnUiThread(this::reload); } catch(Exception failure) { runOnUiThread(() -> { error=failure.getMessage(); render(); }); } });
        })); dialog.show();
    }
    private void publishAccount() {
        MeetingRepository.Meeting meeting=meeting(); if(meeting==null||locked()) return;
        if(!AccountSession.signedIn(this)) { account(); return; }
        if(!meeting.completed) { error="Complete local analysis before publishing to your account."; render(); return; }
        String id=meeting.id;
        new AlertDialog.Builder(this).setTitle("Publish to account?")
            .setMessage("Send this completed report, participant labels, extracted slide text and original recording to "+AccountSession.preferences(this).getString("email","")+" at "+AccountSession.preferences(this).getString("server","")+"? Existing device files are retained.")
            .setNegativeButton("Cancel",null).setPositiveButton("Publish",(dialog,which) -> { AccountSync.publish(this,id); render(); }).show();
    }
    private void export(String name,String type) {
        if(locked()||selectedId==null) return; final String id=selectedId; final MeetingRepository.Meeting meeting=meeting();
        io.execute(() -> {
            try {
                File source=name.equals("meeting-report.md")?repository.markdown(id,meeting.title):name.equals("report-export.json")?repository.jsonExport(id):name.equals("task-calendar.ics")?repository.calendar(id,meeting.title):repository.file(id,name);
                if(!source.isFile()) throw new IOException("This export is not available yet");
                runOnUiThread(() -> { if(isDestroyed()) return; exportName=name;
                    startActivityForResult(new Intent(Intent.ACTION_CREATE_DOCUMENT).setType(type).addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE,"InfluenceIQ_"+id+"_"+name),11);
                });
            } catch(Exception failure) { runOnUiThread(() -> { error=failure.getMessage(); render(); }); }
        });
    }
    protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data); if(result!=RESULT_OK||data==null||data.getData()==null) return;
        if(request==10||request==12||request==11||request==13) {
            File source=request==11&&selectedId!=null&&exportName!=null?repository.file(selectedId,exportName):null;
            if(request==13&&screen.equals("detail")&&selectedId!=null) source=repository.file(selectedId,"presentation.pptx");
            LocalTransfers.start(this,data.getData(),request,source); render();
        }
    }
    private void message(String text) { Toast.makeText(this,text,Toast.LENGTH_SHORT).show(); }
}

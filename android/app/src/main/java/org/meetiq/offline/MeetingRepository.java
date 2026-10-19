package org.meetiq.offline;

import org.json.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.*;

/** Reads existing meeting folders. Confined to the activity's single I/O worker. */
final class MeetingRepository {
    static final class Meeting {
        final String id, title, language, problem;
        final boolean audioExists, reportExists, completed, transcriptMissing;
        final double duration;
        final int passageCount, eventCount;
        final long audioBytes, reportBytes, reportModified, metadataBytes, metadataModified;
        Meeting(String id, String title, File audio, File report, File metadata, JSONObject data, String problem) {
            this.id=id; this.title=title; this.problem=problem;
            audioBytes=audio.length(); reportBytes=report.length(); reportModified=report.lastModified();
            metadataBytes=metadata.length(); metadataModified=metadata.lastModified();
            audioExists=audio.isFile() && audioBytes > 44; reportExists=data != null;
            completed=data != null && data.optBoolean("completed");
            transcriptMissing=data!=null && data.optJSONObject("processing")!=null && data.optJSONObject("processing").optBoolean("legacy_transcript_missing");
            duration=data == null ? Math.max(0, (audioBytes-44)/32000.0) : data.optDouble("duration", 0);
            language=data == null ? "auto" : data.optString("language", "auto");
            passageCount=data == null ? 0 : data.optJSONArray("transcript_segments") == null ? 0 : data.optJSONArray("transcript_segments").length();
            eventCount=data == null ? 0 : data.optJSONArray("events") == null ? 0 : data.optJSONArray("events").length();
        }
        String date() { return new SimpleDateFormat("MMM d, yyyy · h:mm a", Locale.getDefault()).format(new Date(Long.parseLong(id))); }
        String status() {
            if (MeetingService.busy && id.equals(MeetingService.progress.meetingId)) return MeetingService.progress.recording() ? "Recording" : "Analysing";
            if(transcriptMissing) return "Historical report";
            return completed ? (passageCount==0?"No speech found":"Transcript ready") : reportExists ? "Partial" : "Recorded";
        }
    }

    private final File files;
    private final Map<String,Meeting> summaries = new HashMap<>();
    private String loadedId;
    private long loadedModified, loadedBytes;
    private JSONObject loadedReport;
    MeetingRepository(File files) { this.files=files; }
    File file(String id, String name) {
        if (id == null || !id.matches("[0-9]{1,19}")) throw new IllegalArgumentException("Invalid meeting");
        return new File(files, "meetings/"+id+"/"+name);
    }
    static JSONObject read(File file) throws Exception {
        return new JSONObject(new String(Files.readAllBytes(file.toPath()), StandardCharsets.UTF_8));
    }
    List<Meeting> list() {
        String[] ids = new File(files,"meetings").list((directory, name) -> {
            try { return name.matches("[0-9]{1,19}") && Long.parseLong(name) >= 0 && new File(directory,name).isDirectory(); }
            catch (NumberFormatException error) { return false; }
        });
        if (ids == null) ids=new String[0];
        Arrays.sort(ids, (a,b) -> Long.compare(Long.parseLong(b),Long.parseLong(a)));
        List<Meeting> result=new ArrayList<>();
        for (String id:ids) {
            File audio=file(id,"audio.wav"), report=file(id,"report.json"), metadata=file(id,"metadata.json");
            Meeting previous=summaries.get(id);
            if (previous != null && previous.audioBytes==audio.length() && previous.reportBytes==report.length()
                && previous.reportModified==report.lastModified() && previous.metadataModified==metadata.lastModified()
                && previous.metadataBytes==metadata.length()) { result.add(previous); continue; }
            String title="Meeting · "+new SimpleDateFormat("MMM d, h:mm a",Locale.getDefault()).format(new Date(Long.parseLong(id)));
            try { String saved=read(metadata).optString("title").trim(); if (!saved.isEmpty()) title=saved; } catch (Exception ignored) { }
            JSONObject data=null; String problem=null;
            if (report.exists()) {
                try { data=report(id); } catch (Exception error) { problem="This report could not be read. The original recording is retained."; }
            }
            Meeting meeting=new Meeting(id,title,audio,report,metadata,data,problem);
            summaries.put(id,meeting); result.add(meeting);
        }
        summaries.keySet().retainAll(Arrays.asList(ids));
        return result;
    }
    JSONObject report(String id) throws Exception {
        File source=file(id,"report.json");
        if (!id.equals(loadedId) || loadedModified!=source.lastModified() || loadedBytes!=source.length() || loadedReport==null) {
            loadedReport=read(source); loadedId=id; loadedModified=source.lastModified(); loadedBytes=source.length();
        }
        JSONObject local=metadata(id).optJSONObject("action_reviews");
        if(local!=null) {
            JSONObject combined=loadedReport.optJSONObject("action_reviews"); if(combined==null) combined=new JSONObject();
            Iterator<String> keys=local.keys(); while(keys.hasNext()) { String key=keys.next(); combined.put(key,local.get(key)); }
            loadedReport.put("action_reviews",combined);
        }
        return loadedReport;
    }
    void rename(String id,String title) throws Exception {
        String value=title.trim(); if (value.isEmpty() || value.length()>200) throw new IOException("Enter a title of 1–200 characters");
        File metadata=file(id,"metadata.json"); JSONObject existing;
        try { existing=read(metadata); } catch (Exception error) { existing=new JSONObject(); }
        MeetingService.atomic(metadata,existing.put("title",value));
        summaries.remove(id);
    }
    JSONObject metadata(String id) {
        try { return read(file(id,"metadata.json")); } catch(Exception ignored) { return new JSONObject(); }
    }
    void vocabulary(String id,String value) throws Exception {
        if(value.length()>1000) throw new IOException("Use up to 1,000 characters");
        MeetingService.atomic(file(id,"metadata.json"),metadata(id).put("vocabulary",value.trim())); summaries.remove(id);
    }
    void speaker(String id,String speaker,String name,String role) throws Exception {
        if(!speaker.matches("SPEAKER_[0-9]{2}")) throw new IOException("Select an identified participant");
        if(name.length()>200||role.length()>200) throw new IOException("Use up to 200 characters");
        JSONObject meta=metadata(id),names=meta.optJSONObject("speaker_names"),roles=meta.optJSONObject("speaker_roles");
        if(names==null) names=new JSONObject(); if(roles==null) roles=new JSONObject();
        names.put(speaker,name.trim().replaceAll("[\\r\\n]"," ")); roles.put(speaker,role.trim().replaceAll("[\\r\\n]"," "));
        MeetingService.atomic(file(id,"metadata.json"),meta.put("speaker_names",names).put("speaker_roles",roles)); summaries.remove(id);
    }
    void reviewAction(String id,JSONObject original,String owner,String due,String state) throws Exception {
        JSONObject action=ActionReviews.candidates(report(id)).get(original.optString("event_id"));
        if(action==null||!action.optString("text").equals(original.optString("text"))||!Objects.equals(ActionReviews.start(action),ActionReviews.start(original)))
            throw new IOException("This report changed. Reopen the task before saving.");
        JSONObject value=ActionReviews.make(action,owner,due,state),meta=metadata(id),reviews=meta.optJSONObject("action_reviews");
        if(reviews==null) reviews=new JSONObject();
        if(!reviews.has(action.getString("event_id"))&&reviews.length()>=5000) throw new IOException("This meeting has reached the follow-up review limit");
        reviews.put(action.getString("event_id"),value); MeetingService.atomic(file(id,"metadata.json"),meta.put("action_reviews",reviews));
        summaries.remove(id);
    }
    File calendar(String id,String title) throws Exception {
        File destination=file(id,"task-calendar.ics");
        String value=ActionReviews.calendar(report(id),title,metadata(id).optString("remote_id",id));
        Files.write(destination.toPath(),value.getBytes(StandardCharsets.UTF_8)); return destination;
    }
    static String speakerLabel(JSONObject metadata,String speaker) {
        JSONObject names=metadata.optJSONObject("speaker_names"); String name=names==null?"":names.optString(speaker).trim();
        return name.isEmpty()?(speaker.equals("UNKNOWN")?"Unassigned speaker":speaker.replace("SPEAKER_","Speaker ")):name;
    }
    File jsonExport(String id) throws Exception {
        JSONObject meta=metadata(id),data=new JSONObject(report(id).toString()).put("metadata",meta);
        for(String key:new String[]{"transcript_segments","events","decisions","participants","influence","aligned_segments"}) {
            JSONArray items=data.optJSONArray(key); if(items==null) continue;
            for(int i=0;i<items.length();i++) { JSONObject item=items.optJSONObject(i); String speaker=item.optString("speaker",item.optString("participant","UNKNOWN"));
                item.put("display_name",speakerLabel(meta,speaker)); JSONObject roles=meta.optJSONObject("speaker_roles");
                if(roles!=null&&!roles.optString(speaker).isEmpty()) item.put("display_role",roles.optString(speaker));
            }
        }
        if(file(id,"presentation.json").isFile()) data.put("presentation",read(file(id,"presentation.json")));
        File destination=file(id,"report-export.json"); MeetingService.atomic(destination,data); return destination;
    }
    File markdown(String id,String title) throws Exception {
        JSONObject report=report(id);
        JSONObject meta=metadata(id);
        StringBuilder text=new StringBuilder("# "+title+"\n\nOffline extractive analysis; review against the recording. Recognition accuracy is unmeasured.\n");
        if (!report.optBoolean("completed")) text.append("\nPartial transcript — analysis is incomplete.\n");
        text.append("\n## Event candidates\n\n");
        String vocabulary=metadata(id).optString("vocabulary");
        if(!vocabulary.isEmpty()) text.append("Vocabulary: ").append(vocabulary).append("\n\n");
        if(file(id,"presentation.pptx").isFile()) text.append("Presentation attached. Fusion uses native slide text (TF-IDF), not visual encoding.\n\n");
        JSONArray events=report.optJSONArray("events");
        if (events != null) for (int i=0;i<events.length();i++) {
            JSONObject item=events.getJSONObject(i);
            text.append("- ").append(item.optString("event_type")).append(" [").append(stamp(item.optDouble("start")))
                .append("] ").append(speakerLabel(meta,item.optString("speaker","UNKNOWN"))).append(": ").append(item.optString("text")).append("\n");
        }
        text.append("\n## Reviewed follow-ups\n\n");
        for(JSONObject action:ActionReviews.candidates(report).values()) {
            JSONObject review=ActionReviews.active(report,action); if(review==null) continue;
            text.append("- ").append(action.optString("text")).append("; status: ").append(review.optString("state"))
                .append("; owner: ").append(review.optString("owner")).append("; due: ").append(review.optString("due_date")).append("\n");
        }
        text.append("\n## Participants and influence\n\nScores are unvalidated weighted candidate contributions, not accuracy or causal influence.\n\n");
        JSONArray scores=report.optJSONArray("influence");
        if(scores!=null) for(int i=0;i<scores.length();i++) {
            JSONObject score=scores.getJSONObject(i); String speaker=score.optString("participant");
            text.append("- ").append(speakerLabel(meta,speaker)).append(": ").append(score.optDouble("influence_score"))
                .append("; source events ").append(score.optJSONArray("supporting_events")).append("; raw features ").append(score.optJSONObject("raw_features")).append("\n");
        }
        text.append("\n## Presentation matches\n\n"); JSONArray matches=report.optJSONArray("aligned_segments");
        if(matches!=null) for(int i=0;i<matches.length();i++) { JSONObject match=matches.optJSONObject(i); if(match.isNull("selected_slide")) continue;
            text.append("- Slide ").append(match.optInt("selected_slide")).append(" [").append(stamp(match.optDouble("start"))).append("] ")
                .append(speakerLabel(meta,match.optString("speaker","UNKNOWN"))).append("; similarity ").append(match.optDouble("score")).append(": ").append(match.optString("text")).append("\n");
        }
        text.append("\n## Full transcript\n\n");
        JSONArray segments=report.optJSONArray("transcript_segments");
        if (segments != null) for (int i=0;i<segments.length();i++) {
            JSONObject item=segments.getJSONObject(i);
            text.append("[").append(stamp(item.optDouble("start"))).append("] ")
                .append(speakerLabel(meta,item.optString("speaker","UNKNOWN")));
            JSONObject roles=meta.optJSONObject("speaker_roles"); String role=roles==null?"":roles.optString(item.optString("speaker","UNKNOWN"));
            if(!role.isEmpty()) text.append(" ("+role+")"); text.append(": ").append(item.optString("text")).append("\n\n");
        }
        File destination=file(id,"meeting-report.md");
        Files.write(destination.toPath(),text.toString().getBytes(StandardCharsets.UTF_8)); return destination;
    }
    static String stamp(double seconds) {
        long value=(long)Math.max(0,seconds);
        return String.format(Locale.ROOT,"%02d:%02d:%02d",value/3600,value/60%60,value%60);
    }
    static String language(String code) { return "hi".equals(code) ? "Hindi" : "en".equals(code) ? "English" : "Automatic detection"; }
}

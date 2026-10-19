package org.meetiq.offline;

import org.json.*;
import java.util.*;
import java.io.*;
import java.nio.file.Files;
import java.nio.charset.StandardCharsets;

/** Runs with Android's real org.json/regex runtime through app_process. */
public final class MeetingAnalysisProbe {
    static void check(boolean condition,String message) { if(!condition) throw new AssertionError(message); }
    static JSONObject segment(int id,double start,double end,String speaker,String text) throws Exception {
        return new JSONObject().put("segment_id",id).put("start",start).put("end",end).put("speaker",speaker).put("text",text);
    }
    public static void main(String[] arguments) throws Exception {
        SlideIndex index=new SlideIndex(Arrays.asList("Project budget is 500 dollars","Latency reduced to 50 milliseconds"));
        check(index.scores("budget 500")[0]>index.scores("budget 500")[1],"Wrong slide");
        check(index.scores("unrelated")[0]==0,"Unrelated match");
        JSONArray segments=new JSONArray().put(segment(1,0,2,"SPEAKER_00","We should reduce project latency"))
            .put(segment(2,3,5,"SPEAKER_01","The latency data shows 50 milliseconds"))
            .put(segment(3,6,8,"SPEAKER_01","We agreed to reduce latency to 50 milliseconds"))
            .put(segment(4,9,11,"UNKNOWN","We agreed to reduce the budget"))
            .put(segment(5,12,14,"SPEAKER_02","Hello everyone"));
        JSONArray events=new JSONArray();
        for(int i=0;i<4;i++) { JSONObject copy=new JSONObject(segments.getJSONObject(i).toString()); copy.put("source_segment_id",i+1).put("event_type",new String[]{"proposal","evidence","decision","decision"}[i]); events.put(copy); }
        JSONObject result=MeetingAnalysis.analyse(new JSONObject().put("transcript_segments",segments),events,new JSONArray().put("Project budget 500 dollars").put("Latency 50 milliseconds"));
        check(result.getJSONArray("participants").length()==3,"Unknown participant fabricated");
        check(result.getJSONArray("decisions").getJSONObject(0).getJSONArray("supporting_events").length()==3,"Candidate chain absent");
        check(result.getJSONArray("decisions").getJSONObject(1).getJSONArray("supporting_events").length()==1,"Unrelated topic linked through a generic verb");
        check(result.getJSONArray("influence").getJSONObject(0).getDouble("influence_score")>0,"No influence score");
        check(result.getJSONArray("influence").getJSONObject(2).getDouble("influence_score")==0,"Unobserved contribution fabricated");
        check(result.getJSONArray("aligned_segments").getJSONObject(0).getInt("selected_slide")==2,"Fusion missing");
        JSONObject zero=MeetingAnalysis.analyse(new JSONObject().put("transcript_segments",segments),new JSONArray(),new JSONArray());
        for(int i=0;i<zero.getJSONArray("influence").length();i++) check(zero.getJSONArray("influence").getJSONObject(i).getDouble("influence_score")==0,"Zero evidence mishandled");
        List<SpeakerAttribution.Turn> turns=Arrays.asList(new SpeakerAttribution.Turn(0,2,"A"),new SpeakerAttribution.Turn(1,3,"B"));
        check(SpeakerAttribution.speaker(1,2,turns).equals("UNKNOWN"),"Overlap tie attributed");
        JSONArray words=new JSONArray().put(new JSONObject().put("start",0).put("end",1).put("text"," Hello"))
            .put(new JSONObject().put("start",1).put("end",2).put("text"," everyone"));
        JSONArray raw=new JSONArray().put(segment(1,0,2,"UNKNOWN","Hello everyone").put("words",words));
        JSONArray voice=new JSONArray().put(new JSONObject().put("start",0).put("end",1).put("cluster",4)).put(new JSONObject().put("start",1).put("end",2).put("cluster",2));
        JSONArray attributed=SpeakerReports.assign(raw,voice);
        check(attributed.length()==2,"Word attribution did not split at speaker change");
        check(raw.getJSONObject(0).getString("speaker").equals("UNKNOWN"),"Raw checkpoint mutated");
        File directory=new File(arguments[0]),meeting=new File(directory,"meetings/123"); meeting.mkdirs();
        MeetingService.atomic(new File(meeting,"report.json"),result.put("completed",true));
        MeetingService.atomic(new File(meeting,"metadata.json"),new JSONObject().put("preserve_this","keep"));
        MeetingRepository repository=new MeetingRepository(directory); repository.speaker("123","SPEAKER_00","Asha","Lead");
        check(repository.metadata("123").getString("preserve_this").equals("keep"),"Unrelated metadata lost");
        JSONObject exported=MeetingRepository.read(repository.jsonExport("123"));
        check(exported.getJSONArray("transcript_segments").getJSONObject(0).getString("display_name").equals("Asha"),"Export missing name");
        check(exported.getJSONArray("transcript_segments").getJSONObject(0).getString("display_role").equals("Lead"),"Export missing role");
        String markdown=new String(Files.readAllBytes(repository.markdown("123","Test meeting").toPath()),StandardCharsets.UTF_8);
        check(markdown.contains("Asha (Lead)")&&markdown.contains("## Participants and influence")&&markdown.contains("## Presentation matches"),"Incomplete meeting export");
        JSONObject web=new JSONObject().put("meeting_overview",new JSONObject().put("duration_s",15)).put("processing",new JSONObject().put("language","hi"))
            .put("transcript_segments",segments).put("event_timeline",events)
            .put("participants",new JSONArray().put(new JSONObject().put("speaker_id","SPEAKER_00").put("roles",new JSONArray().put("Contributor")).put("speaking_duration_s",2)))
            .put("slides",new JSONArray().put(new JSONObject().put("slide_id","slide_01").put("slide_number",1).put("text",new JSONArray().put("Budget").put("500"))))
            .put("aligned_segments",new JSONArray().put(new JSONObject().put("slide_id","slide_01").put("alignment_score",.8)));
        JSONObject offline=PortableReport.androidReport(web);
        check(offline.getDouble("duration")==15&&offline.getString("language").equals("hi")&&offline.getBoolean("completed"),"Portable meeting metadata missing");
        check(offline.getJSONArray("participants").getJSONObject(0).getString("speaker").equals("SPEAKER_00"),"Portable speaker alias missing");
        check(offline.getJSONArray("slides").getJSONObject(0).getString("text").contains("500"),"Portable slide text missing");
        check(offline.getJSONArray("aligned_segments").getJSONObject(0).getInt("selected_slide")==1,"Portable slide ID missing");
        check(offline.getJSONArray("events").length()==events.length()&&!web.has("completed"),"Portable conversion lost events or mutated the server report");
        File historical=new File(directory,"meetings/124"); historical.mkdirs();
        MeetingService.atomic(new File(historical,"report.json"),new JSONObject().put("completed",true).put("transcript_segments",new JSONArray())
            .put("processing",new JSONObject().put("legacy_transcript_missing",true)));
        check(repository.list().stream().anyMatch(entry -> entry.id.equals("124")&&entry.status().equals("Historical report")),"Missing legacy transcript mislabeled as silence");
        JSONObject action=new JSONObject().put("event_id","E_TASK").put("event_type","action_item").put("start",.5).put("end",1)
            .put("speaker","SPEAKER_00").put("text","कल report भेज देना।");
        File tasks=new File(directory,"meetings/125"); tasks.mkdirs();
        JSONObject taskReport=new JSONObject().put("completed",true).put("transcript_segments",new JSONArray()).put("events",new JSONArray().put(action));
        MeetingService.atomic(new File(tasks,"report.json"),taskReport);
        MeetingService.atomic(new File(tasks,"metadata.json"),new JSONObject().put("preserve_this","keep"));
        check(ActionReviews.active(taskReport,action)==null,"Unreviewed owner invented");
        repository.reviewAction("125",action,"रवि","2026-12-31","open");
        JSONObject reviewed=repository.report("125"),human=ActionReviews.active(reviewed,action);
        check(human!=null&&human.getString("owner").equals("रवि"),"Manual task owner missing");
        check(repository.metadata("125").getString("preserve_this").equals("keep"),"Task edit destroyed unrelated metadata");
        check(!MeetingRepository.read(new File(tasks,"report.json")).has("action_reviews"),"Source report changed during manual review");
        check(ActionReviews.active(reviewed,new JSONObject(action.toString()).put("text","Changed task"))==null,"Stale review applied to a new task");
        check(ActionReviews.active(reviewed,new JSONObject(action.toString()).put("start",.6))==null,"Stale review applied at a new timestamp");
        boolean invalid=false; try { ActionReviews.make(action,"","2026-02-30","open"); } catch(Exception expected) { invalid=true; }
        check(invalid,"Invalid calendar date accepted");
        String calendar=new String(Files.readAllBytes(repository.calendar("125","Planning").toPath()),StandardCharsets.UTF_8);
        check(calendar.contains("DTSTART;VALUE=DATE:20261231")&&calendar.contains("DTEND;VALUE=DATE:20270101"),"All-day deadline boundaries wrong");
        for(String line:calendar.split("\r\n")) check(line.getBytes(StandardCharsets.UTF_8).length<=75,"Calendar line exceeds UTF-8 limit");
        check(repository.jsonExport("125").isFile()&&repository.report("125").getJSONObject("action_reviews").has("E_TASK"),"Task missing from structured export");
        check(new String(Files.readAllBytes(repository.markdown("125","Planning").toPath()),StandardCharsets.UTF_8).contains("रवि"),"Task missing from Markdown");
        repository.reviewAction("125",action,"रवि","2026-12-31","done");
        boolean noCalendar=false; try { repository.calendar("125","Planning"); } catch(Exception expected) { noCalendar=true; }
        check(noCalendar,"Completed task exported as an open reminder");
        System.out.println("ANDROID_FOLLOWUPS_PASS: source-bound owner/date/status, metadata preservation, exports and safe calendar deadlines");
        System.out.println("ANDROID_PORTABLE_PASS: website report, speaker aliases, slide text, timestamp metadata and source preservation");
        System.out.println("ANDROID_ANALYSIS_PASS: fusion, lineage, influence, unknown abstention, zero evidence, word attribution");
        System.out.println("ANDROID_EXPORT_PASS: names, roles, unrelated metadata, influence, slides and full transcript");
        System.out.println(result.toString());
    }
}

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
        System.out.println("ANDROID_ANALYSIS_PASS: fusion, lineage, influence, unknown abstention, zero evidence, word attribution");
        System.out.println("ANDROID_EXPORT_PASS: names, roles, unrelated metadata, influence, slides and full transcript");
        System.out.println(result.toString());
    }
}

package org.meetiq.offline;

import org.json.*;
import java.util.*;

/** Extractive Android analysis. Every contribution points to a source event. */
final class MeetingAnalysis {
    static final String[] FEATURES={"proposal","evidence","objection","revision","decision","interaction","slide_grounding"};
    static final double[] WEIGHTS={.15,.20,.15,.20,.15,.05,.10};
    static String role(String type) {
        switch(type) {
            case "proposal": return "Proposer";
            case "evidence": return "Evidence provider";
            case "objection": case "disagreement": return "Challenger";
            case "revision": case "correction": return "Reviser";
            case "decision": return "Decision contributor";
            case "action_item": return "Task contributor";
            case "question": return "Questioner";
            default: return "Contributor";
        }
    }
    private static int feature(String type) {
        switch(type) {
            case "proposal": return 0; case "evidence": return 1;
            case "objection": case "disagreement": return 2; case "revision": case "correction": return 3;
            case "decision": return 4; default: return -1;
        }
    }
    static JSONObject analyse(JSONObject report,JSONArray events,JSONArray slideTexts) throws Exception {
        JSONArray segments=report.getJSONArray("transcript_segments"), slides=new JSONArray(), aligned=new JSONArray();
        List<String> texts=new ArrayList<>();
        for(int i=0;i<slideTexts.length();i++) {
            String text=slideTexts.optString(i); texts.add(text);
            slides.put(new JSONObject().put("slide_number",i+1).put("slide_id","slide_"+(i+1)).put("text",text));
        }
        SlideIndex index=new SlideIndex(texts);
        Map<Integer,Integer> selected=new HashMap<>(); Map<Integer,Double> selectedScores=new HashMap<>();
        for(int i=0;i<segments.length();i++) {
            JSONObject segment=segments.getJSONObject(i); double[] scores=index.scores(segment.optString("text"));
            int best=-1; double maximum=0,second=0;
            for(int j=0;j<scores.length;j++) if(scores[j]>maximum) { second=maximum; maximum=scores[j]; best=j; } else second=Math.max(second,scores[j]);
            boolean accepted=best>=0 && maximum>=.15 && maximum-second>=.05;
            JSONArray candidates=new JSONArray();
            List<Integer> ranked=new ArrayList<>(); for(int j=0;j<scores.length;j++) if(scores[j]>0) ranked.add(j);
            ranked.sort((a,b) -> Double.compare(scores[b],scores[a]));
            for(int j=0;j<Math.min(3,ranked.size());j++) { int n=ranked.get(j); candidates.put(new JSONObject().put("slide_number",n+1).put("score",scores[n])); }
            JSONObject match=new JSONObject().put("segment_id",segment.getInt("segment_id")).put("text",segment.optString("text"))
                .put("speaker",segment.optString("speaker","UNKNOWN")).put("start",segment.optDouble("start"))
                .put("selected_slide",accepted?best+1:JSONObject.NULL).put("score",maximum).put("candidates",candidates)
                .put("requires_review",true);
            aligned.put(match);
            if(accepted) { selected.put(segment.getInt("segment_id"),best+1); selectedScores.put(segment.getInt("segment_id"),maximum); }
        }
        Map<String,double[]> raw=new LinkedHashMap<>(); Map<String,Double> speaking=new LinkedHashMap<>();
        Map<String,Set<String>> roles=new LinkedHashMap<>(), evidence=new LinkedHashMap<>();
        for(int i=0;i<segments.length();i++) {
            JSONObject seg=segments.getJSONObject(i); String speaker=seg.optString("speaker","UNKNOWN"); if(speaker.equals("UNKNOWN")) continue;
            raw.putIfAbsent(speaker,new double[7]); roles.putIfAbsent(speaker,new LinkedHashSet<>()); evidence.putIfAbsent(speaker,new LinkedHashSet<>());
            speaking.put(speaker,speaking.getOrDefault(speaker,0.0)+Math.max(0,seg.optDouble("end")-seg.optDouble("start")));
        }
        Map<String,JSONObject> byId=new LinkedHashMap<>(); Map<String,Set<String>> decisionsByEvent=new LinkedHashMap<>();
        JSONArray decisions=new JSONArray(), interactions=new JSONArray();
        for(int i=0;i<events.length();i++) {
            JSONObject event=events.getJSONObject(i); String id="E"+(i+1),speaker=event.optString("speaker","UNKNOWN");
            event.put("event_id",id); byId.put(id,event);
            if(selected.containsKey(event.getInt("source_segment_id"))) event.put("slide_number",selected.get(event.getInt("source_segment_id"))).put("slide_score",selectedScores.get(event.getInt("source_segment_id")));
            if(roles.containsKey(speaker)) roles.get(speaker).add(role(event.optString("event_type")));
            if(!event.optString("event_type").equals("decision")) continue;
            String decisionId="D"+(decisions.length()+1); JSONArray linked=new JSONArray();
            // Candidate lineage requires preceding, nearby, lexically related evidence.
            // This is a documented Android approximation, not causal attribution.
            for(int j=0;j<=i;j++) {
                JSONObject earlier=events.getJSONObject(j); double gap=event.optDouble("start")-earlier.optDouble("start");
                if(feature(earlier.optString("event_type"))<0 || gap<0 || gap>120) continue;
                if(j!=i && (!SlideIndex.related(earlier.optString("text"),event.optString("text")) || earlier.optString("event_type").equals("decision"))) continue;
                String earlierId="E"+(j+1); linked.put(earlierId);
                decisionsByEvent.computeIfAbsent(earlierId,key -> new LinkedHashSet<>()).add(decisionId);
            }
            decisions.put(new JSONObject().put("decision_id",decisionId).put("text",event.optString("text")).put("start",event.optDouble("start"))
                .put("speaker",speaker).put("supporting_events",linked).put("requires_review",true));
        }
        Set<String> counted=new HashSet<>();
        for(Map.Entry<String,Set<String>> linked:decisionsByEvent.entrySet()) {
            JSONObject event=byId.get(linked.getKey()); String speaker=event.optString("speaker","UNKNOWN");
            event.put("supporting_decisions",new JSONArray(linked.getValue()));
            if(!raw.containsKey(speaker)) continue;
            int f=feature(event.optString("event_type"));
            // Multiple rule labels on one passage must not duplicate one contribution.
            if(f>=0&&counted.add(speaker+":"+event.getInt("source_segment_id")+":"+f)) raw.get(speaker)[f]++;
            if(event.has("slide_number")&&counted.add(speaker+":"+event.getInt("source_segment_id")+":slide")) raw.get(speaker)[6]++;
            evidence.get(speaker).add(linked.getKey());
        }
        // Adjacent different-speaker contributions with a shared decision and topic.
        for(int i=1;i<events.length();i++) {
            JSONObject a=events.getJSONObject(i-1),b=events.getJSONObject(i);
            String first=a.optString("speaker","UNKNOWN"),last=b.optString("speaker","UNKNOWN"),aid=a.optString("event_id"),bid=b.optString("event_id");
            if(!raw.containsKey(first)||!raw.containsKey(last)||first.equals(last)||b.optDouble("start")-a.optDouble("end")>15||a.getInt("source_segment_id")==b.getInt("source_segment_id")) continue;
            Set<String> shared=new LinkedHashSet<>(decisionsByEvent.getOrDefault(aid,Collections.emptySet())); shared.retainAll(decisionsByEvent.getOrDefault(bid,Collections.emptySet()));
            if(shared.isEmpty()||!SlideIndex.related(a.optString("text"),b.optString("text"))) continue;
            raw.get(first)[5]++; evidence.get(first).add(aid);
            interactions.put(new JSONObject().put("source",first).put("target",last).put("source_event",aid).put("target_event",bid).put("supporting_decisions",new JSONArray(shared)).put("requires_review",true));
        }
        double[] maxima=new double[7]; for(double[] vector:raw.values()) for(int i=0;i<7;i++) maxima[i]=Math.max(maxima[i],vector[i]);
        JSONArray participants=new JSONArray(); List<JSONObject> scores=new ArrayList<>();
        for(Map.Entry<String,double[]> participant:raw.entrySet()) {
            String speaker=participant.getKey(); JSONObject values=new JSONObject(),normal=new JSONObject(); double score=0;
            for(int i=0;i<7;i++) { double norm=maxima[i]>0?participant.getValue()[i]/maxima[i]:0; values.put(FEATURES[i],participant.getValue()[i]); normal.put(FEATURES[i],norm); score+=WEIGHTS[i]*norm; }
            JSONArray observedRoles=new JSONArray(roles.get(speaker)); if(observedRoles.length()==0) observedRoles.put("Contributor");
            participants.put(new JSONObject().put("speaker",speaker).put("roles",observedRoles).put("speaking_time_s",speaking.get(speaker)));
            JSONArray explanation=new JSONArray().put(evidence.get(speaker).isEmpty()?"Insufficient decision-linked evidence; a zero score does not mean no influence.":"Weighted counts of candidate decision-linked events. Review the listed source evidence; weights are unvalidated.");
            scores.add(new JSONObject().put("participant",speaker).put("influence_score",score).put("raw_features",values).put("normalised_features",normal)
                .put("supporting_events",new JSONArray(evidence.get(speaker))).put("explanation",explanation).put("speaking_time_s",speaking.get(speaker)));
        }
        scores.sort((a,b) -> Double.compare(b.optDouble("influence_score"),a.optDouble("influence_score")));
        JSONArray influence=new JSONArray(); double previous=-1; int rank=0;
        for(int i=0;i<scores.size();i++) { JSONObject score=scores.get(i); double value=score.optDouble("influence_score"); if(value!=previous) rank=i+1; previous=value; influence.put(score.put("rank",rank)); }
        JSONObject weights=new JSONObject(); for(int i=0;i<7;i++) weights.put(FEATURES[i],WEIGHTS[i]);
        boolean attributed=participants.length()>0;
        return report.put("events",events).put("participants",participants).put("influence",influence).put("decisions",decisions).put("interactions",interactions)
            .put("slides",slides).put("aligned_segments",aligned).put("speaker_identified",attributed)
            .put("fusion_method",new JSONObject().put("name","tfidf_native_slide_text_v1").put("threshold",.15).put("minimum_margin",.05).put("visual_encoding",false).put("trained",false))
            .put("influence_method",new JSONObject().put("name","android_candidate_lineage_v1").put("weights",weights).put("validated",false).put("causal",false).put("lineage_window_s",120))
            .put("analysis_method","Pretrained speaker separation; extractive event rules; TF-IDF slide text fusion; candidate decision-linked influence. Review source evidence.");
    }
}

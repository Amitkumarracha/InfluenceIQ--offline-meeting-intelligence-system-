package org.meetiq.offline;

import org.json.*;

/** Schema aliases for reviewing website results; does not rerun or relabel analysis. */
final class PortableReport {
    static JSONObject androidReport(JSONObject source) throws Exception {
        JSONObject data=new JSONObject(source.toString());
        JSONArray transcript=data.getJSONArray("transcript_segments");
        for(int i=0;i<transcript.length();i++) {
            JSONObject row=transcript.getJSONObject(i); row.getString("text"); row.getString("speaker");
            double start=row.getDouble("start"),end=row.getDouble("end");
            if(!Double.isFinite(start)||!Double.isFinite(end)||start<0||end<start) throw new java.io.IOException("Invalid account transcript timestamps");
            if(!row.has("segment_id")) row.put("segment_id",i+1);
        }
        JSONObject overview=data.optJSONObject("meeting_overview");
        if(!data.has("duration")) data.put("duration",overview==null?0:overview.optDouble("duration_s",0));
        JSONObject processing=data.optJSONObject("processing");
        if(!data.has("language")) data.put("language",processing==null?"auto":processing.optString("language","auto"));
        data.put("completed",true);
        if(data.optJSONArray("events")==null) data.put("events",data.optJSONArray("event_timeline")==null?new JSONArray():data.getJSONArray("event_timeline"));
        JSONArray participants=data.optJSONArray("participants");
        if(participants!=null) for(int i=0;i<participants.length();i++) {
            JSONObject person=participants.getJSONObject(i);
            if(!person.has("speaker")) person.put("speaker",person.optString("speaker_id","UNKNOWN"));
            if(!person.has("speaking_time_s")) person.put("speaking_time_s",person.optDouble("speaking_duration_s",0));
        }
        JSONArray slides=data.optJSONArray("slides"),aligned=data.optJSONArray("aligned_segments");
        if(slides!=null) for(int i=0;i<slides.length();i++) {
            JSONObject slide=slides.getJSONObject(i); JSONArray text=slide.optJSONArray("text");
            if(text!=null) { StringBuilder joined=new StringBuilder(); for(int j=0;j<text.length();j++) joined.append(text.optString(j)).append('\n'); slide.put("text",joined.toString().trim()); }
            if(aligned!=null) for(int j=0;j<aligned.length();j++) {
                JSONObject match=aligned.getJSONObject(j);
                if(!match.has("selected_slide")&&slide.optString("slide_id").equals(match.optString("slide_id")))
                    match.put("selected_slide",slide.optInt("slide_number",i+1)).put("score",match.optDouble("alignment_score",0));
            }
        }
        String[] full={"proposal_contribution","evidence_contribution","objection_contribution","revision_contribution","decision_contribution","interaction_contribution","slide_grounded_contribution"};
        JSONArray scores=data.optJSONArray("influence");
        if(scores!=null) for(int i=0;i<scores.length();i++) {
            JSONObject score=scores.getJSONObject(i),raw=score.optJSONObject("raw_features");
            if(!score.has("participant")) score.put("participant",score.optString("speaker_id","UNKNOWN"));
            if(raw!=null) for(int j=0;j<full.length;j++) if(!raw.has(MeetingAnalysis.FEATURES[j])&&raw.has(full[j])) raw.put(MeetingAnalysis.FEATURES[j],raw.get(full[j]));
        }
        return data;
    }
}

package org.meetiq.offline;

import org.json.*;
import java.util.*;

/** Keep raw ASR checkpoint intact; create attributed passages as derived data. */
final class SpeakerReports {
    static JSONArray assign(JSONArray segments,JSONArray rawTurns) throws Exception {
        List<SpeakerAttribution.Turn> turns=new ArrayList<>(); Map<Integer,String> labels=new LinkedHashMap<>();
        for(int i=0;i<rawTurns.length();i++) {
            JSONObject turn=rawTurns.getJSONObject(i); int cluster=turn.getInt("cluster");
            if(!labels.containsKey(cluster)) labels.put(cluster,String.format(Locale.ROOT,"SPEAKER_%02d",labels.size()));
            turns.add(new SpeakerAttribution.Turn(turn.getDouble("start"),turn.getDouble("end"),labels.get(cluster)));
        }
        JSONArray attributed=new JSONArray();
        for(int i=0;i<segments.length();i++) {
            JSONObject seg=segments.getJSONObject(i); JSONArray words=seg.optJSONArray("words");
            StringBuilder original=new StringBuilder(); boolean valid=words!=null && words.length()>0;
            if(words!=null) for(int j=0;j<words.length();j++) {
                JSONObject word=words.getJSONObject(j); original.append(word.optString("text"));
                valid &= word.optDouble("start",-1)>=seg.optDouble("start")-.05 && word.optDouble("end",-1)>word.optDouble("start",-1)
                    && word.optDouble("end")<=seg.optDouble("end")+.05;
            }
            valid &= original.toString().trim().equals(seg.optString("text").trim());
            if(!valid) {
                JSONObject copy=new JSONObject(seg.toString()); copy.remove("words");
                copy.put("speaker",SpeakerAttribution.speaker(seg.optDouble("start"),seg.optDouble("end"),turns));
                copy.put("source_asr_segment_id",seg.getInt("segment_id")).put("segment_id",attributed.length()+1); attributed.put(copy); continue;
            }
            JSONObject passage=null; StringBuilder text=new StringBuilder();
            for(int j=0;j<words.length();j++) {
                JSONObject word=words.getJSONObject(j); String speaker=SpeakerAttribution.speaker(word.getDouble("start"),word.getDouble("end"),turns);
                if(passage==null || !passage.optString("speaker").equals(speaker)) {
                    if(passage!=null) attributed.put(passage.put("text",text.toString().trim()).put("segment_id",attributed.length()+1));
                    passage=new JSONObject().put("start",word.getDouble("start")).put("speaker",speaker).put("source_asr_segment_id",seg.getInt("segment_id"))
                        .put("detected_language",seg.optString("detected_language","auto")); text=new StringBuilder();
                }
                passage.put("end",word.getDouble("end")); text.append(word.optString("text"));
            }
            if(passage!=null) attributed.put(passage.put("text",text.toString().trim()).put("segment_id",attributed.length()+1));
        }
        return attributed;
    }
}

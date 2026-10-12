package org.meetiq.offline;

import java.util.*;

/** Overlap attribution with abstention. Cluster identities are meeting-local. */
final class SpeakerAttribution {
    static final class Turn {
        final double start,end; final String speaker;
        Turn(double start,double end,String speaker) { this.start=start; this.end=end; this.speaker=speaker; }
    }
    static String speaker(double start,double end,List<Turn> turns) {
        if(end<=start) return "UNKNOWN";
        Map<String,Double> coverage=new HashMap<>();
        for(Turn turn:turns) {
            double overlap=Math.max(0,Math.min(end,turn.end)-Math.max(start,turn.start));
            if(overlap>0) coverage.put(turn.speaker,coverage.getOrDefault(turn.speaker,0.0)+overlap);
        }
        String result="UNKNOWN"; double best=0,second=0;
        for(Map.Entry<String,Double> item:coverage.entrySet()) {
            if(item.getValue()>best) { second=best; best=item.getValue(); result=item.getKey(); }
            else second=Math.max(second,item.getValue());
        }
        if(best/(end-start)<0.5 || second>0 && (best-second)/(end-start)<0.15) return "UNKNOWN";
        return result;
    }
}

package org.meetiq.offline;

import java.util.*;

public final class AnalysisMathTest {
    static void check(boolean value,String label) { if(!value) throw new AssertionError(label); }
    public static void main(String[] args) {
        SlideIndex index=new SlideIndex(Arrays.asList("बजट योजना 500 रुपए","Latency decreased 50 milliseconds"));
        double[] hindi=index.scores("बजट योजना"); check(hindi[0]>.6&&hindi[0]<.8&&hindi[1]==0,"Hindi lexical matching");
        check(index.scores("unrelated statement")[0]==0,"Unrelated slide");
        SlideIndex duplicate=new SlideIndex(Arrays.asList("budget 500","budget 500"));
        check(duplicate.scores("budget")[0]==duplicate.scores("budget")[1],"Ambiguous score preservation");
        List<SpeakerAttribution.Turn> turns=Arrays.asList(new SpeakerAttribution.Turn(0,2,"A"),new SpeakerAttribution.Turn(1,3,"B"));
        check(SpeakerAttribution.speaker(1,2,turns).equals("UNKNOWN"),"Overlapping voices");
        check(SpeakerAttribution.speaker(0,.5,turns).equals("A"),"Single voice");
        check(SpeakerAttribution.speaker(4,5,turns).equals("UNKNOWN"),"Missing voice");
        check(SpeakerAttribution.speaker(0,0,turns).equals("UNKNOWN"),"Zero duration");
        System.out.println("Analysis math: Hindi fusion, unknown words, ambiguous slides and overlap attribution passed");
    }
}

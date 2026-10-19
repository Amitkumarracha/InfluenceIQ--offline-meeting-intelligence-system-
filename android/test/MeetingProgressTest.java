package org.meetiq.offline;

/** Checks that live waveform values come from PCM, including signed full scale. */
public final class MeetingProgressTest {
    public static void main(String[] args) {
        byte[] pcm={0,0,0,64,0,(byte)128};
        near(MeetingProgress.amplitude(pcm,6),(float)Math.sqrt(1.25/3));
        near(MeetingProgress.amplitude(pcm,2),0);
        near(MeetingProgress.amplitude(pcm,3),0);
        near(MeetingProgress.amplitude(pcm,8),0);
        MeetingProgress chunk=new MeetingProgress("analyse","123","transcribing",120,300,0,null);
        if(chunk.percent()!=40 || chunk.recording()) throw new AssertionError("Chunk progress");
        if(new MeetingProgress("record","123","recording",4,0,0,null).percent()!=0) throw new AssertionError("Recording has no invented completion percentage");
        if(new MeetingProgress("analyse","123","complete",301,300,0,null).percent()!=100) throw new AssertionError("Clamp completion");
        if(SpeakerBudget.seconds(2L*1024*1024*1024,false)!=8388) throw new AssertionError("PCM allocation ceiling");
        if(SpeakerBudget.seconds(256L*1024*1024,false)!=1048) throw new AssertionError("Reserve system memory");
        if(SpeakerBudget.seconds(Long.MAX_VALUE,true)!=0 || SpeakerBudget.seconds(-1,false)!=0) throw new AssertionError("Low-memory fallback");
        System.out.println("MeetingProgress: PCM amplitude and chunk progress passed");
    }
    private static void near(float actual,float expected) {
        if(Math.abs(actual-expected)>0.00001) throw new AssertionError(actual+" != "+expected);
    }
}

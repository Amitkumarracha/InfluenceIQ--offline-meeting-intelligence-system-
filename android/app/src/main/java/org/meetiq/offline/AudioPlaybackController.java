package org.meetiq.offline;

import android.media.MediaPlayer;
import java.io.File;

/** One asynchronous local player; released with the activity lifecycle. */
final class AudioPlaybackController {
    private MediaPlayer player;
    private String source;
    private boolean prepared;
    String error;
    private int pendingSeek;
    private final Runnable changed;
    AudioPlaybackController(Runnable changed) { this.changed=changed; }
    void play(File audio, double seconds) {
        error=null;
        int position=(int)Math.max(0,seconds*1000);
        if (prepared && audio.getAbsolutePath().equals(source)) { player.seekTo(position); player.start(); changed.run(); return; }
        release(); source=audio.getAbsolutePath(); pendingSeek=position;
        try {
            player=new MediaPlayer(); player.setDataSource(source);
            player.setOnPreparedListener(media -> { if(media!=player) return; prepared=true; media.seekTo(Math.min(pendingSeek,media.getDuration())); media.start(); changed.run(); });
            player.setOnCompletionListener(media -> changed.run());
            player.setOnErrorListener((media,what,extra) -> { release(); error="This recording could not be played."; changed.run(); return true; });
            player.prepareAsync(); changed.run();
        } catch (Exception failure) { release(); error="This recording could not be played."; changed.run(); }
    }
    void toggle(File audio) {
        if (!prepared) { play(audio,pendingSeek/1000.0); return; }
        if (player.isPlaying()) player.pause(); else player.start(); changed.run();
    }
    void seek(int milliseconds) { pendingSeek=Math.max(0,milliseconds); if (prepared) player.seekTo(Math.min(Math.max(0,milliseconds),player.getDuration())); }
    boolean active() { return player!=null; }
    boolean playing() { return prepared && player != null && player.isPlaying(); }
    int position() { return prepared && player != null ? player.getCurrentPosition() : pendingSeek; }
    int duration() { return prepared && player != null ? player.getDuration() : 0; }
    void release() {
        prepared=false; source=null; pendingSeek=0;
        if (player != null) { player.setOnPreparedListener(null); player.setOnCompletionListener(null); player.setOnErrorListener(null); player.release(); player=null; }
    }
}

package org.meetiq.offline;

import android.content.Context;
import android.net.Uri;
import android.provider.OpenableColumns;
import android.database.Cursor;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.concurrent.Executors;
import java.util.concurrent.ExecutorService;
import org.json.*;

/** App-context file transfers survive activity recreation; no network client. */
final class LocalTransfers {
    private static final ExecutorService executor=Executors.newSingleThreadExecutor();
    static volatile boolean busy;
    static volatile String message="", importedMeeting;
    static volatile long revision;
    static void start(Context context, Uri uri, int request, File export) {
        if (busy) return;
        Context app=context.getApplicationContext(); busy=true; importedMeeting=null;
        message=request==10?"Setting up local analysis…":request==12?"Preparing audio…":request==13?"Adding presentation…":"Saving export…"; revision++;
        executor.execute(() -> {
            File temporary=null, directory=null;
            try {
                if (request==11) {
                    if (export==null || !export.isFile()) throw new IOException("Export is no longer available");
                    try (InputStream in=new FileInputStream(export); OutputStream out=app.getContentResolver().openOutputStream(uri)) {
                        if (out==null) throw new IOException("Could not open export destination");
                        copy(in,out,Long.MAX_VALUE,null,null);
                    }
                    message="Export saved to your selected destination.";
                } else {
                    boolean model=request==10, presentation=request==13;
                    temporary=new File(app.getFilesDir(),model?"model.tmp":presentation?"presentation-import.tmp":"audio-import.tmp");
                    MessageDigest digest=MessageDigest.getInstance("SHA-256");
                    try (InputStream in=app.getContentResolver().openInputStream(uri); FileOutputStream out=new FileOutputStream(temporary)) {
                        if (in==null) throw new IOException("Could not open selected file");
                        copy(in,out,model?2L*1024*1024*1024:700L*1024*1024,digest,app.getFilesDir()); out.getFD().sync();
                    }
                    if(presentation) {
                        java.util.List<String> slides=PresentationText.read(temporary);
                        File target=export==null?new File(app.getFilesDir(),"draft-presentation.pptx"):export;
                        JSONObject text=new JSONObject().put("slides",new JSONArray(slides));
                        if(!temporary.renameTo(target)) throw new IOException("Could not save presentation");
                        MeetingService.atomic(new File(target.getParentFile(),export==null?"draft-presentation.json":"presentation.json"),text);
                        message="Presentation saved with "+slides.size()+" slides. Run analysis to update speech matches.";
                    } else if (model) {
                        try (RandomAccessFile file=new RandomAccessFile(temporary,"r")) {
                            if (Integer.reverseBytes(file.readInt())!=0x67676d6c) throw new IOException("Select a GGML Whisper .bin model");
                        }
                        if (!temporary.renameTo(new File(app.getFilesDir(),"model.bin"))) throw new IOException("Could not replace speech model");
                        StringBuilder hash=new StringBuilder(); for(byte value:digest.digest()) hash.append(String.format("%02x",value));
                        Files.write(new File(app.getFilesDir(),"model.sha256").toPath(),hash.toString().getBytes(StandardCharsets.UTF_8));
                        String name="Whisper GGML model";
                        try (Cursor cursor=app.getContentResolver().query(uri,new String[]{OpenableColumns.DISPLAY_NAME},null,null,null)) {
                            if (cursor!=null && cursor.moveToFirst()) name=cursor.getString(0);
                        } catch (Exception ignored) { }
                        app.getSharedPreferences("transcription",Context.MODE_PRIVATE).edit().putString("model_name",name).apply();
                        message="Speech model imported. Ready for local transcription.";
                    } else {
                        directory=new File(app.getFilesDir(),"meetings/"+System.currentTimeMillis());
                        if (!directory.mkdirs()) throw new IOException("Could not create meeting folder");
                        AudioImport.normalize(temporary,new File(directory,"audio.wav"));
                        JSONObject metadata=new JSONObject().put("analysis_language",new String[]{"auto","en","hi"}[Math.max(0,Math.min(2,app.getSharedPreferences("transcription",Context.MODE_PRIVATE).getInt("language",0)))])
                            .put("vocabulary",app.getSharedPreferences("transcription",Context.MODE_PRIVATE).getString("vocabulary",""));
                        MeetingService.atomic(new File(directory,"metadata.json"),metadata);
                        attachDraft(app,directory);
                        importedMeeting=directory.getName(); message="Recording imported. Ready to analyse locally.";
                    }
                }
            } catch (Exception error) {
                if (directory!=null) { File[] files=directory.listFiles(); if(files!=null) for(File file:files) file.delete(); directory.delete(); }
                message="Could not complete transfer: "+error.getMessage()+". Saved recordings remain available.";
            } finally {
                if (temporary!=null) temporary.delete(); busy=false; revision++;
            }
        });
    }
    static void attachDraft(Context context,File directory) throws IOException {
        File source=new File(context.getFilesDir(),"draft-presentation.pptx"), text=new File(context.getFilesDir(),"draft-presentation.json");
        if(!source.isFile()||!text.isFile()) return;
        Files.copy(source.toPath(),new File(directory,"presentation.pptx").toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        Files.copy(text.toPath(),new File(directory,"presentation.json").toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        source.delete(); text.delete();
    }
    private static void copy(InputStream in,OutputStream out,long maximum,MessageDigest digest,File storage) throws IOException {
        byte[] block=new byte[65536]; long total=0; int count;
        while ((count=in.read(block))!=-1) {
            total+=count;
            if (total>maximum) throw new IOException("Selected file exceeds the supported size");
            if (storage!=null && storage.getUsableSpace()<count+1024*1024) throw new IOException("Device storage is full");
            out.write(block,0,count); if (digest!=null) digest.update(block,0,count);
        }
    }
}

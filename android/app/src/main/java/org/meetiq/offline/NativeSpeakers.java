package org.meetiq.offline;

import android.content.Context;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/** Packaged pretrained models; no downloads or network permission at runtime. */
final class NativeSpeakers {
    static { System.loadLibrary("meetiq"); }
    static volatile int done,total;
    static void progress(int processed,int count) { done=processed; total=count; }
    static native byte[] diarize(String audio,String segmentation,String embedding,int speakers);
    static File model(Context context,String name) throws Exception {
        String expected=name.equals("segmentation.onnx")?"220ad67ca923bef2fa91f2390c786097bf305bceb5e261d4af67b38e938e1079":"1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b";
        File directory=new File(context.getFilesDir(),"speaker-models"); if(!directory.isDirectory()&&!directory.mkdirs()) throw new IOException("Cannot prepare local speaker models");
        File target=new File(directory,name);
        if(target.isFile()&&MeetingService.sha256(target).equals(expected)) return target;
        File temporary=new File(directory,name+".tmp");
        try {
            MessageDigest digest=MessageDigest.getInstance("SHA-256");
            try(InputStream in=context.getAssets().open("speaker-models/"+name); FileOutputStream out=new FileOutputStream(temporary)) {
                byte[] block=new byte[65536]; int n;
                while((n=in.read(block))!=-1) { if(directory.getUsableSpace()<n+1024*1024) throw new IOException("Device storage is full"); out.write(block,0,n); digest.update(block,0,n); }
                out.getFD().sync();
            }
            StringBuilder hash=new StringBuilder(); for(byte value:digest.digest()) hash.append(String.format("%02x",value));
            if(!hash.toString().equals(expected)) throw new IOException("Packaged speaker model failed integrity check");
            if(!temporary.renameTo(target)) throw new IOException("Cannot save local speaker model");
            return target;
        } finally { temporary.delete(); }
    }
    static String run(File audio,File segmentation,File embedding,int speakers) {
        done=0; total=0;
        return new String(diarize(audio.getAbsolutePath(),segmentation.getAbsolutePath(),embedding.getAbsolutePath(),speakers),StandardCharsets.UTF_8);
    }
}

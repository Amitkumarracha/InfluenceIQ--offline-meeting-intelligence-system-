package org.meetiq.offline;

import java.io.*;

/** Run with app_process on an emulator: real Android codecs, no speech model. */
public final class AudioImportProbe {
    public static void main(String[] args) throws Exception {
        for(String name:args) {
            File input=new File(name), output=new File(input.getParentFile(),input.getName()+".normalized.wav");
            AudioImport.normalize(input,output);
            try(RandomAccessFile file=new RandomAccessFile(output,"r")) {
                file.seek(20);
                if(Short.reverseBytes(file.readShort())!=1||Short.reverseBytes(file.readShort())!=1||Integer.reverseBytes(file.readInt())!=16000) throw new AssertionError("Wrong output format");
                file.seek(34); if(Short.reverseBytes(file.readShort())!=16) throw new AssertionError("Wrong PCM width");
                double seconds=(file.length()-44)/32000.0;
                if(seconds<1.9||seconds>2.2) throw new AssertionError("Unexpected duration: "+seconds);
                file.seek(44); double energy=0; int count=0;
                while(file.getFilePointer()+2<=file.length()) { double sample=Short.reverseBytes(file.readShort())/32768.0; energy+=sample*sample; count++; }
                if(Math.sqrt(energy/count)<.01) throw new AssertionError("Decoder lost the tone");
                System.out.println(input.getName()+": 16 kHz mono PCM16, duration "+seconds+", signal retained");
            }
        }
    }
}

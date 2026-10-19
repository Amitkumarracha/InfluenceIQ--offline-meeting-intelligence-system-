package org.meetiq.offline;

import java.io.*;
import java.util.HashSet;

/** Check the pinned whisper.cpp GGML layout before replacing a working model. */
final class ModelFile {
    private static int integer(RandomAccessFile file) throws IOException { return Integer.reverseBytes(file.readInt()); }
    private static void require(boolean valid) throws IOException {
        if(!valid) throw new IOException("Incomplete or unsupported multilingual Whisper GGML model");
    }
    private static void skip(RandomAccessFile file,long bytes) throws IOException {
        require(bytes>=0 && bytes<=file.length()-file.getFilePointer());
        file.seek(file.getFilePointer()+bytes);
    }
    static void validate(File source) throws IOException {
        try(RandomAccessFile file=new RandomAccessFile(source,"r")) {
            require(integer(file)==0x67676d6c);
            int vocabulary=integer(file),audioContext=integer(file),state=integer(file),heads=integer(file),audioLayers=integer(file);
            int textContext=integer(file),textState=integer(file),textHeads=integer(file),textLayers=integer(file),mels=integer(file),format=integer(file);
            require(vocabulary>=51865 && vocabulary<=52000 && audioContext==1500 && textContext==448);
            require((state==384||state==512||state==768||state==1024||state==1280) && textState==state && heads==state/64 && textHeads==heads);
            require((audioLayers==4||audioLayers==6||audioLayers==12||audioLayers==24||audioLayers==32)
                && (textLayers==4||textLayers==6||textLayers==12||textLayers==24||textLayers==32));
            require((mels==80||mels==128) && format>=0 && format%1000<=15);
            int filterMels=integer(file),frequencies=integer(file);
            require(filterMels==mels && frequencies==201); skip(file,(long)filterMels*frequencies*4);
            int words=integer(file); require(words>0 && words<=vocabulary);
            for(int i=0;i<words;i++) { int size=integer(file); require(size>=0 && size<=65536); skip(file,size); }
            HashSet<String> names=new HashSet<>();
            while(file.getFilePointer()<file.length()) {
                int dimensions=integer(file),nameLength=integer(file),type=integer(file);
                require(dimensions>=1 && dimensions<=3 && nameLength>0 && nameLength<=256);
                long elements=1; int width=0;
                for(int i=0;i<dimensions;i++) { int size=integer(file); require(size>0 && size<=100000); if(i==0) width=size; elements*=size; require(elements<=Integer.MAX_VALUE); }
                byte[] name=new byte[nameLength]; file.readFully(name);
                require(names.add(new String(name,java.nio.charset.StandardCharsets.UTF_8)) && names.size()<=audioLayers*15+textLayers*24+11);
                int block,bytes;
                switch(type) {
                    case 0: block=1; bytes=4; break;
                    case 1: block=1; bytes=2; break;
                    case 2: block=32; bytes=18; break;
                    case 3: block=32; bytes=20; break;
                    case 6: block=32; bytes=22; break;
                    case 7: block=32; bytes=24; break;
                    case 8: block=32; bytes=34; break;
                    case 10: block=256; bytes=84; break;
                    case 11: block=256; bytes=110; break;
                    case 12: block=256; bytes=144; break;
                    case 13: block=256; bytes=176; break;
                    case 14: block=256; bytes=210; break;
                    default: throw new IOException("Unsupported GGML quantization; import an F16, Q4, Q5 or Q8 model");
                }
                require(width%block==0); skip(file,elements/block*bytes);
            }
            require(names.size()==audioLayers*15+textLayers*24+11);
        } catch(EOFException error) { throw new IOException("Speech model is truncated. The previous model has been retained.",error); }
    }
}

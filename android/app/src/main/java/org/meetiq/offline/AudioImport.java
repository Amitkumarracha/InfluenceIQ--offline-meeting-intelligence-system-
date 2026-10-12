package org.meetiq.offline;

import android.media.*;
import java.io.*;
import java.nio.ByteBuffer;

/** Local system codecs decode phone recordings without a network or added library. */
final class AudioImport {
    static void normalize(File source,File destination) throws Exception {
        try(RandomAccessFile file=new RandomAccessFile(source,"r")) {
            if(file.length()>=4&&file.readInt()==0x52494646) { WavAudio.normalize(source,destination); return; }
        }
        MediaExtractor extractor=new MediaExtractor(); MediaCodec decoder=null; PcmAudio pcm=null;
        try {
            extractor.setDataSource(source.getAbsolutePath()); int track=-1;
            for(int i=0;i<extractor.getTrackCount();i++) if(extractor.getTrackFormat(i).getString(MediaFormat.KEY_MIME).startsWith("audio/")) { track=i; break; }
            if(track<0) throw new IOException("No supported audio was found in this file");
            extractor.selectTrack(track); MediaFormat input=extractor.getTrackFormat(track);
            if(input.containsKey(MediaFormat.KEY_DURATION)&&input.getLong(MediaFormat.KEY_DURATION)>6L*3600*1000000)
                throw new IOException("Recording exceeds six hours");
            input.setInteger(MediaFormat.KEY_PCM_ENCODING,AudioFormat.ENCODING_PCM_16BIT);
            decoder=MediaCodec.createDecoderByType(input.getString(MediaFormat.KEY_MIME)); decoder.configure(input,null,null,0); decoder.start();
            boolean ended=false, done=false; long lastOutput=System.nanoTime(); MediaCodec.BufferInfo info=new MediaCodec.BufferInfo();
            while(!done) {
                if(!ended) {
                    int index=decoder.dequeueInputBuffer(10000);
                    if(index>=0) {
                        ByteBuffer buffer=decoder.getInputBuffer(index); buffer.clear(); int size=extractor.readSampleData(buffer,0);
                        if(size<0) { decoder.queueInputBuffer(index,0,0,0,MediaCodec.BUFFER_FLAG_END_OF_STREAM); ended=true; }
                        else { decoder.queueInputBuffer(index,0,size,Math.max(0,extractor.getSampleTime()),0); extractor.advance(); }
                    }
                }
                int index=decoder.dequeueOutputBuffer(info,10000);
                if(index==MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    MediaFormat output=decoder.getOutputFormat(); int encoding=output.containsKey(MediaFormat.KEY_PCM_ENCODING)?output.getInteger(MediaFormat.KEY_PCM_ENCODING):AudioFormat.ENCODING_PCM_16BIT;
                    if(pcm!=null) throw new IOException("Audio format changed during decoding");
                    if(encoding!=AudioFormat.ENCODING_PCM_16BIT&&encoding!=AudioFormat.ENCODING_PCM_FLOAT) throw new IOException("Unsupported decoder sample format");
                    pcm=new PcmAudio(destination,output.getInteger(MediaFormat.KEY_SAMPLE_RATE),output.getInteger(MediaFormat.KEY_CHANNEL_COUNT),encoding==AudioFormat.ENCODING_PCM_FLOAT?32:16,encoding==AudioFormat.ENCODING_PCM_FLOAT);
                } else if(index>=0) {
                    try {
                        if(info.size>0) {
                            if(pcm==null) throw new IOException("Audio decoder did not provide a sample format");
                            if(destination.getParentFile().getUsableSpace()<info.size+1024*1024) throw new IOException("Device storage is full");
                            ByteBuffer buffer=decoder.getOutputBuffer(index); buffer.position(info.offset); buffer.limit(info.offset+info.size);
                            byte[] block=new byte[info.size]; buffer.get(block); pcm.write(block,0,block.length); lastOutput=System.nanoTime();
                        }
                        done=(info.flags&MediaCodec.BUFFER_FLAG_END_OF_STREAM)!=0;
                    } finally { decoder.releaseOutputBuffer(index,false); }
                }
                if(System.nanoTime()-lastOutput>60L*1000000000) throw new IOException("Audio decoder stopped responding");
            }
            if(pcm==null) throw new IOException("Recording contains no audio"); pcm.finish();
        } finally {
            if(pcm!=null) pcm.close();
            if(decoder!=null) { try { decoder.stop(); } finally { decoder.release(); } }
            extractor.release();
        }
    }
}

package org.meetiq.offline;

import java.io.*;

/** Streaming channel mixing and area-averaged resampling to the model's PCM format. */
public final class PcmAudio implements AutoCloseable {
    private final RandomAccessFile output;
    private final int channels, bits, frameBytes;
    private final boolean floating;
    private final double interval;
    private double remaining, weighted, used;
    private final byte[] frame, block=new byte[32768];
    private int pending, position;
    private long bytes;
    private boolean finished;

    public PcmAudio(File destination,int rate,int channels,int bits,boolean floating) throws IOException {
        if(rate<8000||rate>192000||channels<1||channels>8||!(bits==8||bits==16||bits==24||bits==32)||floating&&bits!=32)
            throw new IOException("Unsupported audio sample format");
        this.channels=channels; this.bits=bits; this.floating=floating;
        frameBytes=channels*(bits/8); frame=new byte[frameBytes]; interval=rate/16000.0; remaining=interval;
        output=new RandomAccessFile(destination,"rw"); output.setLength(0); WavAudio.writeHeader(output,0);
    }
    public void write(byte[] values,int first,int count) throws IOException {
        for(int end=first+count;first<end;) {
            int n=Math.min(frameBytes-pending,end-first); System.arraycopy(values,first,frame,pending,n); first+=n; pending+=n;
            if(pending!=frameBytes) continue; pending=0;
            double mono=0;
            for(int channel=0;channel<channels;channel++) {
                int offset=channel*(bits/8), value=0;
                for(int i=0;i<bits/8;i++) value|=(frame[offset+i]&255)<<(8*i);
                double sample=floating?Float.intBitsToFloat(value):bits==8?(value-128)/128.0:
                    bits==32?value/2147483648.0:(value<<(32-bits)>>(32-bits))/Math.pow(2,bits-1);
                if(!Double.isFinite(sample)) throw new IOException("Invalid floating-point audio");
                mono+=sample/channels;
            }
            double available=1;
            while(available>1e-9) {
                double part=Math.min(available,remaining); weighted+=mono*part; used+=part; remaining-=part; available-=part;
                if(remaining<1e-9) { sample(weighted/used); weighted=used=0; remaining=interval; }
            }
        }
    }
    private void sample(double value) throws IOException {
        if(bytes>=32000L*6*3600) throw new IOException("Recording exceeds six hours");
        int pcm=(int)Math.max(-32768,Math.min(32767,Math.round(value*32768)));
        block[position++]=(byte)pcm; block[position++]=(byte)(pcm>>8); bytes+=2;
        if(position==block.length) flush();
    }
    private void flush() throws IOException { output.write(block,0,position); position=0; }
    public void finish() throws IOException {
        if(finished) return;
        if(pending!=0) throw new IOException("Truncated audio frame");
        if(used>1e-9) sample(weighted/used);
        if(bytes==0) throw new IOException("Recording contains no audio");
        flush(); WavAudio.writeHeader(output,bytes); output.getFD().sync(); finished=true;
    }
    public void close() throws IOException { output.close(); }
}

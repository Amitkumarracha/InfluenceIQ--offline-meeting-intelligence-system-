package org.meetiq.offline;

import java.io.*;

/** Read common PCM/float WAV formats; normalize samples for on-device inference. */
public final class WavAudio {
    public static void normalize(File source, File destination) throws IOException {
        try (RandomAccessFile input = new RandomAccessFile(source, "r")) {
            if (input.length() < 44 || !four(input).equals("RIFF")) throw new IOException("Select a PCM WAV recording");
            input.skipBytes(4);
            if (!four(input).equals("WAVE")) throw new IOException("Not a WAV recording");
            int format=0, channels=0, rate=0, bits=0, align=0;
            long offset = -1, bytes = 0;
            while (input.getFilePointer() + 8 <= input.length()) {
                String kind = four(input);
                long length = Integer.toUnsignedLong(Integer.reverseBytes(input.readInt()));
                long first = input.getFilePointer();
                if (length > input.length() - first) throw new IOException("Truncated WAV chunk");
                if (kind.equals("fmt ")) {
                    if (length < 16) throw new IOException("Invalid WAV format");
                    format = Short.toUnsignedInt(Short.reverseBytes(input.readShort()));
                    channels = Short.toUnsignedInt(Short.reverseBytes(input.readShort()));
                    rate = Integer.reverseBytes(input.readInt());
                    input.skipBytes(4); align=Short.toUnsignedInt(Short.reverseBytes(input.readShort()));
                    bits = Short.toUnsignedInt(Short.reverseBytes(input.readShort()));
                    if(format==0xfffe) {
                        if(length<40||Short.toUnsignedInt(Short.reverseBytes(input.readShort()))<22) throw new IOException("Invalid extensible WAV format");
                        int validBits=Short.toUnsignedInt(Short.reverseBytes(input.readShort())); input.skipBytes(4);
                        format=Integer.reverseBytes(input.readInt()); byte[] guid=new byte[12]; input.readFully(guid);
                        if(validBits!=0&&validBits!=bits||!java.util.Arrays.equals(guid,new byte[]{0,0,16,0,(byte)128,0,0,(byte)170,0,56,(byte)155,113}))
                            throw new IOException("Unsupported extensible WAV sample format");
                    }
                } else if (kind.equals("data") && offset < 0) {
                    offset = first; bytes = length;
                }
                input.seek(first + length + (length & 1));
            }
            if ((format!=1&&format!=3)||channels<1||channels>8||rate<8000||rate>192000
                ||!(bits==8||bits==16||bits==24||bits==32)||format==3&&bits!=32
                ||align!=channels*(bits/8)||offset<0||bytes==0||bytes%align!=0)
                throw new IOException("This WAV sample format is unsupported or incomplete");
            if (bytes/(double)align/rate > 6 * 3600) throw new IOException("Recording exceeds six hours");
            if(format!=1||channels!=1||rate!=16000||bits!=16) {
                input.seek(offset);
                try(PcmAudio output=new PcmAudio(destination,rate,channels,bits,format==3)) {
                    byte[] block=new byte[65536]; long remaining=bytes;
                    while(remaining>0) { int count=input.read(block,0,(int)Math.min(remaining,block.length)); if(count<0) throw new EOFException("Truncated recording"); output.write(block,0,count); remaining-=count; }
                    output.finish();
                }
                return;
            }
            try (RandomAccessFile output = new RandomAccessFile(destination, "rw")) {
                output.setLength(0); writeHeader(output, bytes); input.seek(offset);
                byte[] block = new byte[65536]; long remaining = bytes;
                while (remaining > 0) {
                    int count = input.read(block, 0, (int)Math.min(remaining, block.length));
                    if (count < 0) throw new EOFException("Truncated recording");
                    output.write(block, 0, count); remaining -= count;
                }
                output.getFD().sync();
            }
        }
    }
    private static String four(RandomAccessFile input) throws IOException {
        byte[] bytes = new byte[4]; input.readFully(bytes); return new String(bytes, "US-ASCII");
    }
    public static void writeHeader(RandomAccessFile output, long bytes) throws IOException {
        long position = output.getFilePointer();
        output.seek(0);
        output.writeBytes("RIFF"); output.writeInt(Integer.reverseBytes((int)(bytes + 36)));
        output.writeBytes("WAVEfmt "); output.writeInt(Integer.reverseBytes(16));
        output.writeShort(Short.reverseBytes((short)1)); output.writeShort(Short.reverseBytes((short)1));
        output.writeInt(Integer.reverseBytes(16000)); output.writeInt(Integer.reverseBytes(32000));
        output.writeShort(Short.reverseBytes((short)2)); output.writeShort(Short.reverseBytes((short)16));
        output.writeBytes("data"); output.writeInt(Integer.reverseBytes((int)bytes));
        output.seek(Math.max(44, position));
    }
}

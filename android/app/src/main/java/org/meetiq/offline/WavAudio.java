package org.meetiq.offline;

import java.io.*;

/** Accept PCM WAV only; normalize chunk layout for the on-device reader. */
public final class WavAudio {
    public static void normalize(File source, File destination) throws IOException {
        try (RandomAccessFile input = new RandomAccessFile(source, "r")) {
            if (input.length() < 44 || !four(input).equals("RIFF")) throw new IOException("Select a PCM WAV recording");
            input.skipBytes(4);
            if (!four(input).equals("WAVE")) throw new IOException("Not a WAV recording");
            boolean valid = false;
            long offset = -1, bytes = 0;
            while (input.getFilePointer() + 8 <= input.length()) {
                String kind = four(input);
                long length = Integer.toUnsignedLong(Integer.reverseBytes(input.readInt()));
                long first = input.getFilePointer();
                if (length > input.length() - first) throw new IOException("Truncated WAV chunk");
                if (kind.equals("fmt ")) {
                    if (length < 16) throw new IOException("Invalid WAV format");
                    int format = Short.toUnsignedInt(Short.reverseBytes(input.readShort()));
                    int channels = Short.toUnsignedInt(Short.reverseBytes(input.readShort()));
                    int rate = Integer.reverseBytes(input.readInt());
                    input.skipBytes(6);
                    int bits = Short.toUnsignedInt(Short.reverseBytes(input.readShort()));
                    valid = format == 1 && channels == 1 && rate == 16000 && bits == 16;
                } else if (kind.equals("data") && offset < 0) {
                    offset = first; bytes = length;
                }
                input.seek(first + length + (length & 1));
            }
            if (!valid || offset < 0 || bytes == 0 || (bytes & 1) != 0)
                throw new IOException("Import 16 kHz mono, 16-bit PCM WAV. Convert other formats on the laptop.");
            if (bytes > 32000L * 6 * 3600) throw new IOException("Recording exceeds six hours");
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

package org.meetiq.offline.test;

import org.meetiq.offline.WavAudio;
import java.io.*;
import java.nio.file.*;
import java.util.Arrays;

public final class WavAudioTest {
    public static void main(String[] args) throws Exception {
        File directory = Files.createTempDirectory("meetiq-wav-test").toFile();
        File original = new File(directory, "original.wav"), normalized = new File(directory, "normalized.wav");
        try {
            try (RandomAccessFile file = new RandomAccessFile(original, "rw")) {
                WavAudio.writeHeader(file, 0);
                file.write(new byte[]{1, 0, 2, 0});
                WavAudio.writeHeader(file, 4);
                if (file.getFilePointer() != 48) throw new AssertionError("Header update moved the audio write pointer");
                file.write(new byte[]{3, 0});
                WavAudio.writeHeader(file, 6);
            }
            WavAudio.normalize(original, normalized);
            if (!Arrays.equals(Files.readAllBytes(original.toPath()), Files.readAllBytes(normalized.toPath()))) throw new AssertionError("PCM changed");
            try (RandomAccessFile file = new RandomAccessFile(original, "rw")) {
                file.seek(50); file.writeBytes("JUNK"); file.writeInt(Integer.reverseBytes(2)); file.writeShort(0);
                file.seek(4); file.writeInt(Integer.reverseBytes(52));
            }
            WavAudio.normalize(original, normalized);
            if (normalized.length() != 50) throw new AssertionError("Extra WAV chunks were not normalized");
            try (RandomAccessFile file = new RandomAccessFile(original, "rw")) { file.seek(22); file.writeShort(Short.reverseBytes((short)2)); }
            reject(original, normalized);
            try (RandomAccessFile file = new RandomAccessFile(original, "rw")) { file.seek(22); file.writeShort(Short.reverseBytes((short)1)); file.setLength(47); }
            reject(original, normalized);
            System.out.println("Android WAV checks passed: header recovery, PCM preservation, extra chunks, invalid format, truncation.");
        } finally {
            original.delete(); normalized.delete(); directory.delete();
        }
    }
    private static void reject(File original, File normalized) throws Exception {
        try { WavAudio.normalize(original, normalized); throw new AssertionError("Invalid audio accepted"); }
        catch (IOException expected) { }
    }
}

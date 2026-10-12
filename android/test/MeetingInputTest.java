package org.meetiq.offline.test;

import org.meetiq.offline.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public final class MeetingInputTest {
    public static void main(String[] args) throws Exception {
        File directory=Files.createTempDirectory("meeting-input-test").toFile();
        File source=new File(directory,"stereo.wav"), output=new File(directory,"mono.wav"), ppt=new File(directory,"slides.pptx");
        try {
            // Ordinary 44.1 kHz stereo recordings must preserve duration and channel mean.
            try(RandomAccessFile file=new RandomAccessFile(source,"rw")) {
                WavAudio.writeHeader(file,44100*4); file.seek(22); file.writeShort(Short.reverseBytes((short)2)); file.writeInt(Integer.reverseBytes(44100));
                file.writeInt(Integer.reverseBytes(44100*4)); file.writeShort(Short.reverseBytes((short)4)); file.seek(44);
                for(int i=0;i<44100;i++) { file.writeShort(Short.reverseBytes((short)1000)); file.writeShort(Short.reverseBytes((short)3000)); }
            }
            WavAudio.normalize(source,output);
            if(output.length()!=44+32000) throw new AssertionError("Sample-rate conversion changed duration");
            try(RandomAccessFile file=new RandomAccessFile(output,"r")) {
                file.seek(44); while(file.getFilePointer()<file.length()) if(Short.reverseBytes(file.readShort())!=2000) throw new AssertionError("Channel mixing changed mean");
            }
            // Decoder buffers can split a PCM frame across arbitrary byte boundaries.
            try(PcmAudio file=new PcmAudio(output,16000,1,16,false)) { byte[] pcm={1,0,2,0,3,0}; file.write(pcm,0,3); file.write(pcm,3,3); file.finish(); }
            if(!Arrays.equals(Arrays.copyOfRange(Files.readAllBytes(output.toPath()),44,50),new byte[]{1,0,2,0,3,0})) throw new AssertionError("Chunk boundaries changed PCM");
            List<String> terms=Vocabulary.suggest(Arrays.asList("Budget budget बजट हिंदी. We will send the report 2026."));
            if(!terms.get(0).equals("budget")||!terms.contains("हिंदी")||terms.contains("2026")||terms.contains("report")) throw new AssertionError("Vocabulary suggestions broke Unicode/provenance");
            presentation(ppt,"<p:sld xmlns:p='x' xmlns:a='http://schemas.openxmlformats.org/drawingml/2006/main'><a:t>Budget हिंदी</a:t></p:sld>");
            if(!PresentationText.read(ppt).equals(Arrays.asList("Budget हिंदी"))) throw new AssertionError("PPT text extraction failed");
            presentation(ppt,"<!DOCTYPE test [<!ENTITY x 'expanded'>]><test>&x;</test>");
            try { PresentationText.read(ppt); throw new AssertionError("Unsafe presentation XML accepted"); } catch(IOException expected) { }
            System.out.println("Meeting inputs passed: stereo/rate conversion, split PCM buffers, Unicode suggestions, PPTX and unsafe XML rejection.");
        } finally { source.delete(); output.delete(); ppt.delete(); directory.delete(); }
    }
    private static void presentation(File file,String xml) throws Exception {
        try(ZipOutputStream zip=new ZipOutputStream(new FileOutputStream(file))) {
            zip.putNextEntry(new ZipEntry("ppt/slides/slide1.xml")); zip.write(xml.getBytes("UTF-8")); zip.closeEntry();
        }
    }
}

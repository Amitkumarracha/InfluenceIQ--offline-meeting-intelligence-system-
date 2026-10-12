package org.meetiq.offline;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.zip.*;
import javax.xml.parsers.SAXParserFactory;
import org.xml.sax.*;
import org.xml.sax.helpers.DefaultHandler;

/** Native PPTX slide text for reference. Does not claim slide-time or speaker fusion. */
public final class PresentationText {
    public static List<String> read(File file) throws Exception {
        try(ZipFile zip=new ZipFile(file)) {
            List<ZipEntry> slides=new ArrayList<>(); Enumeration<? extends ZipEntry> entries=zip.entries();
            while(entries.hasMoreElements()) { ZipEntry entry=entries.nextElement(); if(entry.getName().matches("ppt/slides/slide[0-9]+\\.xml")) slides.add(entry); if(slides.size()>1000) throw new IOException("Presentation has too many slides"); }
            if(slides.isEmpty()) throw new IOException("Select a PPTX presentation with slides");
            slides.sort(Comparator.comparingInt(entry -> Integer.parseInt(entry.getName().replaceAll("[^0-9]",""))));
            List<String> result=new ArrayList<>(); int total=0;
            for(ZipEntry slide:slides) {
                ByteArrayOutputStream bytes=new ByteArrayOutputStream();
                try(InputStream in=zip.getInputStream(slide)) { byte[] block=new byte[8192]; int count; while((count=in.read(block))!=-1) { if(bytes.size()+count>2*1024*1024) throw new IOException("Slide is too large"); bytes.write(block,0,count); } }
                total+=bytes.size(); if(total>16*1024*1024) throw new IOException("Presentation text is too large");
                String xml=new String(bytes.toByteArray(),StandardCharsets.UTF_8);
                if(xml.contains("<!DOCTYPE")||xml.contains("<!ENTITY")||xml.indexOf('\0')>=0) throw new IOException("Unsupported presentation XML");
                StringBuilder text=new StringBuilder(); SAXParserFactory factory=SAXParserFactory.newInstance(); factory.setNamespaceAware(true);
                XMLReader reader=factory.newSAXParser().getXMLReader(); reader.setEntityResolver((publicId,systemId) -> { throw new SAXException("External XML references are disabled"); });
                reader.setContentHandler(new DefaultHandler() {
                    boolean content;
                    public void startElement(String uri,String local,String name,Attributes attrs) { content="http://schemas.openxmlformats.org/drawingml/2006/main".equals(uri)&&"t".equals(local); }
                    public void characters(char[] values,int first,int count) throws SAXException { if(content) { if(text.length()+count>200000) throw new SAXException("Slide text is too long"); text.append(values,first,count); } }
                    public void endElement(String uri,String local,String name) { if(content) text.append(' '); content=false; }
                });
                reader.parse(new InputSource(new StringReader(xml))); result.add(text.toString().trim());
                if(result.stream().mapToInt(String::length).sum()>200000) throw new IOException("Presentation has too much text for local review");
            }
            return result;
        }
    }
}

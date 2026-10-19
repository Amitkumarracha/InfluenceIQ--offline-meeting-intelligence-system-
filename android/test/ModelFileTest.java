package org.meetiq.offline;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;

public final class ModelFileTest {
    private static void rejected(File file) throws Exception {
        try { ModelFile.validate(file); throw new AssertionError("Invalid model accepted"); }
        catch(IOException expected) { }
    }
    public static void main(String[] args) throws Exception {
        File temporary=File.createTempFile("influence-model-test-",".bin");
        try {
            Files.write(temporary.toPath(),new byte[]{'l','m','g','g'}); rejected(temporary);
            if(args.length>0 && new File(args[0]).isFile()) {
                File real=new File(args[0]); ModelFile.validate(real);
                Files.copy(real.toPath(),temporary.toPath(),StandardCopyOption.REPLACE_EXISTING);
                try(RandomAccessFile file=new RandomAccessFile(temporary,"rw")) { file.setLength(file.length()-1); }
                rejected(temporary);
                try(RandomAccessFile file=new RandomAccessFile(temporary,"rw")) { file.setLength(48); file.seek(7*4); file.writeInt(Integer.reverseBytes(123)); }
                rejected(temporary);
                System.out.println("GGML checks passed: real multilingual model, truncated tensor, invalid header and magic-only file");
            } else System.out.println("GGML malformed-file checks passed; provision a model for the complete-file check");
        } finally { temporary.delete(); }
    }
}

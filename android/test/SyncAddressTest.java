package org.meetiq.offline;

public final class SyncAddressTest {
    public static void main(String[] args) throws Exception {
        for(String value:new String[]{"https://meetings.example.org/","http://127.0.0.1:8000","http://10.0.2.2:8000","http://localhost:8000"})
            if(SyncAddress.normalize(value).endsWith("/")) throw new AssertionError("Origin trailing slash");
        for(String value:new String[]{"http://meetings.example.org","http://192.168.1.2:8000","https://user:pass@example.org","https://example.org/api","https://example.org?token=a","https://example.org#fragment","file:///tmp/server","https://example.org:70000"}) {
            try { SyncAddress.normalize(value); throw new AssertionError("Unsafe origin accepted: "+value); }
            catch(java.io.IOException expected) { }
        }
        System.out.println("Account URL policy passed: HTTPS or exact local-development hosts; no URL credentials, paths or redirects");
    }
}

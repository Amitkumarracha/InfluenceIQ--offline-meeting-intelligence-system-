package org.meetiq.offline;

import java.net.URI;
import java.io.IOException;

/** Credentials use HTTPS; loopback HTTP supports a local USB adb reverse tunnel. */
final class SyncAddress {
    static String normalize(String value) throws IOException {
        try {
            URI uri=new URI(value.trim()); String host=uri.getHost(),scheme=uri.getScheme();
            boolean local="127.0.0.1".equals(host)||"localhost".equals(host)||"10.0.2.2".equals(host);
            if(host==null||uri.getRawUserInfo()!=null||uri.getRawQuery()!=null||uri.getRawFragment()!=null
                ||(!"https".equals(scheme)&&!("http".equals(scheme)&&local))
                ||(!uri.getPath().isEmpty()&&!uri.getPath().equals("/"))||uri.getPort()>65535||uri.getPort()==0)
                throw new IOException("Use the website HTTPS origin, or http://127.0.0.1:8000 through USB forwarding");
            return new URI(scheme,null,host.toLowerCase(java.util.Locale.ROOT),uri.getPort(),null,null,null).toString();
        } catch(java.net.URISyntaxException|IllegalArgumentException error) { throw new IOException("Enter a valid server origin",error); }
    }
}

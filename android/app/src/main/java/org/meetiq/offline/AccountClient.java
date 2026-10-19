package org.meetiq.offline;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import org.json.*;

/** Explicit account requests, with bounded responses and no cross-origin redirects. */
final class AccountClient {
    final String server,token;
    static final class Unauthorized extends IOException { Unauthorized() { super("Session expired. Sign in again; local meetings are retained."); } }
    AccountClient(String server,String token) throws IOException { this.server=SyncAddress.normalize(server); this.token=token; }
    private HttpURLConnection connection(String method,String path) throws IOException {
        if(!path.startsWith("/api/")) throw new IOException("Invalid account endpoint");
        HttpURLConnection connection=(HttpURLConnection)new URL(server+path).openConnection();
        connection.setConnectTimeout(15000); connection.setReadTimeout(60000); connection.setInstanceFollowRedirects(false);
        connection.setRequestMethod(method); connection.setRequestProperty("Accept","application/json");
        if(token!=null) connection.setRequestProperty("Authorization","Bearer "+token);
        return connection;
    }
    private static byte[] bytes(InputStream stream,int limit) throws IOException {
        try(InputStream in=stream;ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            if(in==null) return new byte[0]; byte[] block=new byte[65536]; int count;
            while((count=in.read(block))!=-1) { if(out.size()+(long)count>limit) throw new IOException("Server response exceeds the supported size"); out.write(block,0,count); }
            return out.toByteArray();
        }
    }
    private static void check(HttpURLConnection connection) throws Exception {
        int code=connection.getResponseCode(); if(code>=200&&code<300) return;
        if(code==401) throw new Unauthorized();
        String detail="Account request failed ("+code+")";
        if(code>=300&&code<400) detail="Redirect refused. Use the exact HTTPS website origin.";
        else try { JSONObject error=new JSONObject(new String(bytes(connection.getErrorStream(),65536),StandardCharsets.UTF_8));
            if(error.opt("detail") instanceof String) detail=error.getString("detail");
        } catch(IOException|JSONException ignored) { }
        throw new IOException(detail);
    }
    private static JSONObject response(HttpURLConnection connection) throws Exception {
        check(connection); return new JSONObject(new String(bytes(connection.getInputStream(),20*1024*1024),StandardCharsets.UTF_8));
    }
    JSONObject request(String method,String path,JSONObject body) throws Exception {
        HttpURLConnection connection=connection(method,path);
        try {
            if(body!=null) {
                byte[] encoded=body.toString().getBytes(StandardCharsets.UTF_8); connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type","application/json"); connection.setFixedLengthStreamingMode(encoded.length);
                try(OutputStream out=connection.getOutputStream()) { out.write(encoded); }
            }
            return response(connection);
        } finally { connection.disconnect(); }
    }
    JSONObject publish(JSONObject payload,File audio) throws Exception {
        String boundary="InfluenceIQ"+java.util.UUID.randomUUID().toString().replace("-","");
        HttpURLConnection connection=connection("POST","/api/sync/meetings");
        byte[] json=payload.toString().getBytes(StandardCharsets.UTF_8);
        if(json.length>20*1024*1024) throw new IOException("Report exceeds 20 MiB");
        byte[] head=("--"+boundary+"\r\nContent-Disposition: form-data; name=\"payload\"; filename=\"report.json\"\r\nContent-Type: application/json\r\n\r\n").getBytes(StandardCharsets.UTF_8);
        byte[] middle=("\r\n--"+boundary+"\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"audio.wav\"\r\nContent-Type: audio/wav\r\n\r\n").getBytes(StandardCharsets.UTF_8);
        byte[] end=("\r\n--"+boundary+"--\r\n").getBytes(StandardCharsets.UTF_8);
        try {
            connection.setDoOutput(true); connection.setRequestProperty("Content-Type","multipart/form-data; boundary="+boundary);
            connection.setFixedLengthStreamingMode((long)head.length+json.length+middle.length+audio.length()+end.length);
            try(OutputStream out=connection.getOutputStream();InputStream in=new FileInputStream(audio)) {
                out.write(head); out.write(json); out.write(middle); byte[] block=new byte[65536]; int count;
                while((count=in.read(block))!=-1) out.write(block,0,count); out.write(end);
            }
            return response(connection);
        } finally { connection.disconnect(); }
    }
    void audio(String meeting,File destination) throws Exception {
        if(!meeting.matches("[a-zA-Z0-9_-]+")) throw new IOException("Invalid account meeting ID");
        HttpURLConnection connection=connection("GET","/api/sync/meetings/"+meeting+"/audio");
        try {
            check(connection); long total=0;
            try(InputStream in=connection.getInputStream();FileOutputStream out=new FileOutputStream(destination)) {
                byte[] block=new byte[65536]; int count;
                while((count=in.read(block))!=-1) {
                    total+=count; if(total>700L*1024*1024) throw new IOException("Recording exceeds 700 MiB");
                    if(destination.getParentFile().getUsableSpace()<count+1024*1024) throw new IOException("Device storage is full");
                    out.write(block,0,count);
                } out.getFD().sync();
            }
        } finally { connection.disconnect(); }
    }
}

package org.meetiq.offline;

import android.content.Context;
import java.io.*;
import java.util.UUID;
import java.util.concurrent.*;
import org.json.*;

/** User-initiated transfers survive screen recreation; nothing is scheduled automatically. */
final class AccountSync {
    private interface Work { void run(Context context) throws Exception; }
    private static final ExecutorService executor=Executors.newSingleThreadExecutor();
    static volatile boolean busy;
    static volatile long revision;
    static volatile String message="", downloadedMeeting;
    static volatile JSONArray meetings=new JSONArray();
    private static synchronized void start(Context context,String status,Work work) {
        if(busy||MeetingService.busy||LocalTransfers.busy) return;
        Context app=context.getApplicationContext(); busy=true; message=status; downloadedMeeting=null; revision++;
        executor.execute(() -> {
            try { work.run(app); }
            catch(AccountClient.Unauthorized error) { AccountSession.clear(app); meetings=new JSONArray(); message="Could not sync: "+error.getMessage(); }
            catch(Exception error) { message="Could not sync: "+(error.getMessage()==null?error.getClass().getSimpleName():error.getMessage()); }
            finally { busy=false; revision++; }
        });
    }
    static void authenticate(Context context,String server,String email,String password,boolean register) {
        start(context,register?"Creating your shared account…":"Signing in…",app -> {
            AccountClient client=new AccountClient(server,null);
            JSONObject auth=client.request("POST",register?"/api/auth/register":"/api/auth/login",new JSONObject().put("email",email).put("password",password));
            AccountSession.save(app,client.server,auth); meetings=new JSONArray();
            message="Signed in. Recordings stay local until you choose Publish to account.";
            // A successful login remains usable if fetching optional profile/history fails.
            refreshData(app);
        });
    }
    private static void refreshData(Context app) throws Exception {
        AccountClient client=AccountSession.client(app);
        JSONObject identity=client.request("GET","/api/auth/me",null);
        if(!identity.getString("user_id").equals(AccountSession.preferences(app).getString("user_id","")))
            throw new AccountClient.Unauthorized();
        JSONObject profile=client.request("GET","/api/profile",null);
        AccountSession.preferences(app).edit().putString("profile",profile.toString()).commit();
        meetings=client.request("GET","/api/meetings",null).getJSONArray("meetings");
    }
    static void refresh(Context context) { start(context,"Refreshing account profile and meetings…",app -> { refreshData(app); message="Account is up to date. Local recordings were not uploaded."; }); }
    static void profile(Context context,JSONObject profile) { start(context,"Saving account profile…",app -> {
        AccountSession.client(app).request("POST","/api/profile",profile);
        AccountSession.preferences(app).edit().putString("profile",profile.toString()).commit(); message="Profile saved to your website account.";
    }); }
    static synchronized void signOut(Context context) {
        if(busy) return; AccountSession.clear(context); meetings=new JSONArray(); downloadedMeeting=null;
        message="Signed out. Device recordings and downloaded copies remain on this device."; revision++;
    }
    static void publish(Context context,String id) { start(context,"Publishing report and recording to your account…",app -> {
        MeetingRepository repository=new MeetingRepository(app.getFilesDir()); JSONObject meta=repository.metadata(id);
        String owner=AccountSession.owner(app);
        if(meta.has("sync_owner")&&!owner.equals(meta.getString("sync_owner"))) throw new IOException("This copy belongs to another server/account. Sign in to its original account.");
        if(!meta.has("sync_key")) meta.put("sync_key",UUID.randomUUID().toString()); meta.put("sync_owner",owner);
        MeetingService.atomic(repository.file(id,"metadata.json"),meta); // Persist retry identity before any network side effect.
        JSONObject report=new JSONObject(repository.report(id).toString());
        if(!report.optBoolean("completed")) throw new IOException("Complete analysis before publishing");
        for(String key:new String[]{"speaker_names","speaker_roles","vocabulary"}) if(meta.has(key)) report.put(key,meta.get(key));
        JSONObject payload=new JSONObject().put("client_key",meta.getString("sync_key")).put("title",meta.optString("title","Meeting "+id)).put("report",report);
        if(meta.has("remote_id")) payload.put("remote_id",meta.getString("remote_id")).put("base_revision",meta.getString("remote_revision"));
        JSONObject result=AccountSession.client(app).publish(payload,repository.file(id,"audio.wav"));
        meta.put("remote_id",result.getString("id")).put("remote_revision",result.getString("revision"));
        MeetingService.atomic(repository.file(id,"metadata.json"),meta);
        refreshData(app); message="Meeting published. It is now in your website account history.";
    }); }
    static void download(Context context,String remote) { start(context,"Downloading an offline meeting copy…",app -> {
        if(!remote.matches("[a-zA-Z0-9_-]+")) throw new IOException("Invalid account meeting");
        AccountClient client=AccountSession.client(app); JSONObject saved=client.request("GET","/api/meetings/"+remote,null);
        if(!saved.getString("status").equals("completed")) throw new IOException("Wait for this meeting to finish on the server");
        String owner=AccountSession.owner(app),version=saved.getString("revision");
        MeetingRepository repository=new MeetingRepository(app.getFilesDir());
        // Never overwrite local corrections; a newer account revision becomes a separate snapshot.
        for(MeetingRepository.Meeting meeting:repository.list()) {
            JSONObject meta=repository.metadata(meeting.id);
            if(meeting.completed&&meeting.audioExists&&owner.equals(meta.optString("sync_owner"))&&remote.equals(meta.optString("remote_id"))&&version.equals(meta.optString("remote_revision"))) {
                downloadedMeeting=meeting.id; message="This account revision is already available on this device."; return;
            }
        }
        JSONObject report=PortableReport.androidReport(saved.getJSONObject("data"));
        File temporary=new File(app.getFilesDir(),"account-download.tmp"),directory=null;
        try {
            client.audio(remote,temporary);
            File parent=new File(app.getFilesDir(),"meetings"); parent.mkdirs(); long timestamp=System.currentTimeMillis();
            do { directory=new File(parent,String.valueOf(timestamp++)); } while(directory.exists());
            if(!directory.mkdir()) throw new IOException("Could not create offline meeting folder");
            AudioImport.normalize(temporary,new File(directory,"audio.wav"));
            JSONObject meta=new JSONObject().put("title",saved.getString("title")).put("sync_owner",owner).put("sync_key",UUID.randomUUID().toString())
                .put("remote_id",remote).put("remote_revision",version).put("account_created_at",saved.optString("created_at"));
            for(String key:new String[]{"speaker_names","speaker_roles","vocabulary"}) if(report.has(key)) meta.put(key,report.get(key));
            MeetingService.atomic(new File(directory,"metadata.json"),meta); MeetingService.atomic(new File(directory,"report.json"),report);
            JSONArray slides=report.optJSONArray("slides");
            if(slides!=null) { JSONArray text=new JSONArray(); for(int i=0;i<slides.length();i++) text.put(slides.getJSONObject(i).optString("text")); MeetingService.atomic(new File(directory,"presentation.json"),new JSONObject().put("slides",text)); }
            downloadedMeeting=directory.getName(); message="Offline copy saved. Existing device copies were retained.";
        } catch(Exception error) {
            if(directory!=null) { File[] files=directory.listFiles(); if(files!=null) for(File file:files) file.delete(); directory.delete(); }
            throw error;
        } finally { temporary.delete(); }
    }); }
}

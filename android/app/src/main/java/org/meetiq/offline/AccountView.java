package org.meetiq.offline;

import android.app.Activity;
import android.content.*;
import android.text.InputType;
import android.text.InputFilter;
import android.widget.*;
import org.json.*;

/** Optional shared account UI; the local meeting library remains usable signed out. */
final class AccountView {
    private int limit=30;
    private EditText field(Ui ui,LinearLayout body,String label,String value,int maximum,int type) {
        ui.add(body,ui.text(label,14,ui.text,true),6); EditText input=ui.input(label,label,false);
        input.setInputType(type); input.setFilters(new InputFilter[]{new InputFilter.LengthFilter(maximum)}); input.setText(value); ui.add(body,input,12); return input;
    }
    private void button(Ui ui,LinearLayout body,String label,boolean primary,Runnable action) {
        Button button=ui.button(label,primary,action); ui.enabled(button,!AccountSync.busy&&!MeetingService.busy&&!LocalTransfers.busy); ui.add(body,button,12);
    }
    void render(Activity activity,Ui ui,LinearLayout body,Runnable back,Runnable redraw) {
        LinearLayout header=ui.row(); header.addView(ui.iconButton("back","Back",back));
        header.addView(ui.text("Account & sync",22,ui.text,true)); ui.add(body,header,20);
        ui.add(body,ui.notice("Offline first","Recording and analysis work without an account. Connect to the same server as the website to share your account and selected meetings.",false),16);
        if(!AccountSync.message.isEmpty()) ui.add(body,ui.notice(AccountSync.busy?"Connecting…":"Account status",AccountSync.message,AccountSync.message.startsWith("Could not")),14);
        android.content.SharedPreferences preferences=AccountSession.preferences(activity);
        if(!AccountSession.signedIn(activity)) {
            EditText server=field(ui,body,"Website server",preferences.getString("server",""),300,InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_URI);
            server.setHint("https://meetings.example.org");
            server.setImportantForAutofill(android.view.View.IMPORTANT_FOR_AUTOFILL_NO);
            EditText email=field(ui,body,"Account email","",254,InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
            EditText password=field(ui,body,"Account password","",64,InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
            email.setAutofillHints(android.view.View.AUTOFILL_HINT_USERNAME);
            password.setAutofillHints(android.view.View.AUTOFILL_HINT_PASSWORD);
            for(boolean register:new boolean[]{false,true}) button(ui,body,register?"Create shared account":"Sign in",!register,() -> {
                String address=server.getText().toString(),mail=email.getText().toString().trim(),secret=password.getText().toString();
                try { SyncAddress.normalize(address); } catch(Exception error) { server.setError(error.getMessage()); return; }
                if(!mail.contains("@")) { email.setError("Enter your account email"); return; }
                if(secret.isEmpty()||(register&&secret.length()<8)||secret.getBytes(java.nio.charset.StandardCharsets.UTF_8).length>72) { password.setError(register?"Use 8–64 characters, up to 72 UTF-8 bytes":"Enter your password, up to 72 UTF-8 bytes"); return; }
                password.setText(""); AccountSync.authenticate(activity,address,mail,secret,register); redraw.run();
            });
            ui.add(body,ui.text("Use the same email/password as the website. The server address must point to the same installation. First sign-in needs a connection; no recording is uploaded during sign-in.",14,ui.muted,false),18);
            return;
        }
        ui.add(body,ui.text(preferences.getString("email",""),18,ui.text,true),6);
        ui.add(body,ui.text(preferences.getString("server",""),13,ui.muted,false),16);
        button(ui,body,"Refresh account",false,() -> { AccountSync.refresh(activity); redraw.run(); });
        JSONObject profile;
        try { profile=new JSONObject(preferences.getString("profile","{}")); } catch(Exception ignored) { profile=new JSONObject(); }
        ui.add(body,ui.text("Shared profile",20,ui.text,true),14);
        EditText name=field(ui,body,"Account name",profile.optString("name"),100,InputType.TYPE_CLASS_TEXT);
        EditText role=field(ui,body,"Account role",profile.optString("role"),100,InputType.TYPE_CLASS_TEXT);
        EditText organization=field(ui,body,"Account organisation",profile.optString("organization"),200,InputType.TYPE_CLASS_TEXT);
        button(ui,body,"Save account profile",false,() -> {
            try { AccountSync.profile(activity,new JSONObject().put("name",name.getText().toString()).put("role",role.getText().toString()).put("organization",organization.getText().toString())); redraw.run(); }
            catch(JSONException error) { name.setError("Could not read the profile"); }
        });
        ui.add(body,ui.text("Account meetings",20,ui.text,true),8);
        ui.add(body,ui.text("Choose a meeting to save an offline copy with its recording. Newer account versions are saved separately to preserve device edits. Original PPTX files and model weights are not transferred.",14,ui.muted,false),16);
        JSONArray meetings=AccountSync.meetings;
        if(meetings.length()==0) ui.add(body,ui.text("No account meetings loaded. Refresh when connected. Publish a completed device meeting from its Meeting options.",14,ui.muted,false),14);
        for(int i=0;i<Math.min(limit,meetings.length());i++) {
            JSONObject meeting=meetings.optJSONObject(i); if(meeting==null) continue;
            String id=meeting.optString("id"),title=meeting.optString("title","Meeting"),status=meeting.optString("status");
            android.view.View row=ui.action("document",title,status.equals("completed")?"Save offline copy":"Server status: "+status,false,() -> { AccountSync.download(activity,id); redraw.run(); });
            row.setContentDescription("Download account meeting "+title); ui.enabled(row,status.equals("completed")&&!AccountSync.busy&&!MeetingService.busy&&!LocalTransfers.busy); ui.add(body,row,12);
        }
        if(meetings.length()>limit) button(ui,body,"Show more account meetings",false,() -> { limit+=30; redraw.run(); });
        button(ui,body,"Open website",false,() -> {
            try { activity.startActivity(new Intent(Intent.ACTION_VIEW,android.net.Uri.parse(preferences.getString("server","")))); }
            catch(ActivityNotFoundException ignored) { android.widget.Toast.makeText(activity,"Install a browser to open the website",Toast.LENGTH_SHORT).show(); }
        });
        button(ui,body,"Sign out",false,() -> { AccountSync.signOut(activity); limit=30; redraw.run(); });
        ui.add(body,ui.text("Signing out removes this account session. Device recordings and downloaded copies remain in the device library. Shared-device users should manage those copies separately.",13,ui.muted,false),12);
    }
}

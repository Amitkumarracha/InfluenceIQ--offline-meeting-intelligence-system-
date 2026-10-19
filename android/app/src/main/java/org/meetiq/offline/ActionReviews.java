package org.meetiq.offline;

import org.json.*;
import java.util.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.io.IOException;

/** Explicit user corrections; never infer the task owner from its speaker. */
final class ActionReviews {
    static Map<String,JSONObject> candidates(JSONObject report) {
        JSONArray rows=report.optJSONArray("action_items");
        boolean filtered=rows!=null;
        if(rows==null) rows=report.optJSONArray("events");
        if(rows==null) rows=report.optJSONArray("event_timeline");
        Map<String,JSONObject> result=new LinkedHashMap<>();
        if(rows!=null) for(int i=0;i<rows.length();i++) {
            JSONObject item=rows.optJSONObject(i);
            if(item!=null&&(filtered||item.optString("event_type").equals("action_item"))&&!item.optString("event_id").isEmpty()) result.put(item.optString("event_id"),item);
        }
        return result;
    }
    static Double start(JSONObject item) {
        Object raw=item.opt("start"); if(raw==null||raw==JSONObject.NULL) raw=item.opt("timestamp_s");
        if(raw==null||raw==JSONObject.NULL) raw=item.opt("timestamp");
        if(raw instanceof String&&((String)raw).matches("[0-9]+:[0-9]{2}:[0-9]{2}(\\.[0-9]+)?")) {
            String[] parts=((String)raw).split(":");
            try { raw=Double.parseDouble(parts[0])*3600+Double.parseDouble(parts[1])*60+Double.parseDouble(parts[2]); }
            catch(NumberFormatException error) { return null; }
        }
        if(!(raw instanceof Number)) return null;
        double value=((Number)raw).doubleValue(); return Double.isFinite(value)&&value>=0?value+0.0:null;
    }
    static JSONObject make(JSONObject action,String owner,String due,String state) throws Exception {
        if(owner==null||owner.length()>100) throw new IOException("Use an owner label of up to 100 characters");
        for(int i=0;i<owner.length();i++) if(owner.charAt(i)<32||owner.charAt(i)==127) throw new IOException("Owner labels cannot contain control characters");
        if(!Arrays.asList("open","done","dismissed").contains(state)) throw new IOException("Choose open, done or dismissed");
        if(due==null) throw new IOException("Use a date in YYYY-MM-DD format");
        if(!due.isEmpty()) {
            try {
                if(!due.matches("[0-9]{4}-[0-9]{2}-[0-9]{2}")) throw new IllegalArgumentException();
                LocalDate value=LocalDate.parse(due); if(value.getYear()<1||value.getYear()>9998) throw new IllegalArgumentException();
            } catch(Exception error) { throw new IOException("Enter a valid due date in YYYY-MM-DD format"); }
        }
        Double seconds=start(action);
        return new JSONObject().put("owner",owner.trim()).put("due_date",due).put("state",state).put("human_reviewed",true)
            .put("source_text",action.optString("text")).put("source_start",seconds==null?JSONObject.NULL:seconds);
    }
    static JSONObject active(JSONObject report,JSONObject action) {
        JSONObject reviews=report.optJSONObject("action_reviews"),value=reviews==null?null:reviews.optJSONObject(action.optString("event_id"));
        if(value==null||!Boolean.TRUE.equals(value.opt("human_reviewed"))||!value.optString("source_text").equals(action.optString("text"))) return null;
        Object raw=value.opt("source_start"); Double seconds=raw instanceof Number?((Number)raw).doubleValue()+0.0:null;
        if(!Objects.equals(seconds,start(action))) return null;
        try { return make(action,value.optString("owner"),value.optString("due_date"),value.optString("state")); }
        catch(Exception error) { return null; }
    }
    private static String escape(String text) {
        return text.replaceAll("[\\x00-\\x09\\x0B\\x0C\\x0E-\\x1F\\x7F]","").replace("\\","\\\\")
            .replace("\r\n","\n").replace('\r','\n').replace("\n","\\n").replace(";","\\;").replace(",","\\,");
    }
    static String calendar(JSONObject report,String title,String meetingId) throws Exception {
        List<String> lines=new ArrayList<>(Arrays.asList("BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//InfluenceIQ//Offline Follow-ups//EN","CALSCALE:GREGORIAN"));
        String stamp=DateTimeFormatter.ofPattern("uuuuMMdd'T'HHmmss'Z'",Locale.ROOT).withZone(ZoneOffset.UTC).format(Instant.now());
        for(Map.Entry<String,JSONObject> entry:candidates(report).entrySet()) {
            JSONObject action=entry.getValue(),review=active(report,action);
            if(review==null||!review.optString("state").equals("open")||review.optString("due_date").isEmpty()) continue;
            LocalDate due=LocalDate.parse(review.getString("due_date")); String identity=meetingId+"\n"+entry.getKey()+"\n"+action.optString("text");
            byte[] hash=MessageDigest.getInstance("SHA-256").digest(identity.getBytes(StandardCharsets.UTF_8)); StringBuilder uid=new StringBuilder();
            for(byte b:hash) uid.append(String.format(Locale.ROOT,"%02x",b&255));
            String owner=review.optString("owner"),description="Meeting: "+title+"\nOwner: "+(owner.isEmpty()?"Unassigned":owner)+"\nSource seconds: "+start(action)+"\nUser-reviewed follow-up. Verify the original recording.";
            lines.addAll(Arrays.asList("BEGIN:VEVENT","UID:"+uid+"@influenceiq.local","DTSTAMP:"+stamp,
                "DTSTART;VALUE=DATE:"+due.format(DateTimeFormatter.BASIC_ISO_DATE),"DTEND;VALUE=DATE:"+due.plusDays(1).format(DateTimeFormatter.BASIC_ISO_DATE),
                "SUMMARY:"+escape(action.optString("text")),"DESCRIPTION:"+escape(description),"TRANSP:TRANSPARENT","END:VEVENT"));
        }
        if(!lines.contains("BEGIN:VEVENT")) throw new IOException("Review an open action item and set its due date before exporting a calendar");
        lines.add("END:VCALENDAR"); StringBuilder result=new StringBuilder();
        for(String line:lines) {
            int length=0;
            for(int index=0;index<line.length();) {
                int code=line.codePointAt(index); String character=new String(Character.toChars(code)); int bytes=character.getBytes(StandardCharsets.UTF_8).length;
                if(length+bytes>75) { result.append("\r\n "); length=1; }
                result.append(character); length+=bytes; index+=Character.charCount(code);
            }
            result.append("\r\n");
        }
        return result.toString();
    }
}

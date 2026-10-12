package org.meetiq.offline;

import android.content.Context;
import android.content.res.Configuration;
import android.content.res.ColorStateList;
import android.graphics.*;
import android.graphics.drawable.*;
import android.view.*;
import android.widget.*;

/** Local framework widgets, palette and vector drawing; no downloaded assets. */
final class Ui {
    final Context context;
    final boolean dark;
    final int background, card, border, text, muted, accent, blue, onAccent, warning, warningText;
    Ui(Context context) {
        this.context=context;
        dark=(context.getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK)==Configuration.UI_MODE_NIGHT_YES;
        background=color(dark?"#0D1B1D":"#F6F8F7"); card=color(dark?"#162A2B":"#FFFFFF");
        border=color(dark?"#263D4F":"#D8E3EC"); text=color(dark?"#F1F7FD":"#142C3D");
        muted=color(dark?"#A4BBD0":"#526B7D"); accent=color(dark?"#22D9C7":"#007E75");
        blue=color(dark?"#65B7FF":"#176EC1"); onAccent=color(dark?"#052830":"#FFFFFF");
        warning=color(dark?"#302514":"#FFF3DA"); warningText=color(dark?"#FFD894":"#654314");
    }
    static int color(String value) { return Color.parseColor(value); }
    int dp(float value) { return Math.round(value*context.getResources().getDisplayMetrics().density); }
    LinearLayout column() { LinearLayout v=new LinearLayout(context); v.setOrientation(LinearLayout.VERTICAL); return v; }
    LinearLayout row() { LinearLayout v=new LinearLayout(context); v.setOrientation(LinearLayout.HORIZONTAL); v.setGravity(Gravity.CENTER_VERTICAL); return v; }
    TextView text(String value,float size,int color,boolean bold) {
        TextView v=new TextView(context); v.setText(value); v.setTextSize(size); v.setTextColor(color);
        v.setFontFeatureSettings("kern"); v.setIncludeFontPadding(false); v.setLineSpacing(dp(3),1);
        v.setTypeface(Typeface.create(bold?"sans-serif-medium":"sans-serif",Typeface.NORMAL));
        return v;
    }
    void add(LinearLayout parent,View view,int bottom) {
        LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,-2); params.bottomMargin=dp(bottom); parent.addView(view,params);
    }
    void space(LinearLayout parent,int height) { parent.addView(new View(context),new LinearLayout.LayoutParams(1,dp(height))); }
    GradientDrawable shape(int fill,int stroke,int radius) {
        GradientDrawable drawable=new GradientDrawable(); drawable.setColor(fill); drawable.setCornerRadius(dp(radius));
        if (stroke!=0) drawable.setStroke(dp(1),stroke); return drawable;
    }
    Drawable touch(int fill,int stroke,int radius) {
        GradientDrawable shape=shape(fill,stroke,radius);
        return new RippleDrawable(ColorStateList.valueOf(dark?0x33FFFFFF:0x18000000),shape,null);
    }
    LinearLayout card() {
        LinearLayout view=column(); view.setPadding(dp(16),dp(16),dp(16),dp(16)); view.setBackground(shape(card,border,18)); return view;
    }
    TextView chip(String label,int foreground,int fill) {
        TextView v=text(label,12,foreground,true); v.setPadding(dp(10),dp(7),dp(10),dp(7));
        v.setBackground(shape(fill,0,14)); return v;
    }
    Button button(String label,boolean primary,Runnable action) {
        Button v=new Button(context); v.setText(label); v.setAllCaps(false); v.setTextSize(15); v.setTypeface(Typeface.create("sans-serif-medium",0));
        v.setStateListAnimator(null); v.setLetterSpacing(0); v.setTextColor(primary?onAccent:text); v.setMinHeight(dp(52)); v.setMinimumWidth(0); v.setMinWidth(0);
        v.setPadding(dp(16),dp(12),dp(16),dp(12)); v.setBackground(touch(primary?accent:card,primary?0:border,16));
        v.setContentDescription(label); v.setOnClickListener(view -> action.run()); return v;
    }
    void enabled(View view,boolean enabled) { if(view.isEnabled()!=enabled) view.setEnabled(enabled); float opacity=enabled?1:.42f; if(view.getAlpha()!=opacity) view.setAlpha(opacity); }
    View iconButton(String name,String description,Runnable action) {
        Icon icon=new Icon(context,name,text); icon.setPadding(dp(13),dp(13),dp(13),dp(13));
        icon.setLayoutParams(new LinearLayout.LayoutParams(dp(48),dp(48))); icon.setBackground(touch(Color.TRANSPARENT,0,24));
        icon.setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_YES);
        icon.setContentDescription(description); icon.setFocusable(true); icon.setOnClickListener(view -> action.run()); return icon;
    }
    View action(String icon,String title,String subtitle,boolean primary,Runnable action) {
        LinearLayout row=row(); row.setPadding(dp(16),dp(17),dp(14),dp(17)); row.setMinimumHeight(dp(76));
        row.setBackground(touch(primary?accent:card,primary?0:border,18));
        int foreground=primary?onAccent:text;
        Icon image=new Icon(context,icon,primary?onAccent:blue); row.addView(image,new LinearLayout.LayoutParams(dp(34),dp(34)));
        LinearLayout labels=column(); labels.setPadding(dp(15),0,dp(10),0);
        add(labels,text(title,17,foreground,true),5); add(labels,text(subtitle,13,primary?onAccent:muted,false),0);
        row.addView(labels,new LinearLayout.LayoutParams(0,-2,1));
        Icon arrow=new Icon(context,"chevron",primary?onAccent:muted); row.addView(arrow,new LinearLayout.LayoutParams(dp(18),dp(18)));
        row.setContentDescription(title); row.setFocusable(true); row.setOnClickListener(view -> action.run()); return row;
    }
    EditText input(String hint,String description,boolean multiline) {
        EditText view=new EditText(context); view.setTextSize(16); view.setTextColor(text); view.setHintTextColor(muted);
        view.setHint(hint); view.setContentDescription(description); view.setPadding(dp(14),dp(13),dp(14),dp(13));
        view.setBackground(shape(card,border,12)); view.setMinHeight(dp(50));
        view.setSingleLine(!multiline); if (multiline) { view.setMinLines(3); view.setGravity(Gravity.TOP); }
        view.setBackgroundTintList(null); return view;
    }
    LinearLayout notice(String title,String body,boolean alert) {
        LinearLayout box=card(); box.setBackground(shape(alert?warning:card,alert?color(dark?"#795722":"#E5C68C"):border,16));
        LinearLayout row=row(); Icon icon=new Icon(context,alert?"warning":"lock",alert?warningText:accent);
        row.addView(icon,new LinearLayout.LayoutParams(dp(24),dp(24)));
        TextView heading=text(title,14,alert?warningText:text,true); heading.setPadding(dp(10),0,0,0);
        row.addView(heading,new LinearLayout.LayoutParams(0,-2,1)); add(box,row,8);
        add(box,text(body,14,alert?warningText:muted,false),0); return box;
    }

    static final class Icon extends View {
        final String name; final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        Icon(Context context,String name,int color) { super(context); this.name=name; paint.setColor(color); setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO); }
        private void line(Canvas c,float a,float b,float x,float y) { c.drawLine(a,b,x,y,paint); }
        private void path(Canvas c,float... points) {
            Path path=new Path(); path.moveTo(points[0],points[1]); for(int i=2;i<points.length;i+=2) path.lineTo(points[i],points[i+1]); c.drawPath(path,paint);
        }
        protected void onDraw(Canvas canvas) {
            super.onDraw(canvas); canvas.save(); canvas.translate(getPaddingLeft(),getPaddingTop());
            canvas.scale((getWidth()-getPaddingLeft()-getPaddingRight())/24f,(getHeight()-getPaddingTop()-getPaddingBottom())/24f);
            paint.setStyle(Paint.Style.STROKE); paint.setStrokeWidth(1.7f); paint.setStrokeCap(Paint.Cap.ROUND); paint.setStrokeJoin(Paint.Join.ROUND);
            switch(name) {
                case "mic": canvas.drawRoundRect(8,2,16,15,4,4,paint); canvas.drawArc(5,7,19,19,0,180,false,paint); line(canvas,12,19,12,23); line(canvas,8,23,16,23); break;
                case "lock": canvas.drawRoundRect(5,10,19,22,3,3,paint); canvas.drawArc(8,2,16,15,180,180,false,paint); line(canvas,12,15,12,18); break;
                case "model": path(canvas,12,2,21,7,21,17,12,22,3,17,3,7,12,2); path(canvas,3,7,12,12,21,7); line(canvas,12,12,12,22); path(canvas,7,5,16,10,16,15); break;
                case "settings": canvas.drawCircle(12,12,7,paint); canvas.drawCircle(12,12,2.5f,paint); for(int i=0;i<8;i++) { double a=i*Math.PI/4; line(canvas,(float)(12+7*Math.cos(a)),(float)(12+7*Math.sin(a)),(float)(12+10*Math.cos(a)),(float)(12+10*Math.sin(a))); } break;
                case "clock": canvas.drawCircle(12,12,9,paint); path(canvas,12,6,12,12,16,14); break;
                case "play": paint.setStyle(Paint.Style.FILL); Path p=new Path(); p.moveTo(8,4); p.lineTo(20,12); p.lineTo(8,20); p.close(); canvas.drawPath(p,paint); break;
                case "pause": paint.setStyle(Paint.Style.FILL); canvas.drawRoundRect(6,4,10,20,1,1,paint); canvas.drawRoundRect(14,4,18,20,1,1,paint); break;
                case "stop": paint.setStyle(Paint.Style.FILL); canvas.drawRoundRect(5,5,19,19,3,3,paint); break;
                case "close": line(canvas,5,5,19,19); line(canvas,19,5,5,19); break;
                case "back": path(canvas,14,5,7,12,14,19); line(canvas,7,12,21,12); break;
                case "chevron": path(canvas,9,5,16,12,9,19); break;
                case "edit": path(canvas,5,16,16,5,20,9,9,20,4,21,5,16); line(canvas,14,7,18,11); break;
                case "search": canvas.drawCircle(10,10,7,paint); line(canvas,15,15,22,22); break;
                case "check": path(canvas,4,12,9,17,20,5); break;
                case "more": paint.setStyle(Paint.Style.FILL); for(int y=5;y<22;y+=7) canvas.drawCircle(12,y,1.4f,paint); break;
                case "export": path(canvas,12,3,12,16); path(canvas,7,11,12,16,17,11); path(canvas,4,16,4,21,20,21,20,16); break;
                case "wave": for(int x=3;x<24;x+=4) { int h=x==11?10:x==7||x==15?6:3; line(canvas,x,12-h,x,12+h); } break;
                case "flag": path(canvas,5,22,5,3,19,3,16,8,19,13,5,13); break;
                case "warning": path(canvas,12,2,23,22,1,22,12,2); line(canvas,12,8,12,14); canvas.drawCircle(12,18,.5f,paint); break;
                default: path(canvas,5,2,15,2,21,8,21,22,5,22,5,2); path(canvas,15,2,15,8,21,8); line(canvas,9,13,17,13); line(canvas,9,17,16,17); break;
            }
            canvas.restore();
        }
    }
    static final class Waveform extends View {
        private final float[] levels=new float[48]; private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        private int first;
        Waveform(Context context,int color) { super(context); paint.setColor(color); paint.setStrokeCap(Paint.Cap.ROUND); setContentDescription("Live microphone input level"); }
        void push(float level) { levels[first]=Math.min(1,level*5); first=(first+1)%levels.length; invalidate(); }
        protected void onDraw(Canvas canvas) {
            float gap=getWidth()/(float)levels.length; paint.setStrokeWidth(Math.max(2,gap*.36f));
            for(int i=0;i<levels.length;i++) { float height=Math.max(2,levels[(first+i)%levels.length]*getHeight()*.45f); canvas.drawLine((i+.5f)*gap,getHeight()/2f-height,(i+.5f)*gap,getHeight()/2f+height,paint); }
        }
    }
}

package org.meetiq.offline;

import java.text.Normalizer;
import java.util.*;
import java.util.regex.*;

/** Sparse TF-IDF text fusion. Scores are lexical similarity, not confidence. */
final class SlideIndex {
    // Explicit Unicode categories work on both Android ICU and the JVM.
    private static final Pattern WORD=Pattern.compile("[\\p{L}\\p{M}\\p{N}]+");
    private static final Set<String> STOP=new HashSet<>(Arrays.asList(
        "a","an","the","and","or","to","of","in","for","is","it","we","i","you","this","that","on","be","will","have","are",
        "hai","hain","ka","ki","ke","ko","se","aur","hum","ye","है","हैं","का","की","के","को","से","और",
        "agreed","agree","decided","decide","choose","chosen","use","using","need","want","should","reduce","increase","change","make",
        "project","meeting","data","shows","show","said","says","think","kar","karenge","hoga","chahiye"));
    private final Map<String,Double> idf=new HashMap<>();
    private final Map<String,Map<Integer,Double>> postings=new HashMap<>();
    private final int size;
    static Map<String,Integer> tokens(String text) {
        Map<String,Integer> count=new HashMap<>();
        Matcher words=WORD.matcher(Normalizer.normalize(text,Normalizer.Form.NFKC).toLowerCase(Locale.ROOT));
        while(words.find()) { String word=words.group(); if(!STOP.contains(word)) count.put(word,count.getOrDefault(word,0)+1); }
        return count;
    }
    static boolean related(String a,String b) {
        Set<String> first=tokens(a).keySet(), second=tokens(b).keySet();
        int common=0; for(String term:first) if(second.contains(term)) common++;
        return common>0 && common/(double)Math.max(1,Math.min(first.size(),second.size()))>=0.2;
    }
    SlideIndex(List<String> texts) {
        size=texts.size(); Map<String,Integer> frequency=new HashMap<>();
        for(String text:texts) for(String term:tokens(text).keySet()) frequency.put(term,frequency.getOrDefault(term,0)+1);
        for(Map.Entry<String,Integer> term:frequency.entrySet()) idf.put(term.getKey(),1+Math.log((1.0+size)/(1.0+term.getValue())));
        for(int i=0;i<size;i++) for(Map.Entry<String,Double> term:vector(texts.get(i)).entrySet())
            postings.computeIfAbsent(term.getKey(),key -> new HashMap<>()).put(i,term.getValue());
    }
    private Map<String,Double> vector(String text) {
        Map<String,Double> values=new HashMap<>(); double norm=0;
        for(Map.Entry<String,Integer> term:tokens(text).entrySet()) if(idf.containsKey(term.getKey())) {
            double value=(1+Math.log(term.getValue()))*idf.get(term.getKey()); values.put(term.getKey(),value); norm+=value*value;
        }
        if(norm>0) { double length=Math.sqrt(norm); values.replaceAll((key,value) -> value/length); }
        return values;
    }
    double[] scores(String text) {
        double[] scores=new double[size];
        for(Map.Entry<String,Double> term:vector(text).entrySet()) for(Map.Entry<Integer,Double> hit:postings.get(term.getKey()).entrySet())
            scores[hit.getKey()]+=term.getValue()*hit.getValue();
        for(int i=0;i<size;i++) scores[i]=Math.min(1,Math.max(0,scores[i]));
        return scores;
    }
}

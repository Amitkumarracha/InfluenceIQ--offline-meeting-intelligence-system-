package org.meetiq.offline;

import java.text.Normalizer;
import java.util.*;
import java.util.regex.*;

/** Suggestions are observed words; they remain editable and are not entity claims. */
public final class Vocabulary {
    private static final Set<String> COMMON=new HashSet<>(Arrays.asList(("the and that this with from have has had will would could should can not yes so but are was were for you your our they their we what when how who why about just also really now going want think know like okay right yeah well thank thanks all some one two see say said make need use good time today tomorrow send report meeting "
        +"है हैं हूँ हूं था थी थे में से के की का को और पर यह वह हम मैं आप नहीं भी तो लिए एक क्या करना करेंगे main mai mein hum aap hai hain ka ki ke ko se aur nahi haan toh bhi kar karo karna karenge").split(" ")));
    public static List<String> suggest(Collection<String> texts) {
        Map<String,Integer> counts=new LinkedHashMap<>();
        Pattern words=Pattern.compile("[\\p{L}\\p{N}][\\p{L}\\p{N}\\p{M}]*");
        for(String text:texts) {
            Matcher matcher=words.matcher(Normalizer.normalize(text,Normalizer.Form.NFKC).toLowerCase(Locale.ROOT));
            while(matcher.find()) { String term=matcher.group(); if(term.length()>=3&&!COMMON.contains(term)&&!term.matches("[\\p{N}]+")) counts.put(term,counts.getOrDefault(term,0)+1); }
        }
        List<String> result=new ArrayList<>(counts.keySet()); result.sort((a,b) -> Integer.compare(counts.get(b),counts.get(a)));
        return new ArrayList<>(result.subList(0,Math.min(20,result.size())));
    }
}

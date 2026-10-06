package org.meetiq.offline;

import java.text.Normalizer;
import java.util.*;
import java.util.regex.Pattern;

/** Shared phrase candidates. No inference of agreement, identity or task ownership. */
final class EventRules {
    private final Map<String, List<Pattern>> patterns;
    private final Map<String, List<Pattern>> blockers;

    EventRules(Map<String, List<String>> rules, Map<String, List<String>> excluded) {
        patterns = compile(rules); blockers = compile(excluded);
    }

    private static Map<String, List<Pattern>> compile(Map<String, List<String>> source) {
        Map<String, List<Pattern>> result = new LinkedHashMap<>();
        for (Map.Entry<String, List<String>> entry : source.entrySet()) {
            List<Pattern> bank = new ArrayList<>();
            for (String pattern : entry.getValue()) bank.add(Pattern.compile(pattern, Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE));
            result.put(entry.getKey(), bank);
        }
        return result;
    }

    private static boolean matches(List<Pattern> bank, String text) {
        if (bank != null) for (Pattern pattern : bank) if (pattern.matcher(text).find()) return true;
        return false;
    }

    List<String> eventTypes(String source) {
        String text = Normalizer.normalize(source, Normalizer.Form.NFKC).toLowerCase(Locale.ROOT).replace('’', '\'').trim();
        List<String> result = new ArrayList<>();
        for (Map.Entry<String, List<Pattern>> entry : patterns.entrySet()) {
            if (!matches(blockers.get(entry.getKey()), text) && matches(entry.getValue(), text)) result.add(entry.getKey());
        }
        return result;
    }
}

package org.meetiq.offline;

import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** Runs the actual exported Python/Android phrase banks without Android runtime. */
public final class EventRulesTest {
    public static void main(String[] args) throws Exception {
        Map<String,List<String>> rules = new LinkedHashMap<>(), blockers = new LinkedHashMap<>();
        for (String line : Files.readAllLines(Paths.get(args[0]), StandardCharsets.UTF_8)) {
            String[] parts = line.split("\t", 3);
            Map<String,List<String>> bank = parts[0].equals("block") ? blockers : rules;
            if (!bank.containsKey(parts[1])) bank.put(parts[1], new ArrayList<>());
            bank.get(parts[1]).add(parts[2]);
        }
        EventRules engine = new EventRules(rules, blockers);
        expect(engine, "हमने बजट फाइनल कर दिया।", "decision", true);
        expect(engine, "mein report kal bhej dungi", "action_item", true);
        expect(engine, "aap report review kar dena", "action_item", true);
        expect(engine, "Have we decided to launch?", "decision", false);
        expect(engine, "क्या हमने तय किया?", "decision", false);
        expect(engine, "humne decide nahi kiya", "decision", false);
        expect(engine, "I do not agree.", "agreement", false);
        expect(engine, "bilkul sahi nahi hai", "agreement", false);
        expect(engine, "main report nahi bhej dunga", "action_item", false);
        expect(engine, "We decided not to launch.", "decision", true);
        expect(engine, "I’ll send the report.", "action_item", true);
        System.out.println("Android bilingual checks passed: shared banks, Hindi/Hinglish, questions, negation.");
    }

    private static void expect(EventRules engine, String text, String type, boolean present) {
        if (engine.eventTypes(text).contains(type) != present) throw new AssertionError(type + ": " + text);
    }
}

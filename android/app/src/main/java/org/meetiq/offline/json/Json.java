package org.meetiq.offline.json;

import java.util.*;

public class Json {
    public static Object parse(String text) {
        if (text == null || text.trim().isEmpty()) return null;
        return new Parser(text).parse();
    }

    public static String write(Object value) {
        StringBuilder sb = new StringBuilder();
        write(value, sb, 0, false);
        return sb.toString();
    }

    public static String write(Object value, int indent) {
        StringBuilder sb = new StringBuilder();
        write(value, sb, indent, true);
        return sb.toString();
    }

    @SuppressWarnings("unchecked")
    public static Map<String, Object> obj(Object v) {
        return v instanceof Map ? (Map<String, Object>) v : null;
    }

    @SuppressWarnings("unchecked")
    public static List<Object> arr(Object v) {
        return v instanceof List ? (List<Object>) v : null;
    }

    public static double num(Object v, double dflt) {
        if (v instanceof Number) return ((Number) v).doubleValue();
        return dflt;
    }

    public static String str(Object v, String dflt) {
        if (v instanceof String) return (String) v;
        return dflt;
    }

    private static void write(Object v, StringBuilder sb, int indent, boolean pretty) {
        if (v == null) {
            sb.append("null");
        } else if (v instanceof Boolean || v instanceof Number) {
            sb.append(v);
        } else if (v instanceof String) {
            sb.append('"');
            String s = (String) v;
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"': sb.append("\\\""); break;
                    case '\\': sb.append("\\\\"); break;
                    case '\b': sb.append("\\b"); break;
                    case '\f': sb.append("\\f"); break;
                    case '\n': sb.append("\\n"); break;
                    case '\r': sb.append("\\r"); break;
                    case '\t': sb.append("\\t"); break;
                    default:
                        if (c < 32) {
                            sb.append(String.format("\\u%04x", (int) c));
                        } else {
                            sb.append(c);
                        }
                }
            }
            sb.append('"');
        } else if (v instanceof List) {
            sb.append('[');
            List<?> list = (List<?>) v;
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(',');
                if (pretty) sb.append('\n').append(pad(indent + 2));
                write(list.get(i), sb, pretty ? indent + 2 : 0, pretty);
            }
            if (pretty && !list.isEmpty()) sb.append('\n').append(pad(indent));
            sb.append(']');
        } else if (v instanceof Map) {
            sb.append('{');
            Map<?, ?> map = (Map<?, ?>) v;
            boolean first = true;
            for (Map.Entry<?, ?> e : map.entrySet()) {
                if (!first) sb.append(',');
                first = false;
                if (pretty) sb.append('\n').append(pad(indent + 2));
                write(String.valueOf(e.getKey()), sb, 0, false);
                sb.append(pretty ? ": " : ":");
                write(e.getValue(), sb, pretty ? indent + 2 : 0, pretty);
            }
            if (pretty && !map.isEmpty()) sb.append('\n').append(pad(indent));
            sb.append('}');
        } else if (v instanceof float[]) {
            sb.append('[');
            float[] a = (float[]) v;
            for (int i = 0; i < a.length; i++) {
                if (i > 0) sb.append(',');
                sb.append(a[i]);
            }
            sb.append(']');
        } else if (v instanceof double[]) {
            sb.append('[');
            double[] a = (double[]) v;
            for (int i = 0; i < a.length; i++) {
                if (i > 0) sb.append(',');
                sb.append(a[i]);
            }
            sb.append(']');
        } else if (v instanceof int[]) {
            sb.append('[');
            int[] a = (int[]) v;
            for (int i = 0; i < a.length; i++) {
                if (i > 0) sb.append(',');
                sb.append(a[i]);
            }
            sb.append(']');
        } else {
            write(String.valueOf(v), sb, 0, false);
        }
    }

    private static String pad(int n) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.append(' ');
        return sb.toString();
    }

    private static class Parser {
        private final String s;
        private int i;

        Parser(String s) {
            this.s = s;
            this.i = 0;
        }

        Object parse() {
            skip();
            if (i >= s.length()) return null;
            char c = s.charAt(i);
            if (c == '{') return parseObject();
            if (c == '[') return parseArray();
            if (c == '"') return parseString();
            if (c == 't') { match("true"); return Boolean.TRUE; }
            if (c == 'f') { match("false"); return Boolean.FALSE; }
            if (c == 'n') { match("null"); return null; }
            if (c == '-' || (c >= '0' && c <= '9')) return parseNumber();
            throw new RuntimeException("Unexpected char: " + c + " at " + i);
        }

        private Map<String, Object> parseObject() {
            Map<String, Object> map = new LinkedHashMap<>();
            i++; // '{'
            skip();
            if (i < s.length() && s.charAt(i) == '}') {
                i++;
                return map;
            }
            while (i < s.length()) {
                skip();
                String key = parseString();
                skip();
                if (i >= s.length() || s.charAt(i) != ':') throw new RuntimeException("Expected ':' at " + i);
                i++;
                skip();
                Object val = parse();
                map.put(key, val);
                skip();
                if (i < s.length() && s.charAt(i) == '}') {
                    i++;
                    break;
                }
                if (i >= s.length() || s.charAt(i) != ',') throw new RuntimeException("Expected ',' or '}' at " + i);
                i++;
            }
            return map;
        }

        private List<Object> parseArray() {
            List<Object> list = new ArrayList<>();
            i++; // '['
            skip();
            if (i < s.length() && s.charAt(i) == ']') {
                i++;
                return list;
            }
            while (i < s.length()) {
                list.add(parse());
                skip();
                if (i < s.length() && s.charAt(i) == ']') {
                    i++;
                    break;
                }
                if (i >= s.length() || s.charAt(i) != ',') throw new RuntimeException("Expected ',' or ']' at " + i);
                i++;
            }
            return list;
        }

        private String parseString() {
            i++; // '"'
            StringBuilder sb = new StringBuilder();
            while (i < s.length()) {
                char c = s.charAt(i++);
                if (c == '"') return sb.toString();
                if (c == '\\') {
                    if (i >= s.length()) throw new RuntimeException("Unterminated escape");
                    c = s.charAt(i++);
                    switch (c) {
                        case '"': case '\\': case '/': sb.append(c); break;
                        case 'b': sb.append('\b'); break;
                        case 'f': sb.append('\f'); break;
                        case 'n': sb.append('\n'); break;
                        case 'r': sb.append('\r'); break;
                        case 't': sb.append('\t'); break;
                        case 'u':
                            if (i + 4 > s.length()) throw new RuntimeException("Invalid unicode escape");
                            sb.append((char) Integer.parseInt(s.substring(i, i + 4), 16));
                            i += 4;
                            break;
                        default: throw new RuntimeException("Invalid escape \\" + c);
                    }
                } else {
                    sb.append(c);
                }
            }
            throw new RuntimeException("Unterminated string");
        }

        private Number parseNumber() {
            int start = i;
            while (i < s.length()) {
                char c = s.charAt(i);
                if (c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E' || (c >= '0' && c <= '9')) {
                    i++;
                } else {
                    break;
                }
            }
            String num = s.substring(start, i);
            if (num.contains(".") || num.contains("e") || num.contains("E")) {
                return Double.parseDouble(num);
            }
            long l = Long.parseLong(num);
            if (l >= Integer.MIN_VALUE && l <= Integer.MAX_VALUE) return (int) l;
            return l;
        }

        private void match(String expected) {
            if (i + expected.length() > s.length() || !s.substring(i, i + expected.length()).equals(expected)) {
                throw new RuntimeException("Expected " + expected + " at " + i);
            }
            i += expected.length();
        }

        private void skip() {
            while (i < s.length()) {
                char c = s.charAt(i);
                if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
                    i++;
                } else {
                    break;
                }
            }
        }
    }
}

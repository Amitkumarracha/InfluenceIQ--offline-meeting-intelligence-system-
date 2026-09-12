"""
Report exporter — Phase 13.

Exports a MeetingReport to:
  - JSON   : complete machine-readable structure
  - Markdown: human-readable academic/research report
  - HTML   : standalone, no external dependencies
  - CSV    : structured tables (participants, decisions, influence, action items)
"""

from __future__ import annotations

import csv
import html as html_module
import json
from pathlib import Path
from typing import Any

from src.report.generator import (
    ActionItem,
    DecisionReport,
    InfluenceReport,
    MeetingReport,
    MeetingOverview,
    ParticipantSummary,
    _fmt_ts,
    _NOT_AVAILABLE,
)
from src.utils.logging import get_logger

logger = get_logger("report.exporter")


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def _overview_to_dict(o: MeetingOverview) -> dict[str, Any]:
    return {
        "meeting_id":       o.meeting_id,
        "duration_s":       o.duration_s,
        "duration_hms":     _fmt_ts(o.duration_s),
        "num_participants": o.num_participants,
        "num_slides":       o.num_slides,
        "num_events":       o.num_events,
        "num_decisions":    o.num_decisions,
        "num_action_items": o.num_action_items,
        "num_interactions": o.num_interactions,
    }


def _participant_to_dict(p: ParticipantSummary) -> dict[str, Any]:
    return {
        "speaker_id":            p.speaker_id,
        "speaking_duration_s":   p.speaking_duration_s,
        "num_turns":             p.num_turns,
        "interactions_initiated": p.interactions_initiated,
        "interactions_received":  p.interactions_received,
        "influence_score":       p.influence_score,
        "influence_rank":        p.influence_rank,
        "decision_linked_events": p.decision_linked_events,
        "roles":                 p.roles,
        "supporting_decisions":  p.supporting_decisions,
    }


def _decision_to_dict(d: DecisionReport) -> dict[str, Any]:
    return {
        "decision_id":           d.decision_id,
        "status":                d.status,
        "topic":                 d.topic,
        "proposal_text":         d.proposal_text,
        "proposal_speaker":      d.proposal_speaker,
        "proposal_event_id":     d.proposal_event_id,
        "objections":            d.objections,
        "evidence_items":        d.evidence_items,
        "revisions":             d.revisions,
        "agreements":            d.agreements,
        "final_decision_text":   d.final_decision_text,
        "final_decision_event_id": d.final_decision_event_id,
        "participants":          d.participants,
        "supporting_slides":     d.supporting_slides,
        "supporting_segments":   d.supporting_segments,
        "lineage_text":          d.lineage_text,
        "confidence":            d.confidence,
    }


def _action_to_dict(a: ActionItem) -> dict[str, Any]:
    return {
        "text":                a.text,
        "speaker":             a.speaker,
        "timestamp":           _fmt_ts(a.timestamp),
        "event_id":            a.event_id,
        "related_decision_id": a.related_decision_id,
        "related_slide_id":    a.related_slide_id,
    }


def _influence_to_dict(i: InfluenceReport) -> dict[str, Any]:
    return {
        "participant":           i.speaker_id,
        "rank":                  i.rank,
        "influence_score":       i.score,
        "features":              i.features,
        "raw_features":          i.raw_features,
        "explanation":           i.explanation,
        "supporting_decisions":  i.supporting_decisions,
        "supporting_events":     i.supporting_events,
        "decision_contributions": i.decision_contributions,
    }


def export_json(report: MeetingReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "meeting_overview":     _overview_to_dict(report.meeting_overview),
        "participants":         [_participant_to_dict(p) for p in report.participants],
        "executive_summary":    report.executive_summary,
        "topics":               report.topics,
        "slide_discussions":    report.slide_discussions,
        "proposals":            report.proposals,
        "evidence_items":       report.evidence_items,
        "decisions":            [_decision_to_dict(d) for d in report.decisions],
        "action_items":         [_action_to_dict(a) for a in report.action_items],
        "interactions":         report.interactions,
        "influence":            [_influence_to_dict(i) for i in report.influence],
        "influence_vs_speaking": report.influence_vs_speaking,
        "evaluation":           report.evaluation,
        "ablation":             report.ablation,
        "traceability":         report.traceability,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    logger.info("JSON report saved: %s", output_path)


# ---------------------------------------------------------------------------
# Markdown export
# ---------------------------------------------------------------------------

def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    def _cell(v: Any) -> str:
        return str(v) if v is not None else "—"
    header_row = "| " + " | ".join(headers) + " |"
    sep_row    = "| " + " | ".join("---" for _ in headers) + " |"
    data_rows  = ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return "\n".join([header_row, sep_row] + data_rows)


def export_markdown(report: MeetingReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    o = report.meeting_overview
    lines: list[str] = []

    lines += [
        "# Meeting Intelligence Report",
        f"**Meeting ID:** {report.meeting_id}",
        "",
        "> *Generated by the Offline Multimodal Meeting-Intelligence System.*  ",
        "> *All conclusions are evidence-based analytical estimates, not causal claims.*",
        "",
    ]

    # 1. Overview
    lines += [
        "## 1. Meeting Overview",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| Meeting ID | {o.meeting_id} |",
        f"| Duration | {_fmt_ts(o.duration_s)} |",
        f"| Participants | {o.num_participants} |",
        f"| Slides | {o.num_slides if o.num_slides is not None else '—'} |",
        f"| Detected Events | {o.num_events} |",
        f"| Decisions | {o.num_decisions} |",
        f"| Action Items | {o.num_action_items} |",
        f"| Interactions | {o.num_interactions} |",
        "",
    ]

    # 2. Participants
    lines += ["## 2. Participants", ""]
    lines += [
        "> **Note:** Speaking duration describes conversational activity.",
        "> It is NOT a measure of decision influence.",
        "",
    ]
    if report.participants:
        headers = ["Speaker", "Speaking (s)", "Turns", "Dec-linked Events",
                   "Influence Score", "Influence Rank", "Roles"]
        rows = [
            [
                p.speaker_id,
                p.speaking_duration_s,
                p.num_turns,
                p.decision_linked_events,
                f"{p.influence_score:.4f}" if p.influence_score is not None else "—",
                p.influence_rank or "—",
                ", ".join(p.roles) or "—",
            ]
            for p in sorted(report.participants, key=lambda x: x.speaker_id)
        ]
        lines += [_md_table(headers, rows), ""]
    else:
        lines += ["*No participant data available.*", ""]

    # 3. Executive Summary
    lines += ["## 3. Executive Summary", ""]
    s = report.executive_summary
    if s.get("status") == _NOT_AVAILABLE:
        lines += [_NOT_AVAILABLE, ""]
    else:
        lines += [
            f"- **Proposals detected:** {s.get('num_proposals', 0)}",
            f"- **Confirmed decisions:** {s.get('num_confirmed_decisions', 0)}",
            f"- **Unresolved proposals:** {s.get('num_unresolved_proposals', 0)}",
            f"- **Action items:** {s.get('num_action_items', 0)}",
            "",
            f"*{s.get('note', '')}*",
            "",
        ]
        if s.get("confirmed_decisions"):
            lines += ["**Confirmed Decisions:**", ""]
            for d in s["confirmed_decisions"]:
                lines.append(f"- **{d['decision_id']}** — {d.get('topic') or 'N/A'}: _{d.get('final_decision') or 'see details'}_")
            lines.append("")

    # 4. Topics
    lines += ["## 4. Discussion Topics", ""]
    if report.topics:
        for t in report.topics:
            lines += [
                f"### {t.get('topic', 'Unknown Topic')}",
                f"- **Decision ID:** {t.get('decision_id', '—')}",
                f"- **Status:** {t.get('status', '—')}",
                f"- **Participants:** {', '.join(t.get('participants', []))}",
                f"- **Slides:** {', '.join(t.get('supporting_slides', [])) or '—'}",
                "",
            ]
    else:
        lines += ["*No topic data available.*", ""]

    # 5. Slide-linked Discussion
    lines += ["## 5. Slide-linked Discussion", ""]
    if report.slide_discussions:
        for sd in report.slide_discussions[:10]:
            lines += [f"### Slide: {sd['slide_id']}", ""]
            for seg in sd.get("segments", [])[:5]:
                lines.append(
                    f"**[{seg['timestamp']}]** *{seg['speaker']}* ({seg['event_type']}):  "
                )
                lines.append(f"> {seg['text']}")
                lines.append("")
    else:
        lines += ["*No slide-linked discussion data available.*", ""]

    # 6. Proposals
    lines += ["## 6. Proposals", ""]
    if report.proposals:
        for p in report.proposals:
            lines += [
                f"- **[{p['timestamp']}]** {p['speaker']} (`{p['event_id']}`): _{p['text']}_",
                f"  → Decision-linked: {p['decision_linked']}  |  Status: {p.get('decision_status') or '—'}",
                "",
            ]
    else:
        lines += ["*No proposals detected.*", ""]

    # 7. Decisions
    lines += ["## 7. Decisions", ""]
    if report.decisions:
        for d in report.decisions:
            lines += [
                f"### {d.decision_id} — {d.topic or 'No topic'}",
                f"**Status:** {d.status}  |  **Confidence:** {d.confidence or 'not estimated'}",
                "",
                f"**Lineage:** {d.lineage_text}",
                "",
            ]
            if d.proposal_text:
                lines.append(f"**Proposal** ({d.proposal_speaker}): _{d.proposal_text}_")
                lines.append("")
            if d.objections:
                lines.append("**Objections:**")
                for obj in d.objections:
                    lines.append(f"- {obj.get('speaker')}: _{obj.get('text', '')}_")
                lines.append("")
            if d.revisions:
                lines.append("**Revisions:**")
                for r in d.revisions:
                    lines.append(f"- _{r.get('text', '')}_")
                lines.append("")
            if d.final_decision_text:
                lines.append(f"**Final Decision:** _{d.final_decision_text}_")
                lines.append("")
            if d.supporting_slides:
                lines.append(f"**Slides:** {', '.join(d.supporting_slides)}")
                lines.append("")
    else:
        lines += ["*No decisions detected.*", ""]

    # 8. Action Items
    lines += ["## 8. Action Items", ""]
    if report.action_items:
        headers = ["Action", "Responsible", "Related Decision", "Timestamp", "Slide"]
        rows = [
            [
                a.text[:80],
                a.speaker or "Unassigned",
                a.related_decision_id or "—",
                _fmt_ts(a.timestamp),
                a.related_slide_id or "—",
            ]
            for a in report.action_items
        ]
        lines += [_md_table(headers, rows), ""]
    else:
        lines += ["*No action items detected.*", ""]

    # 9. Interactions
    lines += ["## 9. Participant Interaction Analysis", ""]
    intr = report.interactions
    if isinstance(intr, dict) and "status" not in intr:
        lines += [
            f"- **Total interactions:** {intr.get('total_interactions', 0)}",
            f"- **Decision-linked:** {intr.get('decision_linked', 0)}",
            "",
            "> *These statistics describe conversational interaction — NOT influence.*",
            "",
        ]
        by_type = intr.get("interactions_by_type", {})
        if by_type:
            headers = ["Type", "Count"]
            rows = [[t, c] for t, c in sorted(by_type.items())]
            lines += [_md_table(headers, rows), ""]
    else:
        lines += [_NOT_AVAILABLE, ""]

    # 10. Influence
    lines += [
        "## 10. Participant Influence Analysis",
        "",
        "> *Scores are decision-linked analytical estimates. They do NOT establish causal truth.*  ",
        "> *Human evaluation is required to validate these rankings.*",
        "",
    ]
    if report.influence:
        headers = ["Rank", "Participant", "Score", "Proposal", "Evidence",
                   "Objection", "Revision", "Decision", "Interaction", "Slide"]
        rows = [
            [
                i.rank, i.speaker_id, f"{i.score:.4f}",
                f"{i.features.get('proposal_contribution', 0):.3f}",
                f"{i.features.get('evidence_contribution', 0):.3f}",
                f"{i.features.get('objection_contribution', 0):.3f}",
                f"{i.features.get('revision_contribution', 0):.3f}",
                f"{i.features.get('decision_contribution', 0):.3f}",
                f"{i.features.get('interaction_contribution', 0):.3f}",
                f"{i.features.get('slide_grounded_contribution', 0):.3f}",
            ]
            for i in report.influence
        ]
        lines += [_md_table(headers, rows), ""]

        lines += ["### Explanations", ""]
        for i in report.influence:
            lines += [f"#### {i.speaker_id} (Rank {i.rank})", ""]
            for line in i.explanation:
                lines.append(f"- {line}")
            lines.append("")
    else:
        lines += ["*Influence analysis not available.*", ""]

    # 11. Influence vs Speaking Time
    lines += ["## 11. Influence vs Speaking Time", ""]
    if report.influence_vs_speaking:
        lines += [
            "> This table demonstrates that speaking time and decision-linked influence",
            "> can differ significantly across participants.",
            "",
        ]
        headers = ["Participant", "Speaking Rank", "Speaking (s)", "Influence Rank", "Influence Score"]
        rows = [
            [
                r["participant"],
                r.get("speaking_rank") or "—",
                r.get("speaking_duration_s") or "—",
                r.get("influence_rank") or "—",
                f"{r['influence_score']:.4f}" if r.get("influence_score") is not None else "—",
            ]
            for r in report.influence_vs_speaking
        ]
        lines += [_md_table(headers, rows), ""]
    else:
        lines += ["*Data not available.*", ""]

    # 12. Evaluation
    lines += ["## 12. Evaluation", ""]
    ev = report.evaluation
    if ev.get("status") == _NOT_AVAILABLE:
        lines += [_NOT_AVAILABLE, ""]
    else:
        for key, val in ev.items():
            if isinstance(val, str):
                lines.append(f"- **{key}:** {val}")
            elif isinstance(val, dict) and val.get("status") == "ok":
                lines.append(f"- **{key}:** {json.dumps({k: v for k, v in val.items() if k not in ('status', 'metric')})}")
            elif isinstance(val, dict):
                lines.append(f"- **{key}:** {val.get('status', str(val))}")
        lines.append("")

    # 13. Ablation
    lines += ["## 13. Ablation Study", ""]
    ab = report.ablation
    if isinstance(ab, dict) and "results" in ab:
        lines += [f"*{ab.get('note', '')}*", ""]
        headers = ["Experiment", "Label", "Removed Component", "Spearman", "Kendall"]
        rows = [
            [
                r["experiment"], r["label"], r["removed_component"],
                r["metrics"].get("spearman"),
                r["metrics"].get("kendall"),
            ]
            for r in ab.get("results", [])
        ]
        lines += [_md_table(headers, rows), ""]
    else:
        status = ab.get("status", _NOT_AVAILABLE) if isinstance(ab, dict) else _NOT_AVAILABLE
        lines += [status, ""]

    # 14. Traceability
    lines += ["## 14. Evidence Traceability", ""]
    chains = report.traceability.get("chains", [])
    if chains:
        lines += [
            f"*{report.traceability.get('description', '')}*",
            "",
        ]
        for c in chains[:20]:
            lines += [
                f"- **{c['participant']}** (score={c['influence_score']:.4f}) → "
                f"`{c['event_id']}` `{c['event_type']}` by {c['speaker']} "
                f"at {c['timestamp']} | slide: {c['slide_id'] or '—'} | decision: {c['decision_id']}",
            ]
        lines.append("")
    else:
        lines += ["*Traceability data not available.*", ""]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Markdown report saved: %s", output_path)


# ---------------------------------------------------------------------------
# HTML export
# ---------------------------------------------------------------------------

def _h(text: Any) -> str:
    """HTML-escape a value."""
    return html_module.escape(str(text) if text is not None else "—")


def _html_table(headers: list[str], rows: list[list[Any]], caption: str = "") -> str:
    th = "".join(f"<th>{_h(h)}</th>" for h in headers)
    body_rows = "".join(
        "<tr>" + "".join(f"<td>{_h(c)}</td>" for c in row) + "</tr>"
        for row in rows
    )
    cap = f"<caption>{_h(caption)}</caption>" if caption else ""
    return f"<table>{cap}<thead><tr>{th}</tr></thead><tbody>{body_rows}</tbody></table>"


_CSS = """
body{font-family:Arial,sans-serif;max-width:1100px;margin:2em auto;padding:0 1em;color:#222}
h1{color:#1a3a5c}h2{color:#2c5f8a;border-bottom:2px solid #2c5f8a;padding-bottom:4px}
h3{color:#3a7abf}h4{color:#555}
table{border-collapse:collapse;width:100%;margin-bottom:1em}
th{background:#2c5f8a;color:#fff;padding:6px 10px;text-align:left}
td{border:1px solid #ccc;padding:5px 10px;vertical-align:top}
tr:nth-child(even){background:#f5f8fc}
blockquote{border-left:4px solid #2c5f8a;margin:0;padding:6px 12px;background:#eef4fb}
.note{background:#fff8e1;border:1px solid #ffe082;padding:8px 12px;border-radius:4px;margin-bottom:1em}
.unavailable{color:#888;font-style:italic}
code{background:#f0f0f0;padding:1px 4px;border-radius:3px;font-size:0.9em}
"""


def export_html(report: MeetingReport, output_path: Path) -> None:
    o = report.meeting_overview
    sections: list[str] = []

    def _sec(title: str, content: str) -> str:
        return f"<section><h2>{_h(title)}</h2>{content}</section>"

    # Overview
    overview_rows = [
        ["Meeting ID", o.meeting_id],
        ["Duration", _fmt_ts(o.duration_s)],
        ["Participants", o.num_participants],
        ["Slides", o.num_slides if o.num_slides is not None else "—"],
        ["Events", o.num_events],
        ["Decisions", o.num_decisions],
        ["Action Items", o.num_action_items],
        ["Interactions", o.num_interactions],
    ]
    sections.append(_sec("1. Meeting Overview",
        _html_table(["Field", "Value"], overview_rows)))

    # Participants
    note = '<div class="note">Speaking duration describes conversational activity — it is NOT a measure of decision influence.</div>'
    if report.participants:
        p_rows = [
            [p.speaker_id, p.speaking_duration_s, p.num_turns,
             p.decision_linked_events,
             f"{p.influence_score:.4f}" if p.influence_score is not None else "—",
             p.influence_rank or "—",
             ", ".join(p.roles) or "—"]
            for p in sorted(report.participants, key=lambda x: x.speaker_id)
        ]
        sections.append(_sec("2. Participants", note + _html_table(
            ["Speaker", "Speaking (s)", "Turns", "Dec-Linked Events",
             "Influence Score", "Influence Rank", "Roles"], p_rows)))
    else:
        sections.append(_sec("2. Participants", '<p class="unavailable">No participant data.</p>'))

    # Summary
    s = report.executive_summary
    if s.get("status") == _NOT_AVAILABLE:
        sum_html = f'<p class="unavailable">{_h(_NOT_AVAILABLE)}</p>'
    else:
        sum_html = (
            f"<p><b>Proposals:</b> {s.get('num_proposals',0)} | "
            f"<b>Confirmed decisions:</b> {s.get('num_confirmed_decisions',0)} | "
            f"<b>Unresolved:</b> {s.get('num_unresolved_proposals',0)} | "
            f"<b>Action items:</b> {s.get('num_action_items',0)}</p>"
            f'<p class="note">{_h(s.get("note",""))}</p>'
        )
    sections.append(_sec("3. Executive Summary", sum_html))

    # Decisions
    dec_html = ""
    if report.decisions:
        for d in report.decisions:
            dec_html += f"<h3>{_h(d.decision_id)} — {_h(d.topic or 'No topic')}</h3>"
            dec_html += f"<p><b>Status:</b> {_h(d.status)} | <b>Lineage:</b> <code>{_h(d.lineage_text)}</code></p>"
            if d.proposal_text:
                dec_html += f"<p><b>Proposal</b> ({_h(d.proposal_speaker)}): <em>{_h(d.proposal_text)}</em></p>"
            if d.final_decision_text:
                dec_html += f"<p><b>Final Decision:</b> <em>{_h(d.final_decision_text)}</em></p>"
            if d.supporting_slides:
                dec_html += f"<p><b>Slides:</b> {_h(', '.join(d.supporting_slides))}</p>"
    else:
        dec_html = '<p class="unavailable">No decisions detected.</p>'
    sections.append(_sec("4. Decisions", dec_html))

    # Action items
    if report.action_items:
        ai_rows = [
            [a.text[:80], a.speaker or "Unassigned",
             a.related_decision_id or "—", _fmt_ts(a.timestamp),
             a.related_slide_id or "—"]
            for a in report.action_items
        ]
        sections.append(_sec("5. Action Items", _html_table(
            ["Action", "Responsible", "Related Decision", "Timestamp", "Slide"], ai_rows)))
    else:
        sections.append(_sec("5. Action Items",
            '<p class="unavailable">No action items detected.</p>'))

    # Influence
    inf_note = '<div class="note">Scores are decision-linked analytical estimates. They do NOT establish causal truth. Human evaluation required.</div>'
    if report.influence:
        inf_rows = [
            [i.rank, i.speaker_id, f"{i.score:.4f}",
             f"{i.features.get('proposal_contribution',0):.3f}",
             f"{i.features.get('evidence_contribution',0):.3f}",
             f"{i.features.get('objection_contribution',0):.3f}",
             f"{i.features.get('revision_contribution',0):.3f}",
             f"{i.features.get('decision_contribution',0):.3f}",
             f"{i.features.get('slide_grounded_contribution',0):.3f}"]
            for i in report.influence
        ]
        inf_html = inf_note + _html_table(
            ["Rank", "Participant", "Score", "Proposal", "Evidence",
             "Objection", "Revision", "Decision", "Slide"], inf_rows)
        inf_html += "<h3>Explanations</h3>"
        for i in report.influence:
            inf_html += f"<h4>{_h(i.speaker_id)} (Rank {i.rank})</h4><ul>"
            for line in i.explanation:
                inf_html += f"<li>{_h(line)}</li>"
            inf_html += "</ul>"
        sections.append(_sec("6. Influence Analysis", inf_html))
    else:
        sections.append(_sec("6. Influence Analysis",
            '<p class="unavailable">Influence analysis not available.</p>'))

    # Influence vs Speaking
    if report.influence_vs_speaking:
        cmp_note = '<div class="note">This table demonstrates that speaking time and decision-linked influence can differ significantly.</div>'
        cmp_rows = [
            [r["participant"], r.get("speaking_rank") or "—",
             r.get("speaking_duration_s") or "—",
             r.get("influence_rank") or "—",
             f"{r['influence_score']:.4f}" if r.get("influence_score") is not None else "—"]
            for r in report.influence_vs_speaking
        ]
        sections.append(_sec("7. Influence vs Speaking Time", cmp_note + _html_table(
            ["Participant", "Speaking Rank", "Speaking (s)", "Influence Rank", "Score"], cmp_rows)))

    # Evaluation
    ev = report.evaluation
    if ev.get("status") == _NOT_AVAILABLE:
        ev_html = f'<p class="unavailable">{_h(_NOT_AVAILABLE)}</p>'
    else:
        ev_html = "<ul>"
        for key, val in ev.items():
            if isinstance(val, str):
                ev_html += f"<li><b>{_h(key)}:</b> {_h(val)}</li>"
            elif isinstance(val, dict) and val.get("status") == "ok":
                ev_html += f"<li><b>{_h(key)}:</b> <code>{_h(str({k:v for k,v in val.items() if k not in ('status','metric')}))}</code></li>"
            elif isinstance(val, dict):
                ev_html += f"<li><b>{_h(key)}:</b> {_h(val.get('status', str(val)))}</li>"
        ev_html += "</ul>"
    sections.append(_sec("8. Evaluation", ev_html))

    # Ablation
    ab = report.ablation
    if isinstance(ab, dict) and "results" in ab:
        ab_rows = [
            [r["experiment"], r["label"], r["removed_component"],
             r["metrics"].get("spearman"), r["metrics"].get("kendall")]
            for r in ab.get("results", [])
        ]
        ab_html = f'<p class="note">{_h(ab.get("note",""))}</p>'
        ab_html += _html_table(["Experiment", "Label", "Removed", "Spearman", "Kendall"], ab_rows)
        sections.append(_sec("9. Ablation Study", ab_html))
    else:
        status = ab.get("status", _NOT_AVAILABLE) if isinstance(ab, dict) else _NOT_AVAILABLE
        sections.append(_sec("9. Ablation Study",
            f'<p class="unavailable">{_h(status)}</p>'))

    # Traceability
    chains = report.traceability.get("chains", [])
    if chains:
        tr_rows = [
            [c["participant"], c["event_id"], c["event_type"],
             c["speaker"], c["timestamp"], c["slide_id"] or "—",
             c["decision_id"], c["text"][:60]]
            for c in chains[:30]
        ]
        tr_html = _html_table(
            ["Participant", "Event ID", "Type", "Speaker", "Time", "Slide", "Decision", "Text"],
            tr_rows)
        sections.append(_sec("10. Traceability", tr_html))

    body = "\n".join(sections)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meeting Intelligence Report — {_h(report.meeting_id)}</title>
<style>{_CSS}</style>
</head>
<body>
<h1>Meeting Intelligence Report</h1>
<p><strong>Meeting ID:</strong> {_h(report.meeting_id)}</p>
<blockquote>Generated by the Offline Multimodal Meeting-Intelligence System.<br>
All conclusions are evidence-based analytical estimates, not causal claims.</blockquote>
{body}
</body>
</html>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    logger.info("HTML report saved: %s", output_path)


# ---------------------------------------------------------------------------
# CSV exports
# ---------------------------------------------------------------------------

def export_csv_participants(report: MeetingReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["speaker_id", "speaking_duration_s", "num_turns",
               "decision_linked_events", "influence_score", "influence_rank",
               "interactions_initiated", "interactions_received", "roles"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for p in report.participants:
            w.writerow({
                "speaker_id": p.speaker_id,
                "speaking_duration_s": p.speaking_duration_s,
                "num_turns": p.num_turns,
                "decision_linked_events": p.decision_linked_events,
                "influence_score": p.influence_score,
                "influence_rank": p.influence_rank,
                "interactions_initiated": p.interactions_initiated,
                "interactions_received": p.interactions_received,
                "roles": ";".join(p.roles),
            })
    logger.info("Participants CSV saved: %s", output_path)


def export_csv_decisions(report: MeetingReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["decision_id", "status", "topic", "proposal_speaker",
               "proposal_text", "final_decision_text", "participants",
               "supporting_slides", "lineage_text"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for d in report.decisions:
            w.writerow({
                "decision_id": d.decision_id,
                "status": d.status,
                "topic": d.topic or "",
                "proposal_speaker": d.proposal_speaker or "",
                "proposal_text": (d.proposal_text or "")[:200],
                "final_decision_text": (d.final_decision_text or "")[:200],
                "participants": ";".join(d.participants),
                "supporting_slides": ";".join(d.supporting_slides),
                "lineage_text": d.lineage_text,
            })
    logger.info("Decisions CSV saved: %s", output_path)


def export_csv_influence(report: MeetingReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    feat_keys = ["proposal_contribution", "evidence_contribution",
                 "objection_contribution", "revision_contribution",
                 "decision_contribution", "interaction_contribution",
                 "slide_grounded_contribution"]
    headers = ["rank", "participant", "influence_score"] + feat_keys + ["supporting_decisions"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for i in report.influence:
            row: dict = {
                "rank": i.rank,
                "participant": i.speaker_id,
                "influence_score": i.score,
                "supporting_decisions": ";".join(i.supporting_decisions),
            }
            for k in feat_keys:
                row[k] = i.features.get(k, 0.0)
            w.writerow(row)
    logger.info("Influence CSV saved: %s", output_path)


def export_csv_action_items(report: MeetingReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    headers = ["event_id", "text", "speaker", "timestamp",
               "related_decision_id", "related_slide_id"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for a in report.action_items:
            w.writerow({
                "event_id": a.event_id,
                "text": a.text[:200],
                "speaker": a.speaker or "Unassigned",
                "timestamp": _fmt_ts(a.timestamp),
                "related_decision_id": a.related_decision_id or "",
                "related_slide_id": a.related_slide_id or "",
            })
    logger.info("Action items CSV saved: %s", output_path)


# ---------------------------------------------------------------------------
# Multi-format export
# ---------------------------------------------------------------------------

def export_all(
    report: MeetingReport,
    output_dir: Path,
    formats: list[str] | None = None,
) -> dict[str, Path]:
    """
    Export report in all requested formats.

    Parameters
    ----------
    report     : MeetingReport to export.
    output_dir : Directory to write files.
    formats    : List of format strings: 'json', 'markdown', 'html', 'csv'.
                 Defaults to all four.

    Returns
    -------
    {format: path} mapping for exported files.
    """
    if formats is None:
        formats = ["json", "markdown", "html", "csv"]

    mid = report.meeting_id
    paths: dict[str, Path] = {}

    if "json" in formats:
        p = output_dir / f"{mid}_report.json"
        export_json(report, p)
        paths["json"] = p

    if "markdown" in formats:
        p = output_dir / f"{mid}_report.md"
        export_markdown(report, p)
        paths["markdown"] = p

    if "html" in formats:
        p = output_dir / f"{mid}_report.html"
        export_html(report, p)
        paths["html"] = p

    if "csv" in formats:
        csv_paths = {
            "participants": output_dir / f"{mid}_participants.csv",
            "decisions":    output_dir / f"{mid}_decisions.csv",
            "influence":    output_dir / f"{mid}_influence.csv",
            "action_items": output_dir / f"{mid}_action_items.csv",
        }
        export_csv_participants(report, csv_paths["participants"])
        export_csv_decisions(report, csv_paths["decisions"])
        export_csv_influence(report, csv_paths["influence"])
        export_csv_action_items(report, csv_paths["action_items"])
        paths.update(csv_paths)

    return paths

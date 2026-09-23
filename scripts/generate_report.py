"""
Report generation script — Phase 13.

Consumes existing pipeline outputs and generates a final meeting report.
Does NOT rerun any ML model.

Usage
-----
python scripts/generate_report.py --meeting-id <id>
python scripts/generate_report.py --meeting-id <id> --format json markdown html csv
python scripts/generate_report.py --meeting-id <id> --input-dir data/processed --output-dir outputs/reports
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logging import get_logger

logger = get_logger("generate_report")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Phase 13 — Meeting Report Generator")
    p.add_argument("--meeting-id", required=True)
    p.add_argument("--input-dir",  default="data/processed",
                   help="Root of data/processed/ (default: data/processed)")
    p.add_argument("--output-dir", default="outputs/reports",
                   help="Output directory (default: outputs/reports)")
    p.add_argument(
        "--format", nargs="+",
        choices=["json", "markdown", "html", "csv"],
        default=["json", "markdown", "html", "csv"],
        help="Report formats to generate",
    )
    p.add_argument("--eval-metrics", default=None,
                   help="Path to evaluation metrics JSON (optional)")
    p.add_argument("--ablation",     default=None,
                   help="Path to ablation JSON (optional)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    from src.report.generator import generate_report
    from src.report.exporter import export_all

    input_dir  = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating report for meeting: %s", args.meeting_id)
    logger.info("Input dir : %s", input_dir)
    logger.info("Output dir: %s", output_dir)
    logger.info("Formats   : %s", args.format)

    report = generate_report(
        meeting_id=args.meeting_id,
        input_dir=input_dir,
        eval_metrics_path=Path(args.eval_metrics) if args.eval_metrics else None,
        ablation_path=Path(args.ablation) if args.ablation else None,
    )

    exported = export_all(report, output_dir, formats=args.format)

    print(f"\n[Report Generation Summary — {args.meeting_id}]")
    print(f"  Participants   : {report.meeting_overview.num_participants}")
    print(f"  Events         : {report.meeting_overview.num_events}")
    print(f"  Decisions      : {report.meeting_overview.num_decisions}")
    print(f"  Action Items   : {report.meeting_overview.num_action_items}")
    print(f"  Interactions   : {report.meeting_overview.num_interactions}")
    print()
    for fmt, path in exported.items():
        print(f"  {fmt:<12}: {path}")
    print()
    print("NOTE: Report content is derived from existing pipeline outputs.")
    print("No ML model was rerun. Missing sections are marked as unavailable.")
    print("\nDone.")


if __name__ == "__main__":
    main()

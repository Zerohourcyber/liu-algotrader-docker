#!/usr/bin/env python3
import os, sys, subprocess, json, textwrap, argparse
from pathlib import Path
from datetime import datetime

# Default injections
DATA_BLOCK = textwrap.dedent("""\
[data]
source = "yahoo"   # no API key required
""")

STRAT_BLOCK = textwrap.dedent("""\
[[strategies]]
name   = "mean_reversion_auto"
module = "liualgotrader.strategies.mean_reversion"
  [strategies.settings]
  lookback       = 20
  threshold      = 1.5
  allocation_pct = 0.2

[[strategies.schedule]]
start    = 0
duration = 390
""")

def inject_sections(tp: Path):
    text = tp.read_text()
    to_add = ""
    if "[data]" not in text:
        print("✨ Injecting [data] block.")
        to_add += "\n" + DATA_BLOCK
    else:
        print("🔍 [data] already present.")
    if "mean_reversion_auto" not in text:
        print("✨ Appending strategy block.")
        to_add += "\n" + STRAT_BLOCK
    else:
        print("🔍 mean_reversion strategy already present.")
    tp.write_text(text + to_add)

def run_backtest(args):
    os.environ["TLOG_LEVEL"] = "DEBUG"
    cmd = [
        "python3", "-m", "liualgotrader.enhanced_backtest",
        "--tradeplan",   args.tradeplan,
        "--symbols",     args.symbols,
        "--start-date",  args.start_date,
        "--end-date",    args.end_date,
        "--batch-id",    f"auto-{datetime.now():%Y%m%d-%H%M%S}",
        "--diagnostics", args.diagnostics,
        "--log-level",   "DEBUG"
    ]
    print("🚀 Running:", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True)

def main():
    p = argparse.ArgumentParser(
        description="Fix-it-bot: inject data+strategy and run backtest"
    )
    p.add_argument("--symbols",     required=True)
    p.add_argument("--start-date",  required=True)
    p.add_argument("--end-date",    required=True)
    p.add_argument("--tradeplan",   default="liu_samples/tradeplan.toml")
    p.add_argument("--diagnostics", default="liu_samples/diagnostics.json")
    args = p.parse_args()

    tp = Path(args.tradeplan)
    if not tp.exists():
        print(f"❌ tradeplan not found at {tp}", file=sys.stderr)
        sys.exit(1)

    inject_sections(tp)
    proc = run_backtest(args)

    if proc.returncode != 0:
        print("❌ Backtest failed:\n", proc.stderr, file=sys.stderr)
        sys.exit(proc.returncode)

    dg = Path(args.diagnostics)
    if not dg.exists():
        print("✅ No issues detected — diagnostics.json not created.")
        sys.exit(0)

    issues = json.loads(dg.read_text()).get("issues", [])
    if issues:
        print("🚨 Issues detected:")
        for i in issues:
            print(" •", i)
        sys.exit(3)

    print("✅ Backtest OK — diagnostics written to", dg)
    sys.exit(0)

if __name__ == "__main__":
    main()

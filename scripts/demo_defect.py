"""Switch the deliberate demo defect on or off (for the failing-run demonstration).

    python scripts/demo_defect.py on      # URL validation is bypassed -> test case 3 fails
    python scripts/demo_defect.py off     # restore correct behaviour
    python scripts/demo_defect.py status
"""
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "portal" / "validators.py"
ANCHOR = "# >>> demo-defect anchor (do not remove) <<<"
DEFECT = "    return True  # DEMO DEFECT: URL validation bypassed"


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    lines = TARGET.read_text(encoding="utf-8").splitlines()
    is_on = any("DEMO DEFECT" in l for l in lines)

    if action == "status":
        print("Defect is ON" if is_on else "Defect is OFF")
        return 0
    if action == "on" and not is_on:
        i = next(n for n, l in enumerate(lines) if ANCHOR in l)
        lines.insert(i + 1, DEFECT)
    elif action == "off":
        lines = [l for l in lines if "DEMO DEFECT" not in l]
    elif action not in ("on", "off"):
        print(__doc__)
        return 2
    TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Defect turned {action.upper()}. Now commit and push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

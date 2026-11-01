"""Compile button-card JavaScript templates without executing any template.

Usage: python validate_panels_js.py PANEL_PATH [PANEL_PATH...] [--report FILE]
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml
from validate_config import StrictLoader, strings


def nodes(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def validate(paths):
    blocks = []
    result = dict(files=[], javascript_templates=0, custom_card_types={},
                  script_actions={}, reset_mentions=[], errors=[], limits=[
                      "JavaScript is syntax-compiled with new Function only; templates are never executed.",
                      "Live Home Assistant and custom-card rendering require a browser check."])
    custom_types = Counter()
    services = Counter()
    for path in paths:
        path = Path(path)
        files = sorted(path.rglob("*.yaml")) if path.is_dir() else [path]
        for file in files:
            try:
                data = yaml.load(file.read_text(encoding="utf-8-sig"), Loader=StrictLoader)
            except Exception as exc:
                result["errors"].append(f"{file}: {exc}")
                continue
            result["files"].append(str(file))
            for node in nodes(data):
                if isinstance(node, dict):
                    card = node.get("type", "")
                    if isinstance(card, str) and card.startswith("custom:"):
                        custom_types[card] += 1
            for breadcrumb, value in strings(data):
                if value.startswith("script."):
                    services[value] += 1
                if re.search(r"reinici|reset|delete_test|cerrar_semana|close_week", value, re.I):
                    result["reset_mentions"].append(f"{file.name}{breadcrumb}: {value[:180]}")
                # Extra outer brackets defer evaluation for nested button-cards.
                for match in re.finditer(r"(\[{3,})(.*?)(\]{3,})", value, re.S):
                    if len(match.group(1)) != len(match.group(3)):
                        result["errors"].append(f"{file}{breadcrumb}: unmatched template bracket depth")
                    blocks.append(dict(file=str(file), location=breadcrumb, code=match.group(2)))
    runtime = shutil.which("node")
    if not runtime:
        result["errors"].append("Node.js is unavailable; cannot compile JavaScript.")
    else:
        program = """const fs=require('fs');
const blocks=JSON.parse(fs.readFileSync(0,'utf8'));
const errors=[];
for (let i=0;i<blocks.length;i++) {
  try { new Function(blocks[i].code); }
  catch(error) { errors.push({index:i,error:error.message}); }
}
process.stdout.write(JSON.stringify(errors));
"""
        completed = subprocess.run([runtime, "-e", program], input=json.dumps(blocks),
                                   text=True, encoding="utf-8", capture_output=True)
        if completed.returncode:
            result["errors"].append(completed.stderr)
        else:
            for failure in json.loads(completed.stdout):
                block = blocks[failure["index"]]
                result["errors"].append(f"{block['file']}{block['location']}: {failure['error']}")
    result["javascript_templates"] = len(blocks)
    result["custom_card_types"] = dict(sorted(custom_types.items()))
    result["script_actions"] = dict(sorted(services.items()))
    result["ok"] = not result["errors"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = validate(args.paths)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    sys.exit(0 if result["ok"] else 1)

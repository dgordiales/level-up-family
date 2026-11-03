"""Static validation; does not replace Home Assistant's own config check.

Usage: python validate_config.py CONFIG_ROOT [--report report.json]
Checks YAML duplicate keys, Jinja syntax/filters, repeated entity definitions,
and static references to the application's helper/script/shell entities.
"""
import argparse
import ast
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import unicodedata

import jinja2
import yaml


@dataclass
class Include:
    tag: str
    value: str


class StrictLoader(yaml.SafeLoader):
    pass


def strict_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise yaml.constructor.ConstructorError(
                "mapping", node.start_mark, f"duplicate key {key!r}", key_node.start_mark)
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, strict_mapping)
for tag in ("!include", "!include_dir_named", "!include_dir_merge_named",
            "!include_dir_list", "!include_dir_merge_list", "!secret"):
    StrictLoader.add_constructor(tag, lambda loader, node, tag=tag: Include(tag, loader.construct_scalar(node)))


def strings(value, breadcrumb=""):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from strings(item, f"{breadcrumb}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from strings(item, f"{breadcrumb}[{index}]")
    elif isinstance(value, str):
        yield breadcrumb, value


def includes(value):
    if isinstance(value, Include):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from includes(item)
    elif isinstance(value, list):
        for item in value:
            yield from includes(item)


def slug_name(value):
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", plain.lower())).strip("_")


def sensor_definitions(data):
    if not isinstance(data, dict):
        return
    for group in data.get("template", []) or []:
        if not isinstance(group, dict):
            continue
        for domain in ("sensor", "binary_sensor"):
            for entity in group.get(domain, []) or []:
                if isinstance(entity, dict) and isinstance(entity.get("name"), str):
                    yield entity.get("default_entity_id") or f"{domain}.{slug_name(entity['name'])}"
    for group in data.get("command_line", []) or []:
        if isinstance(group, dict) and isinstance(group.get("sensor"), dict):
            sensor = group["sensor"]
            yield sensor.get("default_entity_id") or f"sensor.{slug_name(sensor['name'])}"


def validate(root):
    root = Path(root).resolve()
    result = dict(root=str(root), yaml_files=0, python_files=0, jinja_templates=0,
                  static_references=0, entity_definitions=0, errors=[],
                  external_includes=[], limits=[
                      "Static validation only: Home Assistant schema/entity registry and UI require live checks.",
                      "Dynamic entity references and JavaScript Lovelace templates are not evaluated.",
                  ])
    env = jinja2.Environment(extensions=["jinja2.ext.loopcontrols", "jinja2.ext.do"])
    env.filters.update(bitwise_and=lambda a, b: int(a) & int(b),
                       bitwise_or=lambda a, b: int(a) | int(b),
                       from_json=json.loads, to_json=json.dumps, as_datetime=lambda value: value,
                       as_timestamp=lambda value: value, timestamp_custom=lambda value, *args: value)
    if not root.is_dir():
        result["errors"].append(f"Missing config directory: {root}")
    loaded = []
    definitions = {}
    domains = ("input_number", "input_text", "input_datetime", "input_boolean", "script", "shell_command")
    for path in sorted(root.rglob("*.yaml")):
        try:
            data = yaml.load(path.read_text(encoding="utf-8-sig"), Loader=StrictLoader)
            loaded.append((path, data))
            result["yaml_files"] += 1
        except Exception as exc:
            result["errors"].append(f"{path.relative_to(root)}: {exc}")
            continue
        if isinstance(data, dict):
            if 'level_up_family' in data:
                definitions['sensor.luf_family'] = str(path) + ' (custom integration)'
            for domain in domains:
                domain_data = data.get(domain)
                if not isinstance(domain_data, dict):
                    continue
                for key in domain_data:
                    entity = f"{domain}.{key}"
                    if entity in definitions:
                        result["errors"].append(f"Duplicate definition {entity}: {path} and {definitions[entity]}")
                    definitions[entity] = str(path)
            for entity in sensor_definitions(data):
                if entity in definitions:
                    result["errors"].append(f"Duplicate definition {entity}: {path} and {definitions[entity]}")
                definitions[entity] = str(path)
        for include in includes(data):
            if include.tag != "!secret" and not (path.parent / include.value).exists():
                result["external_includes"].append(
                    f"{path.relative_to(root)}: {include.tag} {include.value}")
        for breadcrumb, value in strings(data):
            if "{{" in value or "{%" in value or "{#" in value:
                try:
                    env.compile(value)
                    result["jinja_templates"] += 1
                except Exception as exc:
                    result["errors"].append(f"{path.relative_to(root)}{breadcrumb}: Jinja {exc}")
    result["entity_definitions"] = len(definitions)
    references = {}
    for path, data in loaded:
        for breadcrumb, value in strings(data):
            for entity in re.findall(
                    r"\b(?:sensor|binary_sensor|input_number|input_text|input_datetime|input_boolean|script|shell_command)\.[a-zA-Z0-9_]+", value):
                # Service names such as input_number.set_value are integration APIs.
                if entity.split(".", 1)[0] not in ("script", "shell_command") and entity.split(".", 1)[1] in (
                        "set_value", "set_datetime", "increment", "decrement", "turn_on", "turn_off", "toggle"):
                    continue
                if entity in ("script.turn_on", "script.turn_off", "script.reload"):
                    continue
                if entity.endswith("_"):
                    # Prefixes assembled into dynamic names are not static refs.
                    continue
                references.setdefault(entity, []).append(f"{path.relative_to(root)}{breadcrumb}")
    result["static_references"] = len(references)
    for entity, locations in sorted(references.items()):
        if entity not in definitions and re.match(r"(?:luf_|luf_|player[1-9][0-9]*_|lf_)", entity.split(".", 1)[1]):
            result["errors"].append(f"Undefined application reference {entity}: {locations[0]}")
    for path in sorted(root.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            result["python_files"] += 1
        except Exception as exc:
            result["errors"].append(f"{path.relative_to(root)}: Python {exc}")
    result["ok"] = not result["errors"]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = validate(args.root)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    sys.exit(0 if result["ok"] else 1)

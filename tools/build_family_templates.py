"""Rebuild the generic, privacy-safe runtime provisioning templates."""
import json
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent


def build(source=ROOT):
    source = Path(source)
    read = lambda path: yaml.safe_load((source / path).read_text(encoding='utf-8'))
    return {'parents': read('config/panel/level_up_family/parents.yaml'),
            'player1_panel': read('config/panel/level_up_family/player1.yaml'),
            'player2_panel': read('config/panel/level_up_family/player2.yaml'),
            'player2_package': read('config/packages/level_up_family/lf_player2.yaml'),
            'weekly': read('config/packages/level_up_family/lf_weekly.yaml'),
            'defaults': json.loads((source / 'config/level_up_family/task_defaults.json').read_text(encoding='utf-8'))}


if __name__ == '__main__':
    path = ROOT / 'config/custom_components/level_up_family/templates.json'
    path.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(path)

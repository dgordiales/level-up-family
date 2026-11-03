"""Load the browser module repeatedly without browser or third-party packages."""
from pathlib import Path
import shutil
import subprocess
import unittest


CARDS = (Path(__file__).resolve().parent.parent
         / 'config/www/level_up_family/level-up-family-cards.js')


class CardRegistrationTests(unittest.TestCase):
    def test_reloading_resource_preserves_registered_elements_without_duplicates(self):
        runtime = shutil.which('node')
        self.assertIsNotNone(runtime, 'Node.js is required to validate card registration')
        program = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const registry = new Map();
let definitionCount = 0;
const unrelatedMetadata = {type:'existing-other-card', name:'Existing card'};
const context = vm.createContext({
  HTMLElement: class {},
  customElements: {
    get: name => registry.get(name),
    define(name, constructor) {
      assert(!registry.has(name), `Duplicate element definition: ${name}`);
      registry.set(name, constructor);
      definitionCount += 1;
    },
  },
  window: {customCards:[unrelatedMetadata]},
});
const source = fs.readFileSync(process.argv[1], 'utf8');
vm.runInContext(source, context);
const expected = ['level-up-family-admin', 'level-up-family-missions', 'level-up-family-reward', 'level-up-family-roster'];
assert.equal(registry.size, expected.length);
const firstConstructors = new Map(registry);
vm.runInContext(source, context);
assert.equal(registry.size, expected.length);
assert.equal(definitionCount, expected.length);
for (const name of expected) {
  assert.equal(registry.get(name), firstConstructors.get(name), `Replaced constructor: ${name}`);
  assert.equal(context.window.customCards.filter(card => card.type === name).length, 1,
               `Duplicate card picker entry: ${name}`);
}
assert.equal(context.window.customCards.filter(card => card.type === unrelatedMetadata.type).length, 1);
assert.equal(context.window.customCards.find(card => card.type === unrelatedMetadata.type), unrelatedMetadata);
"""
        result = subprocess.run([runtime, '-e', program, str(CARDS)],
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == '__main__':
    unittest.main()

"""Import the installed ZIP with Decky 3.3.1's three known stdlib omissions."""
import html
import importlib.util
import sys
from importlib.machinery import PathFinder
from pathlib import Path
from types import SimpleNamespace

plugin = Path(sys.argv[1]).resolve()
missing = {"html.parser", "_markupbase", "shlex"}


class DeckyModules:
    def find_spec(self, fullname, path, target=None):
        if fullname in missing:
            paths = sys.path if path is None else path
            packaged = [p for p in paths if Path(p).resolve().is_relative_to(plugin)]
            spec = PathFinder.find_spec(fullname, packaged)
            if spec is None:
                raise ModuleNotFoundError(fullname, name=fullname)
            return spec


for module in missing:
    sys.modules.pop(module, None)
sys.meta_path.insert(0, DeckyModules())
sys.modules["decky"] = SimpleNamespace(DECKY_PLUGIN_DIR=str(plugin))
spec = importlib.util.spec_from_file_location("decky_entry", plugin / "main.py")
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
from library.providers import Index
from library.platforms import shlex

index = Index()
index.feed('<a href="a&amp;b.nes">test</a>')
assert index.links == ["a&b.nes"]
assert shlex.split('"/media/test card"/roms') == ["/media/test card/roms"]
for module in missing:
    assert Path(sys.modules[module].__file__).resolve().is_relative_to(plugin)
print("Plugin entry point and all three packaged fallbacks passed")

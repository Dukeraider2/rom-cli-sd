"""Package the runtime plugin and, optionally, a companion source archive."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

DECKY=Path(__file__).resolve().parent
ROOT=DECKY.parent


def package(output, source_output=None):
    files={name:DECKY/name for name in ("main.py","dist/index.js","package.json","plugin.json",
           "package-lock.json","tsconfig.json","rollup.config.js")}
    files["LICENSE"]=ROOT/"LICENSE"
    files["README.md"]=DECKY/"README.md"
    for folder,prefix in ((ROOT/"library","library"),(DECKY/"src","src"),(DECKY/"node_modules/@decky/api/src","third-party/decky-api/src")):
        for path in folder.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts:
                files[prefix+"/"+path.relative_to(folder).as_posix()]=path
    for name in ("LICENSE","package.json","README.md"):
        files["third-party/decky-api/"+name]=DECKY/"node_modules/@decky/api"/name
    runtime_names = {"main.py", "dist/index.js", "package.json", "plugin.json", "LICENSE",
                     "README.md", "third-party/decky-api/LICENSE"}
    for leaf in ("LICENSE", "_markupbase.py", "shlex.py", "html/parser.py"):
        name = "third-party/cpython/" + leaf
        files[name] = DECKY/name
        runtime_names.add(name)
    runtime = {name: path for name, path in files.items() if name in runtime_names
               or (path.parent == ROOT/"library" and path.suffix == ".py")}
    write_archive(Path(output), runtime)
    if source_output:
        files["package_plugin.py"] = DECKY/"package_plugin.py"
        write_archive(Path(source_output), files)


def write_archive(target, files):
    target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(target,"w",ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):
            archive.write(path,"ROM Library/"+name)
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError("Package integrity check failed")
    print(target)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output")
    parser.add_argument("--source-output")
    args = parser.parse_args()
    package(args.output, args.source_output)


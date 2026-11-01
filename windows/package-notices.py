"""Collect installed third-party licenses into the distributable Windows ZIP."""
from importlib.metadata import distributions
from pathlib import Path
import shutil
root=Path(__file__).resolve().parents[1]
out=root/'dist/licenses/python';out.mkdir(parents=True,exist_ok=True)
for dist in distributions():
    name=dist.metadata.get('Name','unknown')
    for file in dist.files or []:
        lower=str(file).lower()
        if ('license' in lower or 'copying' in lower or 'notice' in lower) and file.suffix.lower() in ('','.txt','.md','.rst'):
            source=Path(dist.locate_file(file))
            if source.is_file():
                target=out/name/Path(*file.parts[-2:]);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
(out/'DEPENDENCIES.txt').write_text('\n'.join(sorted(d.metadata.get('Name','unknown')+'=='+d.version for d in distributions()))+'\n')

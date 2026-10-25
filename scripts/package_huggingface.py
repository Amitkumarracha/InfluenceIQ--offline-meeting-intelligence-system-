"""Create a backend-only Space folder and ZIP without private workstation files."""
from pathlib import Path
import shutil
import tempfile


FILES = {
    'Dockerfile': 'Dockerfile',
    '.dockerignore': '.dockerignore',
    'deployment/huggingface/README.md': 'README.md',
    'config/config.yaml': 'config/config.yaml',
    'environment/requirements-lock.txt': 'environment/requirements-lock.txt',
    'scripts/download_models.py': 'scripts/download_models.py',
    'scripts/download_speaker_models.py': 'scripts/download_speaker_models.py',
    'scripts/validate_setup.py': 'scripts/validate_setup.py',
    'models/discussion/model.joblib': 'models/discussion/model.joblib',
    'models/discussion/manifest.json': 'models/discussion/manifest.json',
}


def package_backend(root, output_parent):
    root, output_parent = Path(root), Path(output_parent)
    files = dict(FILES)
    for package in ('backend', 'src'):
        sources = sorted((root / package).rglob('*.py'))
        if not sources:
            raise ValueError('Missing Python package: ' + package)
        files.update({str(path.relative_to(root)): str(path.relative_to(root)) for path in sources})
    for name in files:
        source = root / name
        if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise ValueError('Missing or unsafe deployment file: ' + name)
    output_parent.mkdir(parents=True, exist_ok=True)
    destination = Path(tempfile.mkdtemp(prefix='hf-backend-', dir=output_parent))
    for name, target in files.items():
        output = destination / target
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / name, output)
    shutil.make_archive(str(destination), 'zip', root_dir=destination)
    return destination


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    destination = package_backend(root, root / '.runtime' / 'deployment')
    print('Upload the CONTENTS of this folder to the root of your Docker Space:')
    print(destination)
    print('ZIP for transfer (extract before uploading):')
    print(destination.with_suffix('.zip'))

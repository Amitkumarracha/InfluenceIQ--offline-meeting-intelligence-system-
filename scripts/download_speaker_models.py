"""Explicit one-time online provisioning of public sherpa-onnx speaker models."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'models' / 'diarization'
FILES = {
    'segmentation.tar.bz2': 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2',
    'embedding.onnx': 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx',
}

SHA256 = {
    'segmentation.tar.bz2': '24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488',
    'embedding.onnx': '1a331345f04805badbb495c775a6ddffcdd1a732567d5ec8b3d5749e3c7a5e4b',
}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, url in FILES.items():
        target = DEST / name
        if not target.exists():
            temporary = target.with_suffix(target.suffix + '.tmp')
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'MAI-local-model-provisioning'})
                with urllib.request.urlopen(request, timeout=60) as source, temporary.open('wb') as output:
                    size = 0
                    while block := source.read(1024 * 1024):
                        size += len(block)
                        if size > 100 * 1024 * 1024:
                            raise ValueError('Unexpectedly large speaker model')
                        output.write(block)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if digest != SHA256[name]:
            raise ValueError('Speaker model checksum mismatch: ' + name)
        manifest[name] = {'url': url, 'sha256': digest, 'bytes': target.stat().st_size}
        print(name, digest, flush=True)
    with tarfile.open(DEST / 'segmentation.tar.bz2') as archive:
        member = next(m for m in archive.getmembers() if m.name.endswith('/model.onnx') and m.isfile())
        if member.size > 100 * 1024 * 1024:
            raise ValueError('Unexpectedly large segmentation model')
        with archive.extractfile(member) as source, (DEST / 'segmentation.onnx.tmp').open('wb') as output:
            shutil.copyfileobj(source, output)
        (DEST / 'segmentation.onnx.tmp').replace(DEST / 'segmentation.onnx')
    manifest['segmentation.onnx'] = {'sha256': hashlib.sha256((DEST / 'segmentation.onnx').read_bytes()).hexdigest()}
    (DEST / 'provisioning.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Speaker models ready for offline inference:', DEST)


if __name__ == '__main__':
    main()

"""Collect read-only camera evidence from the running local field UI server."""
import argparse
import io
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', help='Optional session ID whose saved original image should be copied')
    parser.add_argument('--output', help='New directory for evidence (must not already exist)')
    args = parser.parse_args()
    stamp = datetime.now(ZoneInfo('Asia/Bangkok')).strftime('%Y%m%d-%H%M%S')
    output = Path(args.output or f'outputs/camera-diagnostic-{stamp}')
    output.mkdir(parents=True, exist_ok=False)
    base = 'http://127.0.0.1:8765/api'

    def get(path):
        with urlopen(base + path, timeout=8) as response:
            return response.read(), dict(response.headers)

    report = {'note': 'HTTP round-trip timing, not sensor-to-screen latency', 'samples': []}
    try:
        report['camera_before'] = json.loads(get('/camera/diagnostics')[0])
        for index in range(20):
            start = time.monotonic()
            data, headers = get('/camera/preview')
            elapsed = (time.monotonic() - start) * 1000
            headers = {k.lower():v for k,v in headers.items()}
            report['samples'].append({'request_ms': round(elapsed, 1),
                'sequence': headers.get('x-frame-sequence'), 'cache_age_ms': headers.get('x-frame-age-ms')})
            if index in {0, 19}:
                (output / f'preview-{index:02d}.jpg').write_bytes(data)
            time.sleep(max(0, .1-elapsed/1000))
        report['camera_after'] = json.loads(get('/camera/diagnostics')[0])
        if args.session:
            # IDs are generated as UUID hex; don't allow arbitrary URL path construction.
            if len(args.session) != 32 or any(c not in '0123456789abcdef' for c in args.session):
                raise ValueError('Session ID must contain 32 lowercase hex characters')
            session = json.loads(get('/sessions/' + args.session)[0])
            if not session['images']:
                raise ValueError('Selected session has no saved image')
            view = session['images'][-1]
            data, _ = get('/sessions/' + args.session + '/images/' + view['id'])
            suffix = '.png' if Image.open(io.BytesIO(data)).format == 'PNG' else '.jpg'
            (output / ('saved-original' + suffix)).write_bytes(data)
            report['saved_image_metadata'] = view
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        reference = Image.new('RGB', (600, 240))
        draw = ImageDraw.Draw(reference)
        for index, colour in enumerate(('white','black','red','green','blue')):
            draw.rectangle((index*120,0,(index+1)*120-1,239), fill=colour)
        reference.save(output / 'reference-white-black-red-green-blue.png')
        (output / 'diagnostics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2), encoding='utf-8')
    print(output.resolve())
    if 'error' in report:
        raise SystemExit('Collection incomplete: ' + report['error'])


if __name__ == '__main__':
    main()

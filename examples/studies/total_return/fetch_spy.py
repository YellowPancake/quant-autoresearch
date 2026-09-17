"""Recreate the pinned SPY proxy CSV; never silently refresh to a new snapshot."""
import csv
import hashlib
import io
import json
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    meta = json.loads((HERE / 'manifest.json').read_text())['data']['spy_total_return.csv']
    url = meta['snapshot_url'].replace('github.com/', 'raw.githubusercontent.com/').replace('/blob/', '/')
    request = urllib.request.Request(url, headers={'User-Agent': 'Quant-AutoResearch-data-replay'})
    raw = urllib.request.urlopen(request, timeout=60).read()
    if hashlib.sha256(raw).hexdigest() != meta['source_sha256']:
        raise ValueError('Upstream snapshot hash mismatch')
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=['date', 'sp500'], lineterminator='\n')
    writer.writeheader()
    for row in csv.DictReader(io.StringIO(raw.decode()), delimiter='\t'):
        day = datetime.strptime(row['Date'], '%m/%d/%Y %H:%M:%S').date().isoformat()
        if '2020-01-01' <= day <= '2026-09-11':
            writer.writerow({'date': day, 'sp500': row['Close']})
    output = buffer.getvalue().encode()
    if hashlib.sha256(output).hexdigest() != meta['sha256']:
        raise ValueError('Normalized data hash mismatch')
    (HERE / 'data/spy_total_return.csv').write_bytes(output)
    print('Pinned SPY proxy reproduced and hash verified.')


if __name__ == '__main__':
    main()

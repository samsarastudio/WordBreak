"""Publish an immutable build asset, then atomically update the public game feed.

CI: set GITHUB_TOKEN (Contents read/write on samsarastudio/WordBreak).
Local: --local uses the existing gh login without putting a token in arguments/files.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

REPO = 'samsarastudio/WordBreak'
BRANCH = 'codex/game-updates'
TAG = 'game-updates'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['windows', 'ios', 'content'], required=True)
    parser.add_argument('--version', required=True)
    parser.add_argument('--file', type=Path, required=True)
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', args.version):
        raise SystemExit('Use a numeric game version, for example 1.1.0')
    token = os.environ.get('GITHUB_TOKEN')
    if not token and args.local:
        token = subprocess.check_output(['gh', 'auth', 'token'], text=True).strip()
    if not token:
        print('PUBLICATION SKIPPED: add GITHUB_TOKEN with repository Contents write permission to Codemagic. The IPA remains available in build artifacts.')
        return
    data = args.file.read_bytes()
    if not data or len(data) > 536870912:
        raise SystemExit('Build is empty or exceeds the 512 MiB update limit')
    digest = hashlib.sha256(data).hexdigest()
    pack = None
    if args.platform == 'content':
        pack = json.loads(data)
        if len(data) > 262144 or pack['schema'] != 1 or pack['revision'] < 1 or pack['minAppVersion'] != args.version:
            raise SystemExit('Invalid content package metadata')

    def api(path, method='GET', payload=None, binary=None):
        url = 'https://api.github.com/repos/' + REPO + path
        if path.startswith('https://uploads.github.com/repos/' + REPO + '/'):
            url = path
        body = binary if binary is not None else json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=body, method=method, headers={
            'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
            'Content-Type': 'application/octet-stream' if binary is not None else 'application/json',
            'User-Agent': 'WorldBreakRelease/1.0', 'X-GitHub-Api-Version': '2022-11-28'})
        with urllib.request.urlopen(req, timeout=300) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

    try:
        release = api('/releases/tags/' + TAG)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        release = api('/releases', 'POST', {'tag_name': TAG, 'target_commitish': 'codex/ios-codemagic',
            'name': 'WORLD BREAK RUSH — automatic game updates',
            'body': 'Windows builds update automatically after installation of version 1.1.0 or later. iOS IPA files are unsigned and require personal signing. The version feed is maintained on codex/game-updates.', 'draft': False})
    label = 'Windows' if args.platform == 'windows' else 'iOS-unsigned' if args.platform == 'ios' else 'DLC'
    suffix = '.zip' if args.platform == 'windows' else '.ipa' if args.platform == 'ios' else '.json'
    identity = args.version if pack is None else 'r' + str(pack['revision'])
    filename = f'WorldBreakRush-{label}-{identity}-{digest[:12]}{suffix}'
    assets = api(f'/releases/{release["id"]}/assets?per_page=100')
    asset = next((item for item in assets if item['name'] == filename), None)
    if asset is None:
        upload = release['upload_url'].split('{')[0] + '?name=' + urllib.parse.quote(filename)
        asset = api(upload, 'POST', binary=data)
    if asset['size'] != len(data):
        raise RuntimeError('Published asset size mismatch')
    try:
        api('/git/ref/heads/' + BRANCH)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        baseline = api('/git/ref/heads/main')['object']['sha']
        api('/git/refs', 'POST', {'ref': 'refs/heads/' + BRANCH, 'sha': baseline})
    entry = dict(version=args.version, url=asset['browser_download_url'], sha256=digest, bytes=len(data))
    if pack is not None:
        del entry['version']
        entry.update(revision=pack['revision'], minAppVersion=pack['minAppVersion'])
    for attempt in range(5):
        sha = None
        try:
            current = api('/contents/updates.json?ref=' + BRANCH)
            sha = current['sha']
            feed = json.loads(base64.b64decode(current['content']))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            feed = {'schema': 1}
        previous = feed.get(args.platform)
        if previous:
            def version(value):
                return tuple(map(int, value.split('.'))) + (0,) * (4 - len(value.split('.')))
            before = version(previous['version']) if pack is None else previous['revision']
            after = version(args.version) if pack is None else pack['revision']
            if before > after:
                raise RuntimeError('Refusing to roll the update channel backwards')
            if before == after and previous['sha256'] != digest:
                raise RuntimeError('A different build already uses this version; increment the game version')
        feed[args.platform] = entry
        body = {'message': f'Publish {args.platform} game {args.version}', 'branch': BRANCH,
                'content': base64.b64encode((json.dumps(feed, indent=2) + '\n').encode()).decode()}
        if sha:
            body['sha'] = sha
        try:
            api('/contents/updates.json', 'PUT', body)
            break
        except urllib.error.HTTPError as error:
            if error.code != 409 or attempt == 4:
                raise
    print(f'Published {args.platform} {args.version}: {asset["browser_download_url"]}')

if __name__ == '__main__':
    main()

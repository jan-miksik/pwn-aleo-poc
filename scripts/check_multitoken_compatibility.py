#!/usr/bin/env python3
"""Guard the ABI, storage, constructors and finalizers against the reviewed release.

Run after building pwn_loan_poc (which also compiles its dependencies). The
snapshot is updated only for an intentional reviewed protocol change. Pure
function bodies may change; state layout, authorization at upgrade and on-chain
instruction order must not silently change along with a readability refactor.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / 'tests/fixtures/multitoken-compatibility.json'
PROGRAMS = ('pwn_config_poc', 'pwn_hub_poc', 'pwn_proposal_poc', 'pwn_loan_poc')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def fingerprint(bytecode, abi):
    sections = re.split(r'(?=^(?:struct|record|mapping|closure|function|finalize) \w+:|^constructor:)',
                        bytecode, flags=re.M)
    finalizers = {}
    storage = []
    for section in sections:
        if section.startswith('finalize '):
            name = section.split(':', 1)[0].removeprefix('finalize ')
            finalizers[name] = digest(section.strip())
        elif not section.startswith(('closure ', 'function ')):
            storage.append(section.strip())
    return dict(abi_sha256=digest(json.dumps(abi, sort_keys=True, separators=(',', ':'))),
                storage_and_constructor_sha256=digest('\n\n'.join(storage)),
                finalizers=finalizers)


def check(build, baseline):
    failures = []
    count = 0
    for name, expected in baseline['programs'].items():
        directory = build / name
        bytecode = (directory / f'{name}.aleo').read_text()
        actual = fingerprint(bytecode, json.loads((directory / 'abi.json').read_text()))
        for key in ('abi_sha256', 'storage_and_constructor_sha256'):
            if actual[key] != expected[key]:
                failures.append(f'{name}: {key} changed')
        for fn in sorted(set(actual['finalizers']) | set(expected['finalizers'])):
            if actual['finalizers'].get(fn) != expected['finalizers'].get(fn):
                failures.append(f'{name}/finalize {fn}: instructions changed')
        count += len(actual['finalizers'])
    if failures:
        raise AssertionError('Compatibility regression against the reviewed release snapshot:\n' + '\n'.join(failures))
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true', help='replace the baseline after an intentional reviewed protocol change')
    options = parser.parse_args()
    build = ROOT / 'pwn_loan_poc/build'
    if options.update:
        programs = {}
        for name in PROGRAMS:
            directory = build / name
            programs[name] = fingerprint(
                (directory / f'{name}.aleo').read_text(),
                json.loads((directory / 'abi.json').read_text()))
        BASELINE.write_text(json.dumps(dict(
            compiler='Leo 4.4.2 (f3578da)',
            description='Reviewed security-hardened ABI, state/constructor, and finalizer fingerprints. Update only for an intentional reviewed protocol change.',
            programs=programs), indent=2) + '\n')
        print(f'Updated compatibility baseline for {len(programs)} programs')
        return
    baseline = json.loads(BASELINE.read_text())
    count = check(build, baseline)
    print(f'PASS compatibility: {len(baseline["programs"])} ABIs / storage layouts / constructors and {count} finalizers unchanged')


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Seeded differential fuzzing of the actual generated Leo arithmetic.

No RPC, deployment, third-party Python packages, or Python copy of the Leo
implementation. Expected values use unbounded multiplication/division. Keep
the seed and case index from results.json to reproduce a failure.
"""
import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
import re
import subprocess

from generate_multitoken import MATH, ROOT
from multitoken_test_support import arithmetic_rejected

U128_MAX = 2**128 - 1
U64_MAX = 2**64 - 1
YEAR_BPS = 315360000000


@dataclass(frozen=True)
class Case:
    operation: str
    values: tuple

    def expected(self):
        if self.operation == 'rounded':
            amount, ratio = self.values
            return (amount * ratio + 9999) // 10000
        if self.operation == 'accrued':
            principal, apr, elapsed = self.values
            return principal * apr * elapsed // YEAR_BPS
        if self.operation == 'native':
            return self.values[0]
        raise ValueError(self.operation)

    def arguments(self):
        types = {'rounded': (128, 64), 'accrued': (128, 32, 32), 'native': (128,)}
        return [f'{v}u{bits}' for v, bits in zip(self.values, types[self.operation])]

    def limit(self):
        return U64_MAX if self.operation == 'native' else U128_MAX


def corpus(seed, count):
    cases = [Case('rounded', (a, r))
             for a in (0, 1, 9999, 10000, 10001, 2**64, U128_MAX)
             for r in (0, 1, 9999, 10000, 10001, U64_MAX)]
    cases += [Case('accrued', (a, apr, seconds))
              for a in (0, 1, YEAR_BPS - 1, YEAR_BPS, YEAR_BPS + 1, U128_MAX)
              for apr, seconds in ((0, 2**32 - 1), (1, 1), (10000, 31536000),
                                   (10**9, 2**32 - 1))]
    cases += [Case('native', (a,)) for a in (0, 1, U64_MAX, U64_MAX + 1, U128_MAX)]
    # Last representable result and first overflowing result at several ratios.
    for ratio in (1, 10001, 15000, U64_MAX):
        threshold = min(U128_MAX, U128_MAX * 10000 // ratio)
        cases.extend(Case('rounded', (a, ratio))
                     for a in (threshold - 1, threshold, threshold + 1) if 0 <= a <= U128_MAX)
    for apr, seconds in ((1, 1), (10000, 31536000), (10**9, 2**32 - 1)):
        threshold = min(U128_MAX, ((U128_MAX + 1) * YEAR_BPS - 1) // (apr * seconds))
        cases.extend(Case('accrued', (a, apr, seconds))
                     for a in (threshold - 1, threshold, threshold + 1) if 0 <= a <= U128_MAX)
    rng = random.Random(seed)
    for _ in range(count):
        if rng.randrange(2):
            ratio = rng.choice((rng.getrandbits(64), rng.randrange(1, 100001)))
            limit = min(U128_MAX, U128_MAX * 10000 // max(1, ratio))
            amount = rng.choice((rng.getrandbits(128), rng.randrange(limit + 1)))
            cases.append(Case('rounded', (amount, ratio)))
        else:
            apr, seconds = rng.randrange(10**9 + 1), rng.getrandbits(32)
            limit = min(U128_MAX, U128_MAX * YEAR_BPS // max(1, apr * seconds))
            amount = rng.choice((rng.getrandbits(128), rng.randrange(limit + 1)))
            cases.append(Case('accrued', (amount, apr, seconds)))
    return cases


def stage(directory):
    """Use exactly the math fragment embedded in the production generator."""
    (directory / 'src').mkdir(parents=True, exist_ok=True)
    (directory / 'program.json').write_text(json.dumps(dict(
        program='pwn_math_fuzz.aleo', version='0.1.0', description='Local arithmetic oracle',
        license='MIT', leo='4.4.2', dependencies=[]), indent=2) + '\n')
    (directory / 'src/main.leo').write_text(MATH + '''
program pwn_math_fuzz.aleo {
    fn check_rounded(amount: u128, ratio: u64) -> u128 { return rounded(amount, ratio); }
    fn check_accrued(amount: u128, apr: u32, elapsed: u32) -> u128 { return accrued(amount, apr, elapsed); }
    fn check_native(amount: u128) -> u64 { return amount as u64; }
    @noupgrade constructor() {}
}
''')


def run_case(case, directory, index):
    output = directory / 'output.json'
    output.unlink(missing_ok=True)
    command = [str(ROOT / 'scripts/leo'), 'run', 'check_' + case.operation,
               *case.arguments(), '--path', str(directory), '--offline',
               '--network', 'testnet', '--endpoint', 'http://127.0.0.1:1',
               '--json-output=' + str(output)]
    process = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=60)
    log = re.sub(r'\x1b\[[0-9;]*m', '', process.stdout)
    (directory / f'{index:04d}.log').write_text(log)
    expected = case.expected()
    overflow = expected > case.limit()
    if overflow:
        # Reject infrastructure/compiler failures: require an arithmetic error.
        ok = arithmetic_rejected(process.returncode, log, case.operation)
        actual = None
    else:
        actual = json.loads(output.read_text()).get('outputs') if output.exists() else None
        bits = 64 if case.operation == 'native' else 128
        ok = process.returncode == 0 and actual == [f'{expected}u{bits}']
    return dict(index=index, **asdict(case), expected=str(expected), overflow=overflow,
                actual=actual, passed=ok, returncode=process.returncode,
                cli_panic='internal compiler error: unexpected panic' in log)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, default=20260920)
    parser.add_argument('--cases', type=int, default=100, help='Random cases in addition to fixed boundaries')
    parser.add_argument('--case', type=int, help='Replay a single corpus index')
    options = parser.parse_args(argv)
    if options.cases < 0:
        parser.error('--cases must be nonnegative')
    cases = corpus(options.seed, options.cases)
    if options.case is not None and not 0 <= options.case < len(cases):
        parser.error('--case is outside the corpus')
    directory = ROOT / 'artifacts/multitoken/fuzz' / f'seed-{options.seed}'
    stage(directory)
    report = dict(seed=options.seed, random_cases=options.cases, completed=False, cases=[])
    try:
        for index, case in enumerate(cases):
            if options.case is not None and index != options.case:
                continue
            result = run_case(case, directory, index)
            report['cases'].append(result)
            if not result['passed']:
                raise AssertionError(f'Arithmetic mismatch: {result}; log: {directory / f"{index:04d}.log"}')
            if len(report['cases']) % 20 == 0:
                print(f"PASS {len(report['cases'])} arithmetic cases (seed {options.seed})", flush=True)
        report['completed'] = True
    finally:
        (directory / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"PASS {len(report['cases'])} Leo arithmetic cases; seed={options.seed}", flush=True)


if __name__ == '__main__':
    main()

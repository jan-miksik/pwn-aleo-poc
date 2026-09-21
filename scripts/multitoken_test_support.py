"""Strict result classification shared by the local test runners."""
import re


def accepted(code, result, log):
    return (code == 0 and result.get('broadcast', {}).get('confirmed') is True
            and 'Transaction accepted.' in log)


def rejection_reason(code, result, log, node_log=''):
    """Return evidence of a protocol failure, never merely an unsuccessful CLI.

    Compiler warnings contain words such as 'assert'; CLI help also mentions
    'rejected transactions'. Neither is evidence that a negative test passed.
    Leo 4.4.2 hides the statePaths response, so a missing record commitment
    requires corroboration from the loopback node for that exact commitment.
    """
    if ('Transaction accepted.' in log
            or result.get('broadcast', {}).get('confirmed') is True):
        return None
    if re.search(r'^Transaction rejected\.$', log, re.M):
        return 'finalize rejection'
    if code != 0 and re.search(r'(?:^|: )Stack (?:evaluation|execution) failed: Instruction .+ failed:', log, re.M):
        return 'VM instruction failure'
    missing = re.search(r'^Failed to fetch from http://127\.0\.0\.1:\d+/testnet/statePaths\?commitments=(\d+field)\s*$', log, re.M)
    if code != 0 and missing and f"Commitment '{missing[1]}' does not exist" in node_log:
        return 'record commitment absent from ledger'
    return None


def arithmetic_rejected(code, log, operation):
    """Recognize checked overflow, including Leo 4.4.2's arithmetic panic."""
    if code == 0:
        return False
    if operation == 'native':
        return "Failed to convert 'u128' into 'u64'" in log
    return bool(re.search(
        r'Integer (?:multiplication|addition) failed on: \d+u128 and \d+u128', log))


def unsigned(value, bits=128):
    """Decode an integer mapping; absence is zero, malformed values are errors."""
    if value is None:
        return 0
    match = re.fullmatch(r'(\d+)u' + str(bits), value)
    if not match or int(match[1]) >= 2 ** bits:
        raise ValueError(f'Expected u{bits}, got {value!r}')
    return int(match[1])


def private_payout_matches(plain, owner, amount, bits):
    """Match entire fields: an expected 600 must not match an actual 1600."""
    return (bool(re.search(r'\bowner:\s*' + re.escape(owner) + r'\.private\s*[,}]', plain))
            and bool(re.search(r'\b(?:amount|microcredits):\s*' + str(amount)
                               + 'u' + str(bits) + r'\.private\s*[,}]', plain)))

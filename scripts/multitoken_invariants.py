"""Model-based lifecycle tests on the real loopback devnode.

The model records economic events only; it never derives expected balances
from contract mappings. Every action checks all assets and all positions.
Deterministic regressions precede seeded random scheduling, then every live
position is settled. This suite deliberately skips proofs (see make security).
"""
from dataclasses import dataclass
import json
import random
import re

from multitoken_test_support import unsigned


@dataclass
class Commitment:
    credit: str
    collateral: str
    salt: int
    terms: str
    id: str
    collateral_ratio: int
    repayment_ratio: int
    available: int
    terms_hash: str
    credit_asset: str
    repayments: int = 0
    closed: bool = False


@dataclass
class Loan:
    commitment: Commitment
    salt: int
    witness: str
    id: str
    collateral: int
    repayment: int
    state: str
    status: int = 1


class Scenario:
    def __init__(self, runner, seed):
        self.t = runner
        self.rng = random.Random(seed)
        self.seed = seed
        self.commitments = []
        self.loans = []
        self.trace = []
        self.surplus = {(owner, asset): 0 for owner in (runner.P, runner.L) for asset in runner.ASSETS}

    def record(self, action, **parameters):
        # Persist BEFORE executing: the final trace entry identifies a failure.
        self.trace.append(dict(action=action, **parameters))
        (self.t.OUT / 'trace.json').write_text(json.dumps(
            dict(seed=self.seed, actions=self.trace), indent=2) + '\n')

    def snapshot(self):
        t = self.t
        snapshot = {}
        for owner in (t.P, t.L):
            for asset, (program, family) in t.ASSETS.items():
                snapshot[f'{owner}/{asset}/liability'] = unsigned(t.mapping(owner, 'liabilities', f"'{program}'"))
                snapshot[f'{owner}/{asset}/reserve'] = unsigned(t.mapping(
                    program + '.aleo', 'account' if family == 1 else 'balances', owner), 64 if family == 1 else 128)
        for c in self.commitments:
            for name in ('terms_hash', 'credit_assets', 'available_credit', 'repayments', 'closed'):
                snapshot[f'{c.id}/{name}'] = t.mapping(t.P, name, c.id)
        for loan in self.loans:
            snapshot[f'{loan.id}/state'] = t.mapping(t.L, 'loans', loan.id)
        return snapshot

    def verify(self):
        t = self.t
        state = self.snapshot()
        for asset in t.ASSETS:
            proposal = sum(c.available + c.repayments for c in self.commitments if c.credit == asset)
            collateral = sum(loan.collateral for loan in self.loans
                             if loan.commitment.collateral == asset and loan.status == 1)
            for owner, expected in ((t.P, proposal), (t.L, collateral)):
                assert state[f'{owner}/{asset}/liability'] == expected, (owner, asset, 'aggregate liability', expected, state)
                assert state[f'{owner}/{asset}/reserve'] == expected + self.surplus[owner, asset], (owner, asset, 'reserve conservation', state)
        for c in self.commitments:
            for name, expected in (('available_credit', f'{c.available}u128'), ('repayments', f'{c.repayments}u128'),
                                   ('closed', str(c.closed).lower()), ('terms_hash', c.terms_hash),
                                   ('credit_assets', c.credit_asset)):
                assert state[f'{c.id}/{name}'] == expected, (c.id, name, expected, state)
            assert not c.closed or c.available == 0, 'closed commitment still has drawable credit'
        for loan in self.loans:
            assert state[f'{loan.id}/state'] == loan.state.replace('status: 1u8', f'status: {loan.status}u8'), ('loan state', loan.id, state)
        t.check(f'invariants after action {len(self.trace)} ({self.trace[-1]["action"] if self.trace else "initial"})', True)

    def reject(self, function, args, key=None):
        before = self.snapshot()
        self.t.execute(function, args, key or self.t.AK, fail=True)
        assert self.snapshot() == before, f'Rejected {function} mutated protocol state or reserves'
        self.verify()

    def open(self, credit, collateral, duration=100000):
        t = self.t
        salt = 10000 + len(self.commitments)
        cr, rr = self.rng.choice((10001, 15000, 19999)), self.rng.choice((10000, 11001, 12007))
        amount = self.rng.randrange(901, 1401)
        terms = (t.terms(credit, collateral, salt, duration=duration)
                 .replace('100u128', '1u128').replace('15000u64', f'{cr}u64')
                 .replace('11000u64', f'{rr}u64'))
        self.record('open', credit=credit, collateral=collateral, salt=salt, amount=amount,
                    collateral_ratio=cr, repayment_ratio=rr, duration=duration)
        cid = t.execute(t.P + '::open_' + t.route(credit),
                        ['1field', terms, t.private(credit, amount), f'{amount}u128', f'{salt}field'] + t.proofs(credit))[-2]
        c = Commitment(credit, collateral, salt, terms, cid, cr, rr, amount,
                       t.mapping(t.P, 'terms_hash', cid), t.mapping(t.P, 'credit_assets', cid))
        self.commitments.append(c)
        self.verify()
        return c

    def draw(self, c, amount=None, duplicate=None):
        t = self.t
        amount = amount if amount is not None else self.rng.randint(1, min(600, c.available))
        salt = duplicate.salt if duplicate else 20000 + len(self.loans)
        collateral = (amount * c.collateral_ratio + 9999) // 10000
        repayment = (amount * c.repayment_ratio + 9999) // 10000
        self.record('duplicate_draw' if duplicate else 'draw', commitment=c.id, amount=amount, salt=salt)
        args = ['1field', c.id, c.terms, f'{amount}u128', t.private(c.collateral, collateral, t.B, t.BK), f'{salt}field'] + t.proofs(c.collateral)
        fn = t.L + '::accept_' + t.route(c.credit) + '_' + t.route(c.collateral)
        if duplicate or c.closed or amount > c.available or amount > 600:
            self.reject(fn, args, t.BK)
            return None
        output = t.execute(fn, args, t.BK)
        witness = output[-2]
        assert f'owner: {t.B}' in output[-4], 'credit paid to wrong owner'
        t.decrypt_payout(c.credit, amount, t.BK, t.B)
        for field, expected in (('credit_amount', amount), ('collateral_amount', collateral), ('repayment_amount', repayment)):
            assert re.search(rf'\b{field}: {expected}u128\b', witness), (field, witness)
        loan = Loan(c, salt, witness, t.lid(witness), collateral, repayment,
                    t.mapping(t.L, 'loans', t.lid(witness)))
        assert 'status: 1u8' in loan.state
        self.loans.append(loan)
        c.available -= amount
        self.verify()
        return loan

    def repay(self, loan, bad_salt=False, underpay=False):
        t, c = self.t, loan.commitment
        amount = loan.repayment - 1 if underpay else loan.repayment + self.rng.randrange(4)
        salt = loan.salt + 999999 if bad_salt else loan.salt
        self.record('repay', loan=loan.id, amount=amount, bad_salt=bad_salt, underpay=underpay)
        args = [loan.witness, t.private(c.credit, max(1, amount), t.B, t.BK), f'{amount}u128', f'{salt}field'] + t.proofs(c.credit)
        fn = t.L + '::repay_' + t.route(c.credit) + '_' + t.route(c.collateral)
        if loan.status != 1 or bad_salt or underpay:
            self.reject(fn, args, t.BK)
            return
        output = t.execute(fn, args, t.BK)
        assert f'owner: {t.B}' in output[-2], 'collateral paid to wrong owner'
        t.decrypt_payout(c.collateral, loan.collateral, t.BK, t.B)
        loan.status = 2
        c.repayments += amount
        self.verify()

    def cancel(self, c):
        self.record('cancel', commitment=c.id, amount=c.available)
        args = [c.id, c.terms, f'{c.salt}field', f'{c.available}u128']
        fn = self.t.P + '::cancel_' + self.t.route(c.credit)
        if c.closed:
            self.reject(fn, args)
            return
        self.t.execute(fn, args)
        c.available, c.closed = 0, True
        self.verify()

    def withdraw(self, c, excessive=False):
        amount = c.repayments + 1 if excessive else self.rng.randint(1, c.repayments)
        self.record('withdraw', commitment=c.id, amount=amount)
        args = [c.id, c.terms, f'{c.salt}field', f'{amount}u128']
        fn = self.t.P + '::withdraw_' + self.t.route(c.credit)
        if excessive:
            self.reject(fn, args)
            return
        self.t.execute(fn, args)
        c.repayments -= amount
        self.verify()

    def claim(self, loan, mature=False):
        t, c = self.t, loan.commitment
        self.record('claim', loan=loan.id, mature=mature)
        fn, args = t.L + '::claim_' + t.route(c.collateral), [loan.witness, f'{c.salt}field']
        if not mature or loan.status != 1:
            self.reject(fn, args)
            return
        output = t.execute(fn, args)
        assert f'owner: {t.DEV}' in output[-2], 'default collateral paid to wrong owner'
        t.decrypt_payout(c.collateral, loan.collateral)
        loan.status = 3
        self.verify()

    def random_step(self):
        c = self.rng.choice(self.commitments)
        action = self.rng.choice(('draw', 'repay', 'cancel', 'withdraw', 'overwithdraw', 'bad_salt', 'underpay', 'claim'))
        if action == 'draw':
            self.draw(c, 1 if c.closed or not c.available else None)
        elif action == 'cancel':
            self.cancel(c)
        elif action in ('withdraw', 'overwithdraw'):
            self.withdraw(c, excessive=action == 'overwithdraw' or c.repayments == 0)
        elif self.loans:
            loan = self.rng.choice(self.loans)
            if action == 'claim':
                self.claim(loan)
            else:
                self.repay(loan, bad_salt=action == 'bad_salt', underpay=action == 'underpay')


def run(t, seed, steps):
    scenario = Scenario(t, seed)
    scenario.verify()
    # Shared credit, different collateral; every supported concrete asset.
    for credit, collateral in (('sol', 'usad'), ('sol', 'wbtc'), ('aleo', 'sol'),
                                ('usdcx', 'aleo'), ('wbtc', 'usdcx'), ('usad', 'wbtc')):
        c = scenario.open(credit, collateral)
        scenario.draw(c, 301)
        scenario.draw(c, 299)
    first, second = scenario.loans[:2]
    c = first.commitment
    scenario.draw(c, 1, duplicate=first)
    scenario.claim(first)
    scenario.repay(first, bad_salt=True)
    scenario.repay(first, underpay=True)
    scenario.repay(first)
    scenario.withdraw(c)
    scenario.withdraw(c, excessive=True)
    scenario.cancel(c)
    scenario.draw(c, 1)  # lock runs before draw rejects: rollback across programs
    scenario.repay(second)  # cancellation must not strand outstanding loans
    scenario.repay(first)  # terminal status cannot pay twice
    scenario.cancel(c)
    # Unsolicited reserves must not inflate lender claims or block settlement.
    scenario.record('donate', amount=7)
    t.execute('credits.aleo::transfer_public', [t.P, '7u64'])
    scenario.surplus[t.P, 'aleo'] += 7
    scenario.verify()
    for _ in range(steps):
        scenario.random_step()
    # Default changes aggregate obligations just like repayment, but must never
    # create lender repayment credit. Exercise each collateral transfer family.
    for collateral in ('aleo', 'sol', 'usdcx'):
        c = scenario.open('sol', collateral, duration=10)
        loan = scenario.draw(c, 301)
        for _ in range(11):
            t.rpc('block/create', {})
        scenario.claim(loan, mature=True)
        scenario.claim(loan, mature=True)
        scenario.repay(loan)
    for loan in scenario.loans:
        if loan.status == 1:
            scenario.repay(loan)
    for commitment in scenario.commitments:
        if not commitment.closed:
            scenario.cancel(commitment)
        if commitment.repayments:
            # A single final withdrawal, independent of earlier partial ones.
            scenario.record('drain_repayments', commitment=commitment.id, amount=commitment.repayments)
            t.execute(t.P + '::withdraw_' + t.route(commitment.credit),
                      [commitment.id, commitment.terms, f'{commitment.salt}field', f'{commitment.repayments}u128'])
            commitment.repayments = 0
            scenario.verify()
    t.check('all positions settled; only donated surplus remains',
            all(loan.status != 1 for loan in scenario.loans)
            and all(c.closed and c.available == c.repayments == 0 for c in scenario.commitments))

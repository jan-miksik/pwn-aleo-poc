"""Fast regressions for code generation and the trustworthiness of test results."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from generate_multitoken import ROOT, MATH, generate, render_programs
from multitoken_fuzz import Case, corpus, stage, U128_MAX, U64_MAX
from multitoken_test_support import accepted, arithmetic_rejected, rejection_reason, unsigned, private_payout_matches
from multitoken_invariants import Commitment, Loan, Scenario
from check_multitoken_compatibility import fingerprint, check as check_compatibility


class GenerationTests(unittest.TestCase):
    def test_generated_files_are_current(self):
        for relative, content in render_programs().items():
            with self.subTest(path=relative):
                self.assertEqual((ROOT / relative).read_text(), content,
                                 'Generated files are stale: run make build')

    def test_generation_is_deterministic_and_can_target_a_temporary_directory(self):
        first = render_programs()
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            generate(directory)
            generate(directory)
            self.assertEqual(first, render_programs())
            for relative, content in first.items():
                self.assertEqual((Path(directory) / relative).read_text(), content)

    def test_dynamic_assets_do_not_become_static_dependencies(self):
        allowed = {'credits.aleo', 'pwn_config_poc.aleo', 'pwn_hub_poc.aleo', 'pwn_proposal_poc.aleo'}
        for relative, content in render_programs().items():
            if relative.endswith('program.json'):
                dependencies = json.loads(content)['dependencies']
                self.assertLessEqual({d['name'] for d in dependencies}, allowed)

    def test_fuzz_executes_the_production_math_fragment(self):
        with tempfile.TemporaryDirectory() as directory:
            stage(Path(directory))
            self.assertTrue((Path(directory) / 'src/main.leo').read_text().startswith(MATH))
        programs = render_programs()
        for program in ('pwn_proposal_poc', 'pwn_loan_poc'):
            self.assertIn(MATH, programs[f'{program}/src/main.leo'])


class CompatibilityTests(unittest.TestCase):
    BYTECODE = '''program fixture.aleo;

struct State:
    amount as u128;

mapping balances:
    key as address.public;
    value as u128.public;

closure helper:
    input r0 as u128;
    output r0 as u128;

function pay:
    input r0 as u128.public;
    async pay r0 into r1;
    output r1 as fixture.aleo/pay.future;

finalize pay:
    input r0 as u128.public;
    assert.eq r0 1u128;
    set r0 into balances[self.caller];

constructor:
    assert.eq edition 0u16;
'''

    def test_only_internal_proof_code_can_change_without_changing_fingerprint(self):
        expected = fingerprint(self.BYTECODE, {})
        self.assertEqual(expected, fingerprint(self.BYTECODE.replace('output r0 as u128;',
                          'add r0 0u128 into r1;\n    output r1 as u128;'), {}))
        for mutation in (
            self.BYTECODE.replace('assert.eq r0 1u128;', 'assert.eq r0 2u128;'),
            self.BYTECODE.replace('value as u128.public;', 'value as u64.public;'),
            self.BYTECODE.replace('assert.eq edition 0u16;', 'assert.eq edition 1u16;'),
            self.BYTECODE.replace('    assert.eq r0 1u128;\n    set r0 into balances[self.caller];',
                                  '    set r0 into balances[self.caller];\n    assert.eq r0 1u128;'),
            self.BYTECODE.replace('finalize pay:', 'finalize another:'),
        ):
            self.assertNotEqual(expected, fingerprint(mutation, {}))
        self.assertNotEqual(expected, fingerprint(self.BYTECODE, {'changed': True}))

    def test_guard_reports_changed_or_missing_finalizers(self):
        with tempfile.TemporaryDirectory() as directory:
            build = Path(directory)
            program = build / 'fixture'
            program.mkdir()
            (program / 'abi.json').write_text('{}')
            path = program / 'fixture.aleo'
            baseline = {'programs': {'fixture': fingerprint(self.BYTECODE, {})}}
            path.write_text(self.BYTECODE)
            self.assertEqual(check_compatibility(build, baseline), 1)
            path.write_text(self.BYTECODE.replace('finalize pay:', 'finalize another:'))
            with self.assertRaisesRegex(AssertionError, 'finalize pay: instructions changed'):
                check_compatibility(build, baseline)


class ResultTests(unittest.TestCase):
    def test_private_payout_amount_is_an_exact_field_match(self):
        plain = '{ owner: aleo1recipient.private, amount: 1600u128.private, _nonce: 1group.public }'
        self.assertTrue(private_payout_matches(plain, 'aleo1recipient', 1600, 128))
        self.assertFalse(private_payout_matches(plain, 'aleo1recipient', 600, 128))
        self.assertFalse(private_payout_matches(plain, 'aleo1recipient', 1600, 64))
        self.assertFalse(private_payout_matches(plain, 'aleo1other', 1600, 128))
        self.assertTrue(private_payout_matches('{ owner: aleo1recipient.private, microcredits: 7u64.private }',
                                              'aleo1recipient', 7, 64))

    def test_spending_decrypted_payout_preserves_each_token_abi(self):
        import multitoken_integration as runner
        for asset, program, args in (
            ('aleo', 'credits.aleo', ['record', 'owner', '1u64']),
            ('sol', 'arc20_sol.aleo', ['record', 'owner', '1u128']),
            ('usad', 'usad_stablecoin.aleo', ['owner', '1u128', 'record', runner.PROOFS]),
        ):
            with self.subTest(asset=asset), patch.object(runner, 'decrypt_payout', return_value='record') as decrypt, \
                    patch.object(runner, 'execute') as execute, patch.object(runner, 'check'):
                runner.spend_payout(asset, 7, 'key', 'owner')
                decrypt.assert_called_once_with(asset, 7, 'key', 'owner')
                execute.assert_called_once_with(program + '::transfer_private_to_public', args, 'key')

    def test_acceptance_requires_cli_and_chain_agreement(self):
        result = {'broadcast': {'confirmed': True}}
        self.assertTrue(accepted(0, result, 'Transaction accepted.'))
        for code, value, log in ((1, result, 'Transaction accepted.'),
                                  (0, {}, 'Transaction accepted.'), (0, result, 'Timeout')):
            self.assertFalse(accepted(code, value, log))

    def test_negative_tests_do_not_accept_tool_or_rpc_failures(self):
        for log in ('Connection refused', 'Error: function not found',
                    'Error: source file not found', 'Compiler internal error',
                    '  10 | assert(before >= total);\nFailed to connect',
                    '(use this to check for rejected transactions)\nTimeout'):
            with self.subTest(log=log):
                self.assertIsNone(rejection_reason(1, {}, log))

    def test_finalization_and_vm_rejection(self):
        self.assertEqual(rejection_reason(0, {}, 'Transaction rejected.\n'), 'finalize rejection')
        for prefix in ('', 'Error [ECLI0377045]: Failed to evaluate program: '):
            self.assertEqual(rejection_reason(1, {}, prefix +
                "Stack evaluation failed: Instruction (assert.eq r0 r1;) at index 0 failed: 'assert.eq' failed"),
                'VM instruction failure')

    def test_confirmed_transactions_cannot_pass_a_negative_test(self):
        self.assertIsNone(rejection_reason(1, {'broadcast': {'confirmed': True}}, 'Transaction rejected.'))
        self.assertIsNone(rejection_reason(1, {}, 'Transaction rejected.\nTransaction accepted.'))

    def test_missing_record_needs_exact_node_evidence(self):
        log = 'Failed to fetch from http://127.0.0.1:4321/testnet/statePaths?commitments=123field\n'
        self.assertIsNone(rejection_reason(1, {}, log))
        self.assertIsNone(rejection_reason(1, {}, log, "Commitment '456field' does not exist"))
        self.assertEqual(rejection_reason(1, {}, log, "Commitment '123field' does not exist"),
                         'record commitment absent from ledger')

    def test_arithmetic_errors_are_not_arbitrary_panics(self):
        self.assertTrue(arithmetic_rejected(101, 'Integer multiplication failed on: 99u128 and 99u128', 'rounded'))
        self.assertTrue(arithmetic_rejected(213, "Failed to convert 'u128' into 'u64'", 'native'))
        for text in ('internal compiler error: unexpected panic', 'overflow in compiler',
                     'Connection refused', 'assert failed'):
            self.assertFalse(arithmetic_rejected(1, text, 'rounded'))
        self.assertFalse(arithmetic_rejected(0, 'Integer addition failed on: 1u128 and 2u128', 'rounded'))

    def test_mapping_parser_rejects_malformed_or_truncated_amounts(self):
        self.assertEqual(unsigned(None), 0)
        self.assertEqual(unsigned(f'{U128_MAX}u128'), U128_MAX)
        self.assertEqual(unsigned(f'{U64_MAX}u64', 64), U64_MAX)
        for value in ('1u64', '-1u128', '1', '0u128garbage', f'{2**128}u128'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                unsigned(value)


class CorpusTests(unittest.TestCase):
    def test_corpus_is_replayable(self):
        self.assertEqual(corpus(42, 100), corpus(42, 100))
        self.assertNotEqual(corpus(42, 100), corpus(43, 100))
        self.assertEqual(corpus(42, 100)[:len(corpus(42, 0))], corpus(43, 0))

    def test_boundaries_include_valid_and_overflowing_results_for_every_operation(self):
        cases = corpus(42, 0)
        for operation in ('rounded', 'accrued', 'native'):
            group = [c for c in cases if c.operation == operation]
            self.assertTrue(any(c.expected() > c.limit() for c in group))
            self.assertTrue(any(c.expected() == c.limit() for c in group))
            self.assertTrue(any(c.expected() == 0 for c in group))
        self.assertIn(Case('rounded', (U128_MAX, 10000)), cases)
        self.assertIn(Case('native', (U64_MAX + 1,)), cases)


class InvariantOracleTests(unittest.TestCase):
    def setUp(self):
        self.state = {
            ('proposal', 'liabilities', "'credits'"): '17u128',
            ('credits.aleo', 'account', 'proposal'): '20u64',
            ('loan', 'liabilities', "'token'"): '13u128',
            ('token.aleo', 'balances', 'loan'): '13u128',
            ('proposal', 'terms_hash', '1field'): '3field',
            ('proposal', 'credit_assets', '1field'): 'credit descriptor',
            ('proposal', 'available_credit', '1field'): '10u128',
            ('proposal', 'repayments', '1field'): '7u128',
            ('proposal', 'closed', '1field'): 'false',
            ('loan', 'loans', '2field'): '{ witness_hash: 4field, maturity: 50u32, start: 5i64, status: 1u8 }',
        }
        runner = SimpleNamespace(P='proposal', L='loan', ASSETS={'aleo': ('credits', 1), 'token': ('token', 2)},
                                 mapping=lambda p, n, k: self.state.get((p, n, k)), check=lambda *args: None)
        self.scenario = Scenario(runner, 42)
        commitment = Commitment('aleo', 'token', 1, 'terms', '1field', 10000, 10000, 10,
                                '3field', 'credit descriptor', repayments=7)
        loan = Loan(commitment, 2, 'witness', '2field', 13, 13,
                    self.state['loan', 'loans', '2field'])
        self.scenario.commitments.append(commitment)
        self.scenario.loans.append(loan)
        self.scenario.surplus['proposal', 'aleo'] = 3

    def test_consistent_balances_with_unclaimed_donation(self):
        self.scenario.verify()

    def test_oracle_detects_corrupt_accounting_and_immutable_fields(self):
        for key, corrupt in (
            (('proposal', 'liabilities', "'credits'"), '18u128'),
            (('credits.aleo', 'account', 'proposal'), '19u64'),
            (('token.aleo', 'balances', 'loan'), '12u128'),
            (('proposal', 'available_credit', '1field'), '9u128'),
            (('proposal', 'repayments', '1field'), '8u128'),
            (('proposal', 'terms_hash', '1field'), '9field'),
            (('proposal', 'credit_assets', '1field'), 'wrong descriptor'),
            (('loan', 'loans', '2field'), '{ witness_hash: 4field, maturity: 51u32, start: 5i64, status: 1u8 }'),
        ):
            original = self.state[key]
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.state[key] = corrupt
                self.scenario.verify()
            self.state[key] = original

    def test_closed_positions_cannot_retain_drawable_credit(self):
        self.scenario.commitments[0].closed = True
        self.state['proposal', 'closed', '1field'] = 'true'
        with self.assertRaisesRegex(AssertionError, 'closed commitment'):
            self.scenario.verify()

    def test_terminal_loans_must_release_collateral_liabilities(self):
        self.scenario.loans[0].status = 3
        with self.assertRaises(AssertionError):
            self.scenario.verify()

    def test_terminal_state_cannot_be_reopened(self):
        self.scenario.loans[0].status = 2
        self.state['loan', 'liabilities', "'token'"] = '0u128'
        self.state['token.aleo', 'balances', 'loan'] = '0u128'
        with self.assertRaises(AssertionError):
            self.scenario.verify()


if __name__ == '__main__':
    unittest.main()

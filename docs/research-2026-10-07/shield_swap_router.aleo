import shield_swap.aleo;
import shield_swap_freezelist.aleo;
import shield_swap_multisig_core.aleo;
import shield_swap_pricing_terms.aleo;

program shield_swap_router.aleo;

struct U256__8JquwLopp8:
    hi as u128;
    lo as u128;

struct MerkleProof:
    siblings as [field; 16u32];
    leaf_index as u32;

struct PricingTermsSwapPlan:
    blinded_address as address;
    pool as field;
    zero_for_one as boolean;
    amount_in as u128;
    amount_out_min as u128;
    sqrt_price_limit as U256__8JquwLopp8;
    nonce as u64;
    deadline as u32;
    token0_id as field;
    token1_id as field;

struct PricingTermsSwapMultiHopRequest:
    token_in as field;
    token_out as field;
    amount_in as u128;
    amount_out_min as u128;
    recipient as address;
    hop0 as shield_swap.aleo/SwapHop;
    hop1 as shield_swap.aleo/SwapHop;
    hop2 as shield_swap.aleo/SwapHop;
    hop_count as u8;
    nonce as u64;
    deadline as u32;
    caller as address;

struct ChecksumEdition:
    checksum as [u8; 32u32];
    edition as u16;

struct OracleObservation__DI5XPierhvb:
    sequence as u64;
    timestamp as i64;
    tick_cumulative as i128;
    seconds_per_liquidity_x128 as U256__8JquwLopp8;
    zero_liquidity_seconds as u64;

struct OracleMeta__CK408KBR6QP:
    epoch as u32;
    activated_at as i64;
    newest_sequence as u64;
    count as u32;
    last_trade_at as i64;
    has_trade as boolean;

struct OracleStatusKey__F4oNSDUwTWX:
    scope as u8;
    first as field;
    second as field;

struct OracleStatus__IK9niU7Fbiq:
    initialized as boolean;
    epoch as u32;
    activated_at as i64;
    oldest_at as i64;
    newest_sequence as u64;
    count as u32;
    last_trade_at as i64;
    has_trade as boolean;
    liquidity as u128;
    tick as i32;
    paused as boolean;
    last_status_change as i64;
    evaluated_at as i64;
    evaluated_height as u32;

struct OracleQuote__4F96AB9pBjw:
    mean_tick as i32;
    harmonic_liquidity as u128;
    zero_liquidity_seconds as u64;
    start_at as i64;
    end_at as i64;
    epoch as u32;

struct OraclePolicy__CYQtp3qo1iD:
    min_window_seconds as u32;
    min_harmonic_liquidity as u128;
    min_current_liquidity as u128;
    max_inactive_seconds as u32;
    expected_epoch as u32;

struct TradingTotals__72deiBHZGC8:
    volume0 as u128;
    volume1 as u128;
    lp_fees0 as u128;
    lp_fees1 as u128;
    protocol_fees0 as u128;
    protocol_fees1 as u128;
    swaps as u64;

struct OracleMoment__6B7WMwQayvG:
    sequence as u64;
    timestamp as i64;
    tick_squared_cumulative as u128;

struct AnalyticsState__52h0FdOSd8B:
    activated_at as i64;
    moment as OracleMoment__6B7WMwQayvG;
    archive_sequence as u64;
    archive_count as u32;
    archive_at as i64;

struct PoolOracleState__AoIWZIRjR2g:
    meta as OracleMeta__CK408KBR6QP;
    analytics as AnalyticsState__52h0FdOSd8B;
    totals as TradingTotals__72deiBHZGC8;

struct OracleSample__HLGFui2oFN8:
    observation as OracleObservation__DI5XPierhvb;
    tick_squared_cumulative as u128;
    totals as TradingTotals__72deiBHZGC8;

struct ArchiveEntry__9mZNFT38bto:
    sequence as u64;
    sample as OracleSample__HLGFui2oFN8;

struct AnalyticsQuote__HK9a1gQMk7C:
    price as OracleQuote__4F96AB9pBjw;
    tick_variance as u128;

struct OracleRiskPolicy__pqwiCtUKG:
    base as OraclePolicy__CYQtp3qo1iD;
    min_end_delay_seconds as u32;
    max_spot_tick_deviation as u32;
    max_mean_tick_deviation as u32;
    max_tick_variance as u128;
    max_reference_tick_deviation as u32;
    max_reference_age_seconds as u32;

struct OracleReference__GxiJ7GncXMo:
    tick as i32;
    observed_at as i64;

struct RangeCumulatives__Bf0FtLgM0Jp:
    tick_cumulative as i128;
    seconds_per_liquidity_x128 as U256__8JquwLopp8;
    seconds as u64;

struct RangeTick__IAWAkuUXE1E:
    generation as u64;
    outside as RangeCumulatives__Bf0FtLgM0Jp;

struct RangeSnapshot__LAXReBa6yS0:
    pool as field;
    lower as i32;
    upper as i32;
    activated_at as i64;
    timestamp as i64;
    lower_generation as u64;
    upper_generation as u64;
    inside as RangeCumulatives__Bf0FtLgM0Jp;

struct PositionActivity__BIF293U7SwN:
    snapshot as RangeSnapshot__LAXReBa6yS0;
    started_at as i64;
    liquidity as u128;
    active_seconds as u64;
    liquidity_seconds as U256__8JquwLopp8;

struct AnalyticsKey__16dh9ueWeab:
    pool as field;
    tier as u8;
    index as u32;

function swap_from_wrapped:
    input r0 as dynamic.record;
    input r1 as [MerkleProof; 2u32].private;
    input r2 as field.private;
    input r3 as address.public;
    input r4 as field.public;
    input r5 as boolean.public;
    input r6 as u128.public;
    input r7 as u128.public;
    input r8 as U256__8JquwLopp8.public;
    input r9 as u64.public;
    input r10 as u32.public;
    input r11 as field.public;
    input r12 as field.public;
    gt r7 0u128 into r13;
    assert.eq r13 true;
    ternary r5 r11 r12 into r14;
    call.dynamic r14 'aleo' 'deposit_private' with r0 r6 r1 (as dynamic.record u128.public [MerkleProof; 2u32].private) into r15 r16 r17 (as dynamic.record dynamic.record dynamic.future);
    call shield_swap.aleo/swap r16 r2 r3 r4 r5 r6 r7 r8 r9 r10 r11 r12 into r18 r19 r20 r21;
    call.dynamic r14 'aleo' 'burn_empty_record' with r19 (as dynamic.record);
    async swap_from_wrapped r14 r17 r21 into r22;
    output r15 as dynamic.record;
    output r18 as field.public;
    output r20 as shield_swap.aleo/SwapComplianceRecord.record;
    output r22 as shield_swap_router.aleo/swap_from_wrapped.future;

finalize swap_from_wrapped:
    input r0 as field.public;
    input r1 as dynamic.future;
    input r2 as shield_swap.aleo/swap.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r3;
    assert.eq r3 true;
    await r1;
    await r2;

function swap_mh_from_wrapped:
    input r0 as dynamic.record;
    input r1 as [MerkleProof; 2u32].private;
    input r2 as field.private;
    input r3 as address.public;
    input r4 as field.public;
    input r5 as field.public;
    input r6 as u128.public;
    input r7 as u128.public;
    input r8 as shield_swap.aleo/SwapHop.public;
    input r9 as shield_swap.aleo/SwapHop.public;
    input r10 as shield_swap.aleo/SwapHop.public;
    input r11 as u8.public;
    input r12 as u64.public;
    input r13 as u32.public;
    gt r7 0u128 into r14;
    assert.eq r14 true;
    call.dynamic r4 'aleo' 'deposit_private' with r0 r6 r1 (as dynamic.record u128.public [MerkleProof; 2u32].private) into r15 r16 r17 (as dynamic.record dynamic.record dynamic.future);
    call shield_swap.aleo/swap_multi_hop r2 r3 r16 r4 r5 r6 r7 r8 r9 r10 r11 r12 r13 into r18 r19 r20 r21;
    call.dynamic r4 'aleo' 'burn_empty_record' with r19 (as dynamic.record);
    async swap_mh_from_wrapped r4 r17 r21 into r22;
    output r15 as dynamic.record;
    output r18 as field.public;
    output r20 as shield_swap.aleo/MultiHopSwapComplianceRecord.record;
    output r22 as shield_swap_router.aleo/swap_mh_from_wrapped.future;

finalize swap_mh_from_wrapped:
    input r0 as field.public;
    input r1 as dynamic.future;
    input r2 as shield_swap.aleo/swap_multi_hop.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r3;
    assert.eq r3 true;
    await r1;
    await r2;

function claim_to_arc20_no_refund:
    input r0 as field.private;
    input r1 as address.public;
    input r2 as field.public;
    input r3 as field.public;
    input r4 as field.public;
    input r5 as u128.public;
    input r6 as [shield_swap.aleo/MerkleProof; 2u32].private;
    call shield_swap.aleo/claim_swap_output_no_refund r0 r1 r2 r3 r4 r5 r6 into r7 r8;
    async claim_to_arc20_no_refund r3 r4 r8 into r9;
    output r7 as dynamic.record;
    output r9 as shield_swap_router.aleo/claim_to_arc20_no_refund.future;

finalize claim_to_arc20_no_refund:
    input r0 as field.public;
    input r1 as field.public;
    input r2 as shield_swap.aleo/claim_swap_output_no_refund.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r3;
    assert.eq r3 true;
    contains shield_swap.aleo/from_wrapper_token_id[r1] into r4;
    not r4 into r5;
    assert.eq r5 true;
    await r2;

function claim_to_wrapped_no_refund:
    input r0 as field.private;
    input r1 as address.public;
    input r2 as field.public;
    input r3 as field.public;
    input r4 as field.public;
    input r5 as u128.public;
    input r6 as [shield_swap.aleo/MerkleProof; 2u32].private;
    input r7 as [MerkleProof; 2u32].private;
    call shield_swap.aleo/claim_swap_output_no_refund r0 r1 r2 r3 r4 r5 r6 into r8 r9;
    call.dynamic r4 'aleo' 'withdraw_private' with r8 r5 self.signer r7 (as dynamic.record u128.public address.private [MerkleProof; 2u32].private) into r10 r11 (as dynamic.record dynamic.future);
    async claim_to_wrapped_no_refund r4 r9 r11 into r12;
    output r10 as dynamic.record;
    output r12 as shield_swap_router.aleo/claim_to_wrapped_no_refund.future;

finalize claim_to_wrapped_no_refund:
    input r0 as field.public;
    input r1 as shield_swap.aleo/claim_swap_output_no_refund.future;
    input r2 as dynamic.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r3;
    assert.eq r3 true;
    await r1;
    await r2;

function claim_to_wrapped_refund_arc20:
    input r0 as field.private;
    input r1 as address.public;
    input r2 as field.public;
    input r3 as field.public;
    input r4 as field.public;
    input r5 as u128.public;
    input r6 as u128.public;
    input r7 as [shield_swap.aleo/MerkleProof; 2u32].private;
    input r8 as [MerkleProof; 2u32].private;
    call shield_swap.aleo/claim_swap_output r0 r1 r2 r3 r4 r5 r6 r7 into r9 r10 r11;
    call.dynamic r4 'aleo' 'withdraw_private' with r9 r5 self.signer r8 (as dynamic.record u128.public address.private [MerkleProof; 2u32].private) into r12 r13 (as dynamic.record dynamic.future);
    async claim_to_wrapped_refund_arc20 r3 r4 r11 r13 into r14;
    output r12 as dynamic.record;
    output r10 as dynamic.record;
    output r14 as shield_swap_router.aleo/claim_to_wrapped_refund_arc20.future;

finalize claim_to_wrapped_refund_arc20:
    input r0 as field.public;
    input r1 as field.public;
    input r2 as shield_swap.aleo/claim_swap_output.future;
    input r3 as dynamic.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r4;
    not r4 into r5;
    assert.eq r5 true;
    contains shield_swap.aleo/from_wrapper_token_id[r1] into r6;
    assert.eq r6 true;
    await r2;
    await r3;

function claim_to_arc20_refund_wrapped:
    input r0 as field.private;
    input r1 as address.public;
    input r2 as field.public;
    input r3 as field.public;
    input r4 as field.public;
    input r5 as u128.public;
    input r6 as u128.public;
    input r7 as [shield_swap.aleo/MerkleProof; 2u32].private;
    input r8 as [MerkleProof; 2u32].private;
    call shield_swap.aleo/claim_swap_output r0 r1 r2 r3 r4 r5 r6 r7 into r9 r10 r11;
    call.dynamic r3 'aleo' 'withdraw_private' with r10 r6 self.signer r8 (as dynamic.record u128.public address.private [MerkleProof; 2u32].private) into r12 r13 (as dynamic.record dynamic.future);
    async claim_to_arc20_refund_wrapped r3 r4 r11 r13 into r14;
    output r9 as dynamic.record;
    output r12 as dynamic.record;
    output r14 as shield_swap_router.aleo/claim_to_arc20_refund_wrapped.future;

finalize claim_to_arc20_refund_wrapped:
    input r0 as field.public;
    input r1 as field.public;
    input r2 as shield_swap.aleo/claim_swap_output.future;
    input r3 as dynamic.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r4;
    assert.eq r4 true;
    contains shield_swap.aleo/from_wrapper_token_id[r1] into r5;
    not r5 into r6;
    assert.eq r6 true;
    await r2;
    await r3;

function claim_to_wrapped_refund_wrapped:
    input r0 as field.private;
    input r1 as address.public;
    input r2 as field.public;
    input r3 as field.public;
    input r4 as field.public;
    input r5 as u128.public;
    input r6 as u128.public;
    input r7 as [shield_swap.aleo/MerkleProof; 2u32].private;
    input r8 as [MerkleProof; 2u32].private;
    input r9 as [MerkleProof; 2u32].private;
    call shield_swap.aleo/claim_swap_output r0 r1 r2 r3 r4 r5 r6 r7 into r10 r11 r12;
    call.dynamic r4 'aleo' 'withdraw_private' with r10 r5 self.signer r8 (as dynamic.record u128.public address.private [MerkleProof; 2u32].private) into r13 r14 (as dynamic.record dynamic.future);
    call.dynamic r3 'aleo' 'withdraw_private' with r11 r6 self.signer r9 (as dynamic.record u128.public address.private [MerkleProof; 2u32].private) into r15 r16 (as dynamic.record dynamic.future);
    async claim_to_wrapped_refund_wrapped r3 r4 r12 r14 r16 into r17;
    output r13 as dynamic.record;
    output r15 as dynamic.record;
    output r17 as shield_swap_router.aleo/claim_to_wrapped_refund_wrapped.future;

finalize claim_to_wrapped_refund_wrapped:
    input r0 as field.public;
    input r1 as field.public;
    input r2 as shield_swap.aleo/claim_swap_output.future;
    input r3 as dynamic.future;
    input r4 as dynamic.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r5;
    assert.eq r5 true;
    contains shield_swap.aleo/from_wrapper_token_id[r1] into r6;
    assert.eq r6 true;
    await r2;
    await r3;
    await r4;

function swap_wrapped_with_pricing_terms:
    input r0 as dynamic.record;
    input r1 as [MerkleProof; 2u32].private;
    input r2 as field.private;
    input r3 as PricingTermsSwapPlan.public;
    input r4 as shield_swap_pricing_terms.aleo/PricingTerms.public;
    input r5 as signature.private;
    cast r3.pool r3.zero_for_one r3.amount_in r3.sqrt_price_limit r3.blinded_address r3.nonce r3.blinded_address into r6 as shield_swap_pricing_terms.aleo/SwapKey;
    hash.bhp256 r6 into r7 as field;
    call shield_swap_pricing_terms.aleo/authorize_swap shield_swap.aleo r6 r4 r2 r5 into r8;
    gt r3.amount_out_min 0u128 into r9;
    assert.eq r9 true;
    ternary r3.zero_for_one r3.token0_id r3.token1_id into r10;
    call.dynamic r10 'aleo' 'deposit_private' with r0 r3.amount_in r1 (as dynamic.record u128.public [MerkleProof; 2u32].private) into r11 r12 r13 (as dynamic.record dynamic.record dynamic.future);
    call shield_swap.aleo/swap r12 r2 r3.blinded_address r3.pool r3.zero_for_one r3.amount_in r3.amount_out_min r3.sqrt_price_limit r3.nonce r3.deadline r3.token0_id r3.token1_id into r14 r15 r16 r17;
    call.dynamic r10 'aleo' 'burn_empty_record' with r15 (as dynamic.record);
    assert.eq r14 r7;
    async swap_wrapped_with_pricing_terms r10 r8 r13 r17 into r18;
    output r11 as dynamic.record;
    output r14 as field.public;
    output r16 as shield_swap.aleo/SwapComplianceRecord.record;
    output r18 as shield_swap_router.aleo/swap_wrapped_with_pricing_terms.future;

finalize swap_wrapped_with_pricing_terms:
    input r0 as field.public;
    input r1 as shield_swap_pricing_terms.aleo/authorize_swap.future;
    input r2 as dynamic.future;
    input r3 as shield_swap.aleo/swap.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r4;
    assert.eq r4 true;
    await r1;
    await r2;
    await r3;

closure as_pricing_terms_request:
    input r0 as PricingTermsSwapMultiHopRequest;
    cast r0.hop0.pool r0.hop0.zero_for_one r0.hop0.sqrt_price_limit into r1 as shield_swap_pricing_terms.aleo/SwapHop;
    cast r0.hop1.pool r0.hop1.zero_for_one r0.hop1.sqrt_price_limit into r2 as shield_swap_pricing_terms.aleo/SwapHop;
    cast r0.hop2.pool r0.hop2.zero_for_one r0.hop2.sqrt_price_limit into r3 as shield_swap_pricing_terms.aleo/SwapHop;
    cast r0.token_in r0.token_out r0.amount_in r0.amount_out_min r0.recipient r1 r2 r3 r0.hop_count r0.nonce r0.deadline r0.caller into r4 as shield_swap_pricing_terms.aleo/SwapMultiHopRequest;
    output r4 as shield_swap_pricing_terms.aleo/SwapMultiHopRequest;

function swap_mh_wrapped_pricing_terms:
    input r0 as dynamic.record;
    input r1 as [MerkleProof; 2u32].private;
    input r2 as field.private;
    input r3 as PricingTermsSwapMultiHopRequest.public;
    input r4 as shield_swap_pricing_terms.aleo/PricingTerms.public;
    input r5 as signature.private;
    assert.eq r3.caller r3.recipient;
    hash.bhp256 r3 into r6 as field;
    call as_pricing_terms_request r3 into r7;
    call shield_swap_pricing_terms.aleo/authorize_multi_hop shield_swap.aleo r7 r4 r2 r5 into r8;
    gt r3.amount_out_min 0u128 into r9;
    assert.eq r9 true;
    call.dynamic r3.token_in 'aleo' 'deposit_private' with r0 r3.amount_in r1 (as dynamic.record u128.public [MerkleProof; 2u32].private) into r10 r11 r12 (as dynamic.record dynamic.record dynamic.future);
    call shield_swap.aleo/swap_multi_hop r2 r3.recipient r11 r3.token_in r3.token_out r3.amount_in r3.amount_out_min r3.hop0 r3.hop1 r3.hop2 r3.hop_count r3.nonce r3.deadline into r13 r14 r15 r16;
    call.dynamic r3.token_in 'aleo' 'burn_empty_record' with r14 (as dynamic.record);
    assert.eq r13 r6;
    async swap_mh_wrapped_pricing_terms r3.token_in r8 r12 r16 into r17;
    output r10 as dynamic.record;
    output r13 as field.public;
    output r15 as shield_swap.aleo/MultiHopSwapComplianceRecord.record;
    output r17 as shield_swap_router.aleo/swap_mh_wrapped_pricing_terms.future;

finalize swap_mh_wrapped_pricing_terms:
    input r0 as field.public;
    input r1 as shield_swap_pricing_terms.aleo/authorize_multi_hop.future;
    input r2 as dynamic.future;
    input r3 as shield_swap.aleo/swap_multi_hop.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r4;
    assert.eq r4 true;
    await r1;
    await r2;
    await r3;

function swap_with_pricing_terms:
    input r0 as dynamic.record;
    input r1 as field.private;
    input r2 as PricingTermsSwapPlan.public;
    input r3 as shield_swap_pricing_terms.aleo/PricingTerms.public;
    input r4 as signature.private;
    gt r2.amount_out_min 0u128 into r5;
    assert.eq r5 true;
    ternary r2.zero_for_one r2.token0_id r2.token1_id into r6;
    cast r2.pool r2.zero_for_one r2.amount_in r2.sqrt_price_limit r2.blinded_address r2.nonce r2.blinded_address into r7 as shield_swap_pricing_terms.aleo/SwapKey;
    hash.bhp256 r7 into r8 as field;
    call shield_swap_pricing_terms.aleo/authorize_swap shield_swap.aleo r7 r3 r1 r4 into r9;
    call shield_swap.aleo/swap r0 r1 r2.blinded_address r2.pool r2.zero_for_one r2.amount_in r2.amount_out_min r2.sqrt_price_limit r2.nonce r2.deadline r2.token0_id r2.token1_id into r10 r11 r12 r13;
    assert.eq r10 r8;
    async swap_with_pricing_terms r6 r9 r13 into r14;
    output r11 as dynamic.record;
    output r10 as field.public;
    output r12 as shield_swap.aleo/SwapComplianceRecord.record;
    output r14 as shield_swap_router.aleo/swap_with_pricing_terms.future;

finalize swap_with_pricing_terms:
    input r0 as field.public;
    input r1 as shield_swap_pricing_terms.aleo/authorize_swap.future;
    input r2 as shield_swap.aleo/swap.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r3;
    not r3 into r4;
    assert.eq r4 true;
    await r1;
    await r2;

function swap_multi_hop_pricing_terms:
    input r0 as dynamic.record;
    input r1 as field.private;
    input r2 as PricingTermsSwapMultiHopRequest.public;
    input r3 as shield_swap_pricing_terms.aleo/PricingTerms.public;
    input r4 as signature.private;
    gt r2.amount_out_min 0u128 into r5;
    assert.eq r5 true;
    assert.eq r2.caller r2.recipient;
    hash.bhp256 r2 into r6 as field;
    call as_pricing_terms_request r2 into r7;
    call shield_swap_pricing_terms.aleo/authorize_multi_hop shield_swap.aleo r7 r3 r1 r4 into r8;
    call shield_swap.aleo/swap_multi_hop r1 r2.recipient r0 r2.token_in r2.token_out r2.amount_in r2.amount_out_min r2.hop0 r2.hop1 r2.hop2 r2.hop_count r2.nonce r2.deadline into r9 r10 r11 r12;
    assert.eq r9 r6;
    async swap_multi_hop_pricing_terms r2.token_in r8 r12 into r13;
    output r10 as dynamic.record;
    output r9 as field.public;
    output r11 as shield_swap.aleo/MultiHopSwapComplianceRecord.record;
    output r13 as shield_swap_router.aleo/swap_multi_hop_pricing_terms.future;

finalize swap_multi_hop_pricing_terms:
    input r0 as field.public;
    input r1 as shield_swap_pricing_terms.aleo/authorize_multi_hop.future;
    input r2 as shield_swap.aleo/swap_multi_hop.future;
    contains shield_swap.aleo/from_wrapper_token_id[r0] into r3;
    not r3 into r4;
    assert.eq r4 true;
    await r1;
    await r2;

constructor:
    gt edition 0u16 into r0;
    branch.eq r0 false to end_then_0_0;
    cast checksum edition into r1 as ChecksumEdition;
    hash.bhp256 r1 into r2 as field;
    cast shield_swap_router.aleo r2 into r3 as shield_swap_multisig_core.aleo/WalletSigningOpId;
    hash.bhp256 r3 into r4 as field;
    contains shield_swap_multisig_core.aleo/completed_signing_ops[r4] into r5;
    assert.eq r5 true;
    branch.eq true true to end_otherwise_0_1;
    position end_then_0_0;
    position end_otherwise_0_1;

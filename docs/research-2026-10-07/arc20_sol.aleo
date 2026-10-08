import arc20_multisig_core.aleo;

program arc20_sol.aleo;

record Token:
    owner as address.private;
    amount as u128.private;

struct ChecksumEdition:
    checksum as [u8; 32u32];
    edition as u16;

struct TokenAllowance:
    account as address;
    spender as address;

struct Optional__6A9ZdhLQa8N:
    is_some as boolean;
    val as u128;

struct Optional__ATAkdHctJwx:
    is_some as boolean;
    val as boolean;

mapping address_to_role:
    key as address.public;
    value as u16.public;

mapping allowances:
    key as field.public;
    value as u128.public;

mapping balances:
    key as address.public;
    value as u128.public;

mapping pause__:
    key as boolean.public;
    value as boolean.public;

mapping token_supply__:
    key as boolean.public;
    value as u128.public;

function approve_public:
    input r0 as address.public;
    input r1 as u128.public;
    cast self.caller r0 into r2 as TokenAllowance;
    hash.bhp256 r2 into r3 as field;
    async approve_public r3 r1 into r4;
    output r4 as arc20_sol.aleo/approve_public.future;

finalize approve_public:
    input r0 as field.public;
    input r1 as u128.public;
    get.or_use allowances[r0] 0u128 into r2;
    add r2 r1 into r3;
    set r3 into allowances[r0];

function unapprove_public:
    input r0 as address.public;
    input r1 as u128.public;
    cast self.caller r0 into r2 as TokenAllowance;
    hash.bhp256 r2 into r3 as field;
    async unapprove_public r3 r1 into r4;
    output r4 as arc20_sol.aleo/unapprove_public.future;

finalize unapprove_public:
    input r0 as field.public;
    input r1 as u128.public;
    get.or_use allowances[r0] 0u128 into r2;
    gte r2 r1 into r3;
    assert.eq r3 true;
    sub r2 r1 into r4;
    set r4 into allowances[r0];

function transfer_public:
    input r0 as address.public;
    input r1 as u128.public;
    async transfer_public self.caller r1 r0 into r2;
    output r2 as arc20_sol.aleo/transfer_public.future;

finalize transfer_public:
    input r0 as address.public;
    input r1 as u128.public;
    input r2 as address.public;
    get.or_use balances[r0] 0u128 into r3;
    gte r3 r1 into r4;
    assert.eq r4 true;
    sub r3 r1 into r5;
    set r5 into balances[r0];
    get.or_use balances[r2] 0u128 into r6;
    add r6 r1 into r7;
    set r7 into balances[r2];

function transfer_public_as_signer:
    input r0 as address.public;
    input r1 as u128.public;
    async transfer_public_as_signer self.signer r1 r0 into r2;
    output r2 as arc20_sol.aleo/transfer_public_as_signer.future;

finalize transfer_public_as_signer:
    input r0 as address.public;
    input r1 as u128.public;
    input r2 as address.public;
    get.or_use balances[r0] 0u128 into r3;
    gte r3 r1 into r4;
    assert.eq r4 true;
    sub r3 r1 into r5;
    set r5 into balances[r0];
    get.or_use balances[r2] 0u128 into r6;
    add r6 r1 into r7;
    set r7 into balances[r2];

function transfer_private:
    input r0 as Token.record;
    input r1 as address.private;
    input r2 as u128.private;
    sub r0.amount r2 into r3;
    cast r0.owner r3 into r4 as Token.record;
    cast r1 r2 into r5 as Token.record;
    output r4 as Token.record;
    output r5 as Token.record;

function transfer_private_to_public:
    input r0 as Token.record;
    input r1 as address.public;
    input r2 as u128.public;
    sub r0.amount r2 into r3;
    cast r0.owner r3 into r4 as Token.record;
    async transfer_private_to_public r1 r2 into r5;
    output r4 as Token.record;
    output r5 as arc20_sol.aleo/transfer_private_to_public.future;

finalize transfer_private_to_public:
    input r0 as address.public;
    input r1 as u128.public;
    get.or_use balances[r0] 0u128 into r2;
    add r2 r1 into r3;
    set r3 into balances[r0];

function transfer_public_to_private:
    input r0 as address.private;
    input r1 as u128.public;
    cast r0 r1 into r2 as Token.record;
    async transfer_public_to_private self.caller r1 into r3;
    output r2 as Token.record;
    output r3 as arc20_sol.aleo/transfer_public_to_private.future;

finalize transfer_public_to_private:
    input r0 as address.public;
    input r1 as u128.public;
    get.or_use balances[r0] 0u128 into r2;
    gte r2 r1 into r3;
    assert.eq r3 true;
    sub r2 r1 into r4;
    set r4 into balances[r0];

function transfer_from_public:
    input r0 as address.public;
    input r1 as address.public;
    input r2 as u128.public;
    cast r0 self.caller into r3 as TokenAllowance;
    hash.bhp256 r3 into r4 as field;
    async transfer_from_public r4 r2 r0 r1 into r5;
    output r5 as arc20_sol.aleo/transfer_from_public.future;

finalize transfer_from_public:
    input r0 as field.public;
    input r1 as u128.public;
    input r2 as address.public;
    input r3 as address.public;
    get.or_use allowances[r0] 0u128 into r4;
    gte r4 r1 into r5;
    assert.eq r5 true;
    sub r4 r1 into r6;
    set r6 into allowances[r0];
    get.or_use balances[r2] 0u128 into r7;
    gte r7 r1 into r8;
    assert.eq r8 true;
    sub r7 r1 into r9;
    set r9 into balances[r2];
    get.or_use balances[r3] 0u128 into r10;
    add r10 r1 into r11;
    set r11 into balances[r3];

function transfer_from_public_to_private:
    input r0 as address.public;
    input r1 as address.private;
    input r2 as u128.public;
    cast r0 self.caller into r3 as TokenAllowance;
    hash.bhp256 r3 into r4 as field;
    cast r1 r2 into r5 as Token.record;
    async transfer_from_public_to_private r4 r2 r0 into r6;
    output r5 as Token.record;
    output r6 as arc20_sol.aleo/transfer_from_public_to_private.future;

finalize transfer_from_public_to_private:
    input r0 as field.public;
    input r1 as u128.public;
    input r2 as address.public;
    get.or_use allowances[r0] 0u128 into r3;
    gte r3 r1 into r4;
    assert.eq r4 true;
    sub r3 r1 into r5;
    set r5 into allowances[r0];
    get.or_use balances[r2] 0u128 into r6;
    gte r6 r1 into r7;
    assert.eq r7 true;
    sub r6 r1 into r8;
    set r8 into balances[r2];

function shield:
    input r0 as u128.public;
    cast self.caller r0 into r1 as Token.record;
    async shield self.caller r0 into r2;
    output r1 as Token.record;
    output r2 as arc20_sol.aleo/shield.future;

finalize shield:
    input r0 as address.public;
    input r1 as u128.public;
    get.or_use balances[r0] 0u128 into r2;
    gte r2 r1 into r3;
    assert.eq r3 true;
    sub r2 r1 into r4;
    set r4 into balances[r0];

function unshield:
    input r0 as Token.record;
    input r1 as u128.private;
    sub r0.amount r1 into r2;
    cast r0.owner r2 into r3 as Token.record;
    async unshield r0.owner r1 into r4;
    output r3 as Token.record;
    output r4 as arc20_sol.aleo/unshield.future;

finalize unshield:
    input r0 as address.public;
    input r1 as u128.public;
    get.or_use balances[r0] 0u128 into r2;
    add r2 r1 into r3;
    set r3 into balances[r0];

function join:
    input r0 as Token.record;
    input r1 as Token.record;
    is.eq r0.owner r1.owner into r2;
    assert.eq r2 true;
    add r0.amount r1.amount into r3;
    cast r0.owner r3 into r4 as Token.record;
    output r4 as Token.record;

function split:
    input r0 as Token.record;
    input r1 as u128.private;
    cast r0.owner r1 into r2 as Token.record;
    sub r0.amount r1 into r3;
    cast r0.owner r3 into r4 as Token.record;
    output r2 as Token.record;
    output r4 as Token.record;

function mint_public:
    input r0 as address.public;
    input r1 as u128.public;
    async mint_public self.caller r0 r1 into r2;
    output r2 as arc20_sol.aleo/mint_public.future;

finalize mint_public:
    input r0 as address.public;
    input r1 as address.public;
    input r2 as u128.public;
    get address_to_role[r0] into r3;
    and r3 1u16 into r4;
    is.eq r4 1u16 into r5;
    assert.eq r5 true;
    contains pause__[false] into r6;
    get.or_use pause__[false] false into r7;
    ternary r6 r7 false into r8;
    cast r6 r8 into r9 as Optional__ATAkdHctJwx;
    ternary r9.is_some r9.val false into r10;
    assert.eq r10 false;
    get.or_use balances[r1] 0u128 into r11;
    add r2 r11 into r12;
    set r12 into balances[r1];
    contains token_supply__[false] into r13;
    get.or_use token_supply__[false] 0u128 into r14;
    ternary r13 r14 0u128 into r15;
    cast r13 r15 into r16 as Optional__6A9ZdhLQa8N;
    ternary r16.is_some r16.val 0u128 into r17;
    add r17 r2 into r18;
    lte r18 340282366920938463463374607431768211455u128 into r19;
    assert.eq r19 true;
    set r18 into token_supply__[false];

function mint_private:
    input r0 as address.private;
    input r1 as u128.private;
    cast r0 r1 into r2 as Token.record;
    async mint_private self.caller r1 into r3;
    output r2 as Token.record;
    output r3 as arc20_sol.aleo/mint_private.future;

finalize mint_private:
    input r0 as address.public;
    input r1 as u128.public;
    get address_to_role[r0] into r2;
    and r2 1u16 into r3;
    is.eq r3 1u16 into r4;
    assert.eq r4 true;
    contains pause__[false] into r5;
    get.or_use pause__[false] false into r6;
    ternary r5 r6 false into r7;
    cast r5 r7 into r8 as Optional__ATAkdHctJwx;
    ternary r8.is_some r8.val false into r9;
    assert.eq r9 false;
    contains token_supply__[false] into r10;
    get.or_use token_supply__[false] 0u128 into r11;
    ternary r10 r11 0u128 into r12;
    cast r10 r12 into r13 as Optional__6A9ZdhLQa8N;
    ternary r13.is_some r13.val 0u128 into r14;
    add r14 r1 into r15;
    lte r15 340282366920938463463374607431768211455u128 into r16;
    assert.eq r16 true;
    set r15 into token_supply__[false];

function burn_public:
    input r0 as address.public;
    input r1 as u128.public;
    async burn_public self.caller r0 r1 into r2;
    output r2 as arc20_sol.aleo/burn_public.future;

finalize burn_public:
    input r0 as address.public;
    input r1 as address.public;
    input r2 as u128.public;
    get address_to_role[r0] into r3;
    and r3 2u16 into r4;
    is.eq r4 2u16 into r5;
    assert.eq r5 true;
    contains pause__[false] into r6;
    get.or_use pause__[false] false into r7;
    ternary r6 r7 false into r8;
    cast r6 r8 into r9 as Optional__ATAkdHctJwx;
    ternary r9.is_some r9.val false into r10;
    assert.eq r10 false;
    get.or_use balances[r1] 0u128 into r11;
    gte r11 r2 into r12;
    assert.eq r12 true;
    sub r11 r2 into r13;
    set r13 into balances[r1];
    contains token_supply__[false] into r14;
    get.or_use token_supply__[false] 0u128 into r15;
    ternary r14 r15 0u128 into r16;
    cast r14 r16 into r17 as Optional__6A9ZdhLQa8N;
    ternary r17.is_some r17.val 0u128 into r18;
    gte r18 r2 into r19;
    assert.eq r19 true;
    sub r18 r2 into r20;
    set r20 into token_supply__[false];

function burn_private:
    input r0 as Token.record;
    input r1 as u128.private;
    sub r0.amount r1 into r2;
    cast r0.owner r2 into r3 as Token.record;
    async burn_private self.caller r1 into r4;
    output r3 as Token.record;
    output r4 as arc20_sol.aleo/burn_private.future;

finalize burn_private:
    input r0 as address.public;
    input r1 as u128.public;
    get address_to_role[r0] into r2;
    and r2 2u16 into r3;
    is.eq r3 2u16 into r4;
    assert.eq r4 true;
    contains pause__[false] into r5;
    get.or_use pause__[false] false into r6;
    ternary r5 r6 false into r7;
    cast r5 r7 into r8 as Optional__ATAkdHctJwx;
    ternary r8.is_some r8.val false into r9;
    assert.eq r9 false;
    contains token_supply__[false] into r10;
    get.or_use token_supply__[false] 0u128 into r11;
    ternary r10 r11 0u128 into r12;
    cast r10 r12 into r13 as Optional__6A9ZdhLQa8N;
    ternary r13.is_some r13.val 0u128 into r14;
    gte r14 r1 into r15;
    assert.eq r15 true;
    sub r14 r1 into r16;
    set r16 into token_supply__[false];

function update_role:
    input r0 as address.public;
    input r1 as u16.private;
    async update_role self.caller r0 r1 into r2;
    output r2 as arc20_sol.aleo/update_role.future;

finalize update_role:
    input r0 as address.public;
    input r1 as address.public;
    input r2 as u16.public;
    get address_to_role[r0] into r3;
    and r3 8u16 into r4;
    is.eq r4 8u16 into r5;
    assert.eq r5 true;
    is.eq r0 r1 into r6;
    branch.eq r6 false to end_then_0_0;
    and r2 8u16 into r7;
    is.eq r7 8u16 into r8;
    assert.eq r8 true;
    branch.eq true true to end_otherwise_0_1;
    position end_then_0_0;
    position end_otherwise_0_1;
    set r2 into address_to_role[r1];

function set_pause_status:
    input r0 as boolean.public;
    async set_pause_status self.caller r0 into r1;
    output r1 as arc20_sol.aleo/set_pause_status.future;

finalize set_pause_status:
    input r0 as address.public;
    input r1 as boolean.public;
    get address_to_role[r0] into r2;
    and r2 4u16 into r3;
    is.eq r3 4u16 into r4;
    assert.eq r4 true;
    set r1 into pause__[false];

view balance_of:
    input r0 as address.public;
    get.or_use balances[r0] 0u128 into r1;
    output r1 as u128.public;

view allowance:
    input r0 as address.public;
    input r1 as address.public;
    cast r0 r1 into r2 as TokenAllowance;
    hash.bhp256 r2 into r3 as field;
    get.or_use allowances[r3] 0u128 into r4;
    output r4 as u128.public;

view supply:
    contains token_supply__[false] into r0;
    get.or_use token_supply__[false] 0u128 into r1;
    ternary r0 r1 0u128 into r2;
    cast r0 r2 into r3 as Optional__6A9ZdhLQa8N;
    ternary r3.is_some r3.val 0u128 into r4;
    output r4 as u128.public;

view max_supply:
    output 340282366920938463463374607431768211455u128 as u128.public;

view decimals:
    output 9u8 as u8.public;

view name:
    output 'SOL' as identifier.public;

view symbol:
    output 'SOL' as identifier.public;

constructor:
    cast 61u8 159u8 3u8 215u8 96u8 144u8 14u8 107u8 28u8 185u8 132u8 93u8 240u8 41u8 185u8 98u8 59u8 228u8 145u8 252u8 47u8 61u8 169u8 89u8 220u8 145u8 35u8 43u8 185u8 212u8 203u8 112u8 into r0 as [u8; 32u32];
    assert.eq name/checksum r0;
    cast 173u8 218u8 35u8 221u8 212u8 91u8 120u8 219u8 132u8 140u8 19u8 254u8 254u8 25u8 236u8 112u8 198u8 78u8 201u8 44u8 232u8 48u8 135u8 17u8 169u8 213u8 42u8 36u8 15u8 231u8 104u8 244u8 into r1 as [u8; 32u32];
    assert.eq symbol/checksum r1;
    cast 16u8 182u8 204u8 42u8 138u8 98u8 10u8 66u8 245u8 211u8 153u8 203u8 96u8 208u8 143u8 236u8 80u8 88u8 65u8 126u8 163u8 246u8 221u8 93u8 156u8 97u8 74u8 221u8 204u8 71u8 215u8 236u8 into r2 as [u8; 32u32];
    assert.eq decimals/checksum r2;
    cast 205u8 178u8 247u8 132u8 253u8 223u8 249u8 127u8 47u8 226u8 176u8 159u8 28u8 113u8 162u8 63u8 192u8 245u8 28u8 142u8 229u8 97u8 243u8 122u8 9u8 163u8 70u8 84u8 253u8 150u8 63u8 127u8 into r3 as [u8; 32u32];
    assert.eq max_supply/checksum r3;
    is.eq edition 0u16 into r4;
    branch.eq r4 false to end_then_0_0;
    set 8u16 into address_to_role[aleo1kmcydn6me4fn20eq0pcdf8zhh58jpnela8ys3e77xr4x0fn00czqt3v8x2];
    set 4u16 into address_to_role[aleo126h6shw93wegf2fajnux390sfl8r89rym2wwrkge3al43z5mku8shkzk3t];
    set 0u128 into token_supply__[false];
    branch.eq true true to end_otherwise_0_1;
    position end_then_0_0;
    position end_otherwise_0_1;
    gt edition 0u16 into r5;
    branch.eq r5 false to end_then_0_2;
    cast checksum edition into r6 as ChecksumEdition;
    hash.bhp256 r6 into r7 as field;
    cast arc20_sol.aleo r7 into r8 as arc20_multisig_core.aleo/WalletSigningOpId;
    hash.bhp256 r8 into r9 as field;
    contains arc20_multisig_core.aleo/completed_signing_ops[r9] into r10;
    assert.eq r10 true;
    branch.eq true true to end_otherwise_0_3;
    position end_then_0_2;
    position end_otherwise_0_3;

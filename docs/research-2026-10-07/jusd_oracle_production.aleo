program jusd_oracle_production.aleo;

struct ChecksumEdition:
    checksum as [u8; 32u32];
    edition as u16;

mapping price:
    key as boolean.public;
    value as u128.public;

mapping updated_at:
    key as boolean.public;
    value as u32.public;

mapping updater:
    key as boolean.public;
    value as address.public;

mapping admin:
    key as boolean.public;
    value as address.public;

mapping pending_admin:
    key as boolean.public;
    value as address.public;

mapping max_step_ppm:
    key as boolean.public;
    value as u128.public;

mapping min_gap:
    key as boolean.public;
    value as u32.public;

mapping upgrade_approved:
    key as field.public;
    value as boolean.public;

mapping upgrader:
    key as boolean.public;
    value as address.public;

mapping upgrade_eta:
    key as field.public;
    value as u32.public;

mapping upgrade_delay:
    key as boolean.public;
    value as u32.public;

mapping upgrades_disabled:
    key as boolean.public;
    value as boolean.public;

function init:
    input r0 as address.public;
    input r1 as address.public;
    input r2 as u128.public;
    input r3 as u32.public;
    async init self.caller r0 r1 r2 r3 into r4;
    output r4 as jusd_oracle_production.aleo/init.future;

finalize init:
    input r0 as address.public;
    input r1 as address.public;
    input r2 as address.public;
    input r3 as u128.public;
    input r4 as u32.public;
    assert.eq r0 aleo15z3xv5a8r749wn0lmdysq7u4rnj4fd6n3ygv3autsrp4c9nj35gq7n9ljl;
    assert.eq r1 r0;
    contains admin[true] into r5;
    not r5 into r6;
    assert.eq r6 true;
    set r1 into admin[true];
    set r2 into updater[true];
    set r3 into max_step_ppm[true];
    set r4 into min_gap[true];

function set_price:
    input r0 as u128.public;
    async set_price self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/set_price.future;

finalize set_price:
    input r0 as address.public;
    input r1 as u128.public;
    get updater[true] into r2;
    assert.eq r0 r2;
    contains price[true] into r3;
    assert.eq r3 true;
    get price[true] into r4;
    gte r1 r4 into r5;
    assert.eq r5 true;
    sub r1 r4 into r6;
    mul r6 1000000u128 into r7;
    get max_step_ppm[true] into r8;
    mul r4 r8 into r9;
    lte r7 r9 into r10;
    assert.eq r10 true;
    get updated_at[true] into r11;
    sub block.height r11 into r12;
    get min_gap[true] into r13;
    gte r12 r13 into r14;
    assert.eq r14 true;
    set r1 into price[true];
    set block.height into updated_at[true];

function force_price:
    input r0 as u128.public;
    async force_price self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/force_price.future;

finalize force_price:
    input r0 as address.public;
    input r1 as u128.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    gt r1 0u128 into r3;
    assert.eq r3 true;
    contains price[true] into r4;
    branch.eq r4 false to end_then_0_0;
    get price[true] into r5;
    gte r1 r5 into r6;
    sub.w r1 r5 into r7;
    sub.w r5 r1 into r8;
    ternary r6 r7 r8 into r9;
    mul r9 1000000u128 into r10;
    mul r5 50000u128 into r11;
    lte r10 r11 into r12;
    assert.eq r12 true;
    branch.eq true true to end_otherwise_0_1;
    position end_then_0_0;
    gte r1 900000000000000000u128 into r13;
    assert.eq r13 true;
    lte r1 1200000000000000000u128 into r14;
    assert.eq r14 true;
    position end_otherwise_0_1;
    set r1 into price[true];
    set block.height into updated_at[true];

function set_updater:
    input r0 as address.public;
    async set_updater self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/set_updater.future;

finalize set_updater:
    input r0 as address.public;
    input r1 as address.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    set r1 into updater[true];

function propose_admin:
    input r0 as address.public;
    async propose_admin self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/propose_admin.future;

finalize propose_admin:
    input r0 as address.public;
    input r1 as address.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    set r1 into pending_admin[true];

function accept_admin:
    async accept_admin self.caller into r0;
    output r0 as jusd_oracle_production.aleo/accept_admin.future;

finalize accept_admin:
    input r0 as address.public;
    get pending_admin[true] into r1;
    assert.eq r0 r1;
    set r0 into admin[true];
    remove pending_admin[true];

function set_max_step:
    input r0 as u128.public;
    async set_max_step self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/set_max_step.future;

finalize set_max_step:
    input r0 as address.public;
    input r1 as u128.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    set r1 into max_step_ppm[true];

function set_min_gap:
    input r0 as u32.public;
    async set_min_gap self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/set_min_gap.future;

finalize set_min_gap:
    input r0 as address.public;
    input r1 as u32.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    set r1 into min_gap[true];

function approve_upgrade:
    input r0 as [u8; 32u32].public;
    input r1 as u16.public;
    cast r0 r1 into r2 as ChecksumEdition;
    hash.bhp256 r2 into r3 as field;
    async approve_upgrade self.caller r3 into r4;
    output r4 as jusd_oracle_production.aleo/approve_upgrade.future;

finalize approve_upgrade:
    input r0 as address.public;
    input r1 as field.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    set true into upgrade_approved[r1];
    get.or_use upgrade_delay[true] 0u32 into r3;
    add block.height r3 into r4;
    set r4 into upgrade_eta[r1];

function revoke_upgrade:
    input r0 as [u8; 32u32].public;
    input r1 as u16.public;
    cast r0 r1 into r2 as ChecksumEdition;
    hash.bhp256 r2 into r3 as field;
    async revoke_upgrade self.caller r3 into r4;
    output r4 as jusd_oracle_production.aleo/revoke_upgrade.future;

finalize revoke_upgrade:
    input r0 as address.public;
    input r1 as field.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    set false into upgrade_approved[r1];
    remove upgrade_eta[r1];

function set_upgrader:
    input r0 as address.public;
    async set_upgrader self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/set_upgrader.future;

finalize set_upgrader:
    input r0 as address.public;
    input r1 as address.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    set r1 into upgrader[true];

function set_upgrade_delay:
    input r0 as u32.public;
    async set_upgrade_delay self.caller r0 into r1;
    output r1 as jusd_oracle_production.aleo/set_upgrade_delay.future;

finalize set_upgrade_delay:
    input r0 as address.public;
    input r1 as u32.public;
    get admin[true] into r2;
    assert.eq r0 r2;
    get.or_use upgrade_delay[true] 0u32 into r3;
    gte r1 r3 into r4;
    assert.eq r4 true;
    set r1 into upgrade_delay[true];

function disable_upgrades:
    async disable_upgrades self.caller into r0;
    output r0 as jusd_oracle_production.aleo/disable_upgrades.future;

finalize disable_upgrades:
    input r0 as address.public;
    get admin[true] into r1;
    assert.eq r0 r1;
    set true into upgrades_disabled[true];

constructor:
    is.eq edition 0u16 into r0;
    branch.eq r0 false to end_then_0_0;
    assert.eq program_owner aleo15z3xv5a8r749wn0lmdysq7u4rnj4fd6n3ygv3autsrp4c9nj35gq7n9ljl;
    branch.eq true true to end_otherwise_0_1;
    position end_then_0_0;
    cast checksum edition into r1 as ChecksumEdition;
    hash.bhp256 r1 into r2 as field;
    get.or_use upgrade_approved[r2] false into r3;
    assert.eq r3 true;
    get.or_use upgrades_disabled[true] false into r4;
    not r4 into r5;
    assert.eq r5 true;
    get upgrade_eta[r2] into r6;
    gte block.height r6 into r7;
    assert.eq r7 true;
    get admin[true] into r8;
    get.or_use upgrader[true] r8 into r9;
    assert.eq program_owner r9;
    position end_otherwise_0_1;

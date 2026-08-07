# 2026-01-olas Report

## [H-01] Broken TWAP validation allows spot-price manipulation and renders slippage checks ineffective

Final report: [F-2](https://code4rena.com/audits/2026-01-olas/submissions/F-2)

*Submitted by [BenRai](https://code4rena.com/audits/2026-01-olas/submissions/S-847), also found by [0x\_DyDx](https://code4rena.com/audits/2026-01-olas/submissions/S-45), [0xastronatey](https://code4rena.com/audits/2026-01-olas/submissions/S-78), [0xbrett8571](https://code4rena.com/audits/2026-01-olas/submissions/S-84), [0xDemon](https://code4rena.com/audits/2026-01-olas/submissions/S-1235), [0xFBI](https://code4rena.com/audits/2026-01-olas/submissions/S-34), [0xkujen](https://code4rena.com/audits/2026-01-olas/submissions/S-770), [0xshdax](https://code4rena.com/audits/2026-01-olas/submissions/S-104), [0xVrka](https://code4rena.com/audits/2026-01-olas/submissions/S-798), [4nibhal](https://code4rena.com/audits/2026-01-olas/submissions/S-748), [7Tecra7](https://code4rena.com/audits/2026-01-olas/submissions/S-30), [Aamir](https://code4rena.com/audits/2026-01-olas/submissions/S-995), [ACai](https://code4rena.com/audits/2026-01-olas/submissions/S-776), [AcsonBarbosa](https://code4rena.com/audits/2026-01-olas/submissions/S-234), [AgentPulse](https://code4rena.com/audits/2026-01-olas/submissions/S-1012), [aman234](https://code4rena.com/audits/2026-01-olas/submissions/S-782), [AnonOpcode](https://code4rena.com/audits/2026-01-olas/submissions/S-1126), [Auditor3](https://code4rena.com/audits/2026-01-olas/submissions/S-424), [ayazwx](https://code4rena.com/audits/2026-01-olas/submissions/S-866), [bhatmuneeb](https://code4rena.com/audits/2026-01-olas/submissions/S-1098), [Biqua](https://code4rena.com/audits/2026-01-olas/submissions/S-492), [BlueSheep](https://code4rena.com/audits/2026-01-olas/submissions/S-780), [bun](https://code4rena.com/audits/2026-01-olas/submissions/S-259), [catower917](https://code4rena.com/audits/2026-01-olas/submissions/S-116), [ChainSentry](https://code4rena.com/audits/2026-01-olas/submissions/S-702), [chuvak](https://code4rena.com/audits/2026-01-olas/submissions/S-284), [codecoffeeguy](https://code4rena.com/audits/2026-01-olas/submissions/S-3), [coinssp... [truncated]

`autonolas-tokenomics/../contracts/oracles/UniswapPriceOracle.sol` [#L55-L91](https://github.com/valory-xyz/autonolas-tokenomics/blob/bbec5ac12721a62672fb7a5ffba5c40f5a46d8cb/contracts/oracles/UniswapPriceOracle.sol#L55-L91)

The `validatePrice()` function does not compute a real Uniswap V2 TWAP and instead collapses to the current spot price, making the slippage check ineffective and trivially manipulable within a single block.

#### Finding Description

The `validatePrice()` function is meant to validate the trade price against a time-weighted average price (TWAP) from a Uniswap V2 pair, enforcing a maximum allowed slippage. Correct TWAP-based validation is a core security mechanism against flash loans, sandwich attacks, and short-term price manipulation by averaging prices over time.

Uniswap V2 exposes cumulative price variables (price0CumulativeLast and price1CumulativeLast) that grow monotonically over time, encoding the reserve ratio in UQ112x112 format multiplied by elapsed time. To compute a TWAP, a consumer must:

1. Snapshot cumulative prices and timestamps at time t0
2. Read cumulative prices again at time t1
3. Compute the average price as the difference divided by elapsed time

`validatePrice()` deviates from this design:

- It reads the latest cumulative price from the pair
- Reads blockTimestampLast from getReserves()
- Builds an artificial “cumulative price” using the current tradePrice
- Derives a “TWAP” from these values
- Compares that “TWAP” to the current trade price to enforce slippage

The core bug is in the construction and use of cumulative prices:

```
uint256 cumulativePrice = cumulativePriceLast + (tradePrice * elapsedTime);

uint256 timeWeightedAverage = (cumulativePrice - cumulativePriceLast) / elapsedTime;
```

This simplifies to

```
timeWeightedAverage =
(cumulativePriceLast + (tradePrice * elapsedTime) - cumulativePriceLast) / elapsedTime =
(tradePrice * elapsedTime)/ elapsedTime =
tradePrice
```

The computed TWAP is always equal to the current tradePrice, regardless of history, elapsed time, or pool liquidity. The slippage check is effectively nullified because the deviation is always zero (aside from rounding).

Further issues:

- tradePrice comes from getPrice() and is not guaranteed to reflect Uniswap reserves.
- The Uniswap V2 cumulative prices are UQ112x112, but the function uses raw uint256 math without proper fixed-point handling.
- blockTimestampLast reflects the last reserve update, not a consumer-controlled oracle observation.
- The function is view and uses no persisted state, so it is fully exploitable via flash loans or same-block reserve manipulation.

UniswapPriceOracle is used on chains with Uniswap V2 pools (e.g. Ethereum mainnet). `validatePrice()` is the gate for all OLAS swap and liquidity-exit flows that use V2 oracles.

1. BuyBackBurner.\_buyOLAS() (V2 path)

- Called from buyBack(secondToken, secondTokenAmount) when using V2 pools.
- Flow: require(IOracle(poolOracle).validatePrice(maxSlippage), “Before swap slippage limit is breached”) → getPrice() → \_performSwap() → getPrice() again → post-swap bounds check.
- Anyone can call buyBack() after secondTokens (e.g. WETH) are deposited into the contract. The protocol swaps treasury/user deposits for OLAS and sends it to bridge2Burner for burning or bridging.
- Because validatePrice() always passes (TWAP ≈ spot), the pre-swap check is ineffective. An attacker can flash-loan, manipulate the pool, and have the buyback execute at the manipulated price. The protocol receives less OLAS per unit of ETH, and the attacker can unwind to capture arbitrage profit.

  2. LiquidityManagerETH.*checkTokensAndRemoveLiquidityV2() and LiquidityManagerOptimism.*checkTokensAndRemoveLiquidityV2()
- Called from convertToV3() when migrating V2 LP to V3.
- Flow: if (!IOracle(oracleV2).validatePrice(maxSlippage / 100)) revert SlippageLimitBreached() → remove V2 liquidity → mint V3.
- Only the owner can call convertToV3(). The oracle is used to ensure the V2 exit happens at a fair price before migrating to V3.
- Because validatePrice() always passes, the protocol can exit V2 liquidity at a manipulated price. The resulting token amounts (OLAS and quote) are worse than the true TWAP would imply, and the attacker can profit from the price deviation when the protocol swaps or migrates.

Attacker scenario

1. Observe a `buyBack()` or `convertToV3()` transaction in the mempool.
2. Swap to move the Uniswap V2 pool price (e.g. large swap in either direction).
3. Execute the victim transaction in the same block.
4. `validatePrice()` passes because TWAP ≈ manipulated spot.
5. Swap or liquidity removal executes at the manipulated price.
6. Attacker reverses the pool manipulation in the same block.
7. Attacker pockets the arbitrage; the protocol or users take the loss.

The attack is cheap (flash loan + gas), permissionless, and repeatable. The same logic applies to any chain where UniswapPriceOracle is used for OLAS swaps or liquidity exits.

#### Recommendation

Implement a proper Uniswap V2 TWAP oracle pattern by persisting cumulative price snapshots across blocks and computing averages from differences between observations:

- Store price{0,1}CumulativeLast and timestampLast in contract storage
- Update them in a state-changing function (e.g. updateOracle())
- Compute TWAPs using cumulative price deltas
- Correctly handle UQ112x112 fixed-point math

Slippage should be evaluated only after a correct TWAP is computed. This restores the intended oracle guarantees and protects against same-block and flash-loan-based price manipulation.

---


## [H-02] Variable Overwrite in checkPoolAndGetCenterPrice() Creates Dead-Code Deviation Check, Leaving All V3 Protocol-Owned Liquidity Operations Unprotected

Final report: [F-3](https://code4rena.com/audits/2026-01-olas/submissions/F-3)

*Submitted by [fx](https://code4rena.com/audits/2026-01-olas/submissions/S-471), also found by [0x\_oi](https://code4rena.com/audits/2026-01-olas/submissions/S-377), [0xastronatey](https://code4rena.com/audits/2026-01-olas/submissions/S-132), [0xDemon](https://code4rena.com/audits/2026-01-olas/submissions/S-1223), [0xFBI](https://code4rena.com/audits/2026-01-olas/submissions/S-66), [0xSeer](https://code4rena.com/audits/2026-01-olas/submissions/S-19), [abdelhaq16](https://code4rena.com/audits/2026-01-olas/submissions/S-262), [AcsonBarbosa](https://code4rena.com/audits/2026-01-olas/submissions/S-583), [AnonOpcode](https://code4rena.com/audits/2026-01-olas/submissions/S-1151), [Aristos](https://code4rena.com/audits/2026-01-olas/submissions/S-1243), [Auditor3](https://code4rena.com/audits/2026-01-olas/submissions/S-422), [Avalance](https://code4rena.com/audits/2026-01-olas/submissions/S-1259), [DanXIII](https://code4rena.com/audits/2026-01-olas/submissions/S-62), [Egbe](https://code4rena.com/audits/2026-01-olas/submissions/S-959), [emerald7017](https://code4rena.com/audits/2026-01-olas/submissions/S-212), [ESG](https://code4rena.com/audits/2026-01-olas/submissions/S-817), [Funen](https://code4rena.com/audits/2026-01-olas/submissions/S-100), [Gakarot](https://code4rena.com/audits/2026-01-olas/submissions/S-197), [gesha17](https://code4rena.com/audits/2026-01-olas/submissions/S-345), [golem0](https://code4rena.com/audits/2026-01-olas/submissions/S-1007), [grearlake](https://code4rena.com/audits/2026-01-olas/submissions/S-1330), [humaira45](https://code4rena.com/audits/2026-01-olas/submissions/S-954), [I1iveF0rTh1Sh1t](https://code4rena.com/audits/2026-01-olas/submissions/S-404), [inh3l](https://code4rena.com/audits/2026-01-olas/submissions/S-1134), [Inspecktor](https://code4rena.com/audits/2026-01-olas/submissions/S-695), [jayx](https://code4rena.com/audits/2026-01-olas/submissions/S-573), [jkk812812](https://code4rena.com/audits/2026-01-olas/submissions/S-1089), [jo13](h... [truncated]

- `autonolas-tokenomics/../contracts/pol/LiquidityManagerCore.sol` [#L1091-L1137](https://github.com/valory-xyz/autonolas-tokenomics/blob/v1.4.2-pre-external-audit/contracts/pol/LiquidityManagerCore.sol#L1091-L1137)
- `autonolas-tokenomics/../contracts/pol/LiquidityManagerCore.sol` [#L1104-L1106](https://github.com/valory-xyz/autonolas-tokenomics/blob/v1.4.2-pre-external-audit/contracts/pol/LiquidityManagerCore.sol#L1104-L1106)
- `autonolas-tokenomics/../contracts/pol/LiquidityManagerCore.sol` [#L1113-L1116](https://github.com/valory-xyz/autonolas-tokenomics/blob/v1.4.2-pre-external-audit/contracts/pol/LiquidityManagerCore.sol#L1113-L1116)
- `/autonolas-tokenomics/../contracts/pol/LiquidityManagerCore.sol` [#L1119](https://github.com/valory-xyz/autonolas-tokenomics/blob/v1.4.2-pre-external-audit/contracts/pol/LiquidityManagerCore.sol#L1119)
- `/autonolas-tokenomics/../contracts/pol/LiquidityManagerCore.sol` [#L1123](https://github.com/valory-xyz/autonolas-tokenomics/blob/v1.4.2-pre-external-audit/contracts/pol/LiquidityManagerCore.sol#L1123)

`LiquidityManagerCore.checkPoolAndGetCenterPrice()` is the sole TWAP oracle guard for all V3 protocol-owned liquidity operations. It protects **five LiquidityManager functions** that manage protocol-owned concentrated liquidity positions, plus two BuyBackBurner call sites:

**LiquidityManager operations (protocol-owned liquidity):**

- `convertToV3()` (line 689) — migrating V2 liquidity to V3
- `changeRanges()` (line 761) — adjusting concentrated liquidity tick ranges
- `collectFees()` (line 822) — collecting accrued trading fees
- `decreaseLiquidity()` (line 893) — removing liquidity from positions
- `increaseLiquidity()` (line 974) — adding liquidity to positions

**BuyBackBurner call sites:**

- `BuyBackBurner._buyOLAS()` (line 231) — V3 swap path
- `BuyBackBurner.checkPoolPrices()` (line 367) — legacy compatibility

The function is supposed to compare the pool’s current spot price against a TWAP and revert if the deviation exceeds `MAX_ALLOWED_DEVIATION` (10%). However, a variable overwrite at line 1119 causes the deviation check to compare the TWAP against itself, producing a deviation of zero on every call. **The `MAX_ALLOWED_DEVIATION` check is dead code — it can never trigger.**

Additionally, two early-return paths bypass the deviation check entirely for stale or new pools, returning the raw spot price without any validation. Together, these bugs cover every possible execution path:

**Root Cause A: Early-Return Bypasses (Lines 1104, 1114)**

Two early-return paths skip TWAP validation entirely and return the raw spot price:

```
// PATH 1: Stale observations (line 1104-1106)
(uint32 oldestTimestamp,,,) = IUniswapV3(pool).observations(observationIndex);
if (oldestTimestamp + SECONDS_AGO < block.timestamp) {
    return centerSqrtPriceX96;  // Returns SPOT price, NO TWAP check
}

// PATH 2: TWAP call failure (line 1113-1115)
(bool success, bytes memory returnData) = address(this).staticcall(payload);
if (!success) {
    return centerSqrtPriceX96;  // Returns SPOT price, NO TWAP check
}
```

**Path 1** triggers when the pool’s most recent observation is more than `SECONDS_AGO` (1800s = 30 min) old. This fires for any pool that hasn’t had a swap in 30+ minutes.

**Path 2** triggers when `getTwapFromOracle()` fails, which happens for newly created pools (e.g., immediately after `convertToV3()`) that don’t have enough observation history for a 30-minute TWAP.

Both return the current spot price with no manipulation check.

**Root Cause B: Return-Variable Overwrite at Line 1119 Makes Deviation Check Dead Code (Primary Bug)**

When the function passes both early-return checks (active pool with sufficient history), the TWAP deviation check executes — but a variable overwrite causes it to compare the TWAP price against itself, producing zero deviation on every call. The mechanism is a reuse of the function’s return variable `centerSqrtPriceX96` as the decode target for the TWAP result:

```
function checkPoolAndGetCenterPrice(address pool) public view returns (uint160 centerSqrtPriceX96) {
    // Line 1094: centerSqrtPriceX96 = SPOT price from slot0
    (centerSqrtPriceX96, observationIndex) = _getPriceAndObservationIndexFromSlot0(pool);

    // ... early returns (Root Cause A) ...

    // Line 1119: centerSqrtPriceX96 is OVERWRITTEN with TWAP-derived sqrt price
    (twapPrice, centerSqrtPriceX96) = abi.decode(returnData, (uint256, uint160));
    //           ^^^^^^^^^^^^^^^^^ original spot price is LOST

    // Line 1123: "instant price" is computed from the OVERWRITTEN variable
    uint256 instantPrice = mulDiv(uint256(centerSqrtPriceX96), uint256(centerSqrtPriceX96), (1 << 64));
    // instantPrice == twapPrice (both derive from the same centerSqrtPriceX96)

    // Lines 1128-1130: deviation = |twapPrice - twapPrice| / twapPrice = 0 ALWAYS
    deviation = (instantPrice > twapPrice)
        ? mulDiv((instantPrice - twapPrice), 1e18, twapPrice)
        : mulDiv((twapPrice - instantPrice), 1e18, twapPrice);

    // Line 1134: This NEVER triggers because deviation is always 0
    if (deviation > MAX_ALLOWED_DEVIATION) {
        revert Overflow(deviation, MAX_ALLOWED_DEVIATION);
    }
}
```

The precise mechanism: `centerSqrtPriceX96` is the function’s named return variable, initialized to the spot price from `slot0()` at line 1094. At line 1119, `abi.decode(returnData, (uint256, uint160))` overwrites this variable with the TWAP-derived sqrt price from `getTwapFromOracle()`. The `getTwapFromOracle()` function (line 1067-1086) returns `(price, centerSqrtPriceX96)` where `price = centerSqrtPriceX96^2 / 2^64` — the two return values are mathematically coupled. When line 1123 then computes `instantPrice = centerSqrtPriceX96^2 / 2^64`, it reproduces the exact same computation that produced `twapPrice`, because `centerSqrtPriceX96` now holds the TWAP sqrt price instead of the spot sqrt price. The deviation is mathematically guaranteed to be zero:

```
instantPrice = overwritten_centerSqrtPriceX96^2 / 2^64
             = twap_sqrt^2 / 2^64
             = twapPrice                            (by definition from getTwapFromOracle)
deviation    = |twapPrice - twapPrice| / twapPrice = 0    (ALWAYS)
```

**Combined Effect**

| Pool State | Code Path | Result |
| --- | --- | --- |
| Stale observations (>30 min since last swap) | Root Cause A, Path 1 (line 1104) | Returns spot price, no TWAP check |
| New pool (insufficient observation history) | Root Cause A, Path 2 (line 1114) | Returns spot price, no TWAP check |
| Active pool with sufficient history | Root Cause B (line 1119) | TWAP check runs but deviation = 0 always |

There is no condition under which this function detects price manipulation.

#### Risk

**Likelihood: Medium**

Root Cause A requires a pool in a specific state (stale or new). This is realistic — OLAS is not a high-frequency trading token, and 30+ minutes without a swap on a specific pool is common, especially on L2 chains. New pools are immediately vulnerable after `convertToV3()`.

Root Cause B fires on every call where the TWAP oracle succeeds — the “normal” code path for active pools with sufficient history. This is the default condition for established pools.

Together, every possible pool state is covered. An attacker can monitor pool activity and act when conditions align (Root Cause A), or attack any active pool at any time (Root Cause B).

**Impact: Medium**

The `MAX_ALLOWED_DEVIATION` check is dead code — it cannot trigger under any condition. This leaves all five LiquidityManager operations exposed to flash-loan price manipulation:

- **`changeRanges()`** (line 761): Uses `centerSqrtPriceX96` to calculate new tick ranges. An attacker can manipulate the pool price, causing the protocol to rebalance its concentrated liquidity position to a range centered on the manipulated price. When the attacker restores the price, the protocol’s position is out of range and earns no fees.
- **`convertToV3()`** (line 689): Uses `centerSqrtPriceX96` to calculate tick ranges for the new V3 position. Manipulation causes the protocol to create its initial position at the wrong price range, permanently locking liquidity in an unfavorable range.
- **`decreaseLiquidity()`** (line 893): The price check is supposed to prevent removal of liquidity during manipulation (which affects the token ratio received). Without it, an attacker can manipulate the price to extract a more favorable token ratio from the protocol’s position.
- **`increaseLiquidity()`** (line 974): The price check is supposed to prevent adding liquidity at a manipulated price (which affects the token ratio deposited). Without it, the protocol deposits at an unfavorable ratio.
- **`collectFees()`** (line 822): The price check prevents fee collection during manipulation (which could affect swap calculations in the same transaction).

These are **protocol-owned liquidity management operations** — they control the protocol’s own concentrated liquidity positions on Uniswap V3. The oracle guard is their sole defense against flash-loan manipulation. The impact is Medium because exploitation requires a flash-loan manipulation of a V3 pool in the same block as a protocol operation, and the loss magnitude depends on the pool’s liquidity depth and the size of the affected operation.

#### Proof of Concept

[View detailed Proof of Concept](https://code4rena.com/audits/2026-01-olas/submissions/S-471)

#### Recommended Mitigation

Two fixes are needed — one for each root cause:

**Root Cause A:** Revert when TWAP is unavailable instead of silently returning unprotected spot price:

```
// Line 1104-1106: REVERT instead of early return
if (oldestTimestamp + SECONDS_AGO < block.timestamp) {
    revert InsufficientObservationHistory(pool, oldestTimestamp, SECONDS_AGO);
}

// Line 1113-1115: REVERT instead of early return
if (!success) {
    revert TwapCalculationFailed(pool);
}
```

**Root Cause B:** Preserve the original spot price before the overwrite:

```
// After line 1094, before the TWAP fetch:
uint160 spotSqrtPriceX96 = centerSqrtPriceX96;  // Preserve spot price

// Line 1119 still overwrites centerSqrtPriceX96 (needed for return value):
(twapPrice, centerSqrtPriceX96) = abi.decode(returnData, (uint256, uint160));

// Line 1123: Use the ORIGINAL spot price, not the overwritten TWAP value:
uint256 instantPrice = mulDiv(uint256(spotSqrtPriceX96), uint256(spotSqrtPriceX96), (1 << 64));
```

---


## [H-03] Balancer oracle uses vault balances as price and can be steered by anyone

Final report: [F-4](https://code4rena.com/audits/2026-01-olas/submissions/F-4)

*Submitted by [Silvermist](https://code4rena.com/audits/2026-01-olas/submissions/S-248), also found by [Ace2](https://code4rena.com/audits/2026-01-olas/submissions/S-1058), [AzizHack](https://code4rena.com/audits/2026-01-olas/submissions/S-1198), [Funen](https://code4rena.com/audits/2026-01-olas/submissions/S-95), [holtzzx](https://code4rena.com/audits/2026-01-olas/submissions/S-1327), [joker158](https://code4rena.com/audits/2026-01-olas/submissions/S-98), [LittleJoe](https://code4rena.com/audits/2026-01-olas/submissions/S-93), [Nerca](https://code4rena.com/audits/2026-01-olas/submissions/S-784), [nisedo](https://code4rena.com/audits/2026-01-olas/submissions/S-905), [santipu\_](https://code4rena.com/audits/2026-01-olas/submissions/S-1005), [Silverwind](https://code4rena.com/audits/2026-01-olas/submissions/S-1044), [udaykiranpedda](https://code4rena.com/audits/2026-01-olas/submissions/S-663), and [Yifan](https://code4rena.com/audits/2026-01-olas/submissions/S-1172)*

`autonolas-tokenomics/../contracts/oracles/BalancerPriceOracle.sol` [#L72-L80](https://github.com/valory-xyz/autonolas-tokenomics/blob/bbec5ac12721a62672fb7a5ffba5c40f5a46d8cb/contracts/oracles/BalancerPriceOracle.sol#L72-L80)

`BalancerPriceOracle.getPrice()` does not read a Balancer oracle accumulator. It reads the pool balances directly from the Vault and returns a simple reserve ratio. That value is a spot price and it can change whenever the pool is traded.

```
(, uint256[] memory balances, ) = IVault(balancerVault).getPoolTokens(balancerPoolId);
uint256 balanceIn = balances[direction];
uint256 balanceOut = balances[(direction + 1) % 2];
return (balanceOut * 1e18) / balanceIn;
```

`updatePrice()` is permissionless and writes the oracle snapshot based on the current spot price returned by `getPrice()`. This means any address can decide when the snapshot should be updated, and the snapshot is always derived from the spot regime that exists at that moment.

```
uint256 currentPrice = getPrice();
snapshot.cumulativePrice += snapshot.averagePrice * elapsedTime;
uint256 averagePrice = (snapshot.cumulativePrice + (currentPrice * elapsedTime)) /
    ((snapshot.cumulativePrice / snapshot.averagePrice) + elapsedTime);
snapshot.averagePrice = averagePrice;
snapshot.lastUpdated = block.timestamp;
```

`validatePrice(slippage)` then compares the current spot price (`getPrice()`) to a band around the computed “timeWeightedAverage”. In practice, this check is only enforcing that current spot is near the oracle’s stored snapshot state. If an attacker can keep the pool in a manipulated spot regime and call `updatePrice()` over time, the stored snapshot can be moved away from the original market price and toward the attacker-controlled regime. Then `validatePrice()` can still return true while the price is far from the original reference.

#### Recommended mitigation steps

Do not use raw Vault balances as an oracle for slippage protection of large protocol swaps.

#### Proof of Concept

[View detailed Proof of Concept](https://code4rena.com/audits/2026-01-olas/submissions/S-248)

<https://github.dev/code-423n4/reports/blob/main/olas/2026-01-olas.md>

---


## [H-04] Incorrect TWAP calculation in BalancerPriceOracle allows price manipulation and breaks oracle guarantees

Final report: [F-6](https://code4rena.com/audits/2026-01-olas/submissions/F-6)

*Submitted by [BenRai](https://code4rena.com/audits/2026-01-olas/submissions/S-853), also found by [0xDemon](https://code4rena.com/audits/2026-01-olas/submissions/S-1244), [Ace2](https://code4rena.com/audits/2026-01-olas/submissions/S-1053), [Gakarot](https://code4rena.com/audits/2026-01-olas/submissions/S-308), [jkk812812](https://code4rena.com/audits/2026-01-olas/submissions/S-1060), [JoshuaM33](https://code4rena.com/audits/2026-01-olas/submissions/S-844), [Morraez](https://code4rena.com/audits/2026-01-olas/submissions/S-1181), [rage](https://code4rena.com/audits/2026-01-olas/submissions/S-544), and [santipu\_](https://code4rena.com/audits/2026-01-olas/submissions/S-1057)*

`autonolas-tokenomics/../contracts/oracles/BalancerPriceOracle.sol` [#L84-L128](https://github.com/valory-xyz/autonolas-tokenomics/blob/bbec5ac12721a62672fb7a5ffba5c40f5a46d8cb/contracts/oracles/BalancerPriceOracle.sol#L84-L128)

The `BalancerPriceOracle.updatePrice()` function implements an incorrect Time-Weighted Average Price (TWAP) formula that does not properly accumulate price over time, making the oracle unreliable and susceptible to manipulation.

#### Finding Description

The protocol implements a price oracle that attempts to provide a Time-Weighted Average Price (TWAP) from Balancer pool prices. The `updatePrice()` function is responsible for updating the price snapshot and calculating the average price over time, which is then used to validate new price updates through a slippage check.

The core issue lies in the TWAP calculation formula within the `updatePrice()` function:

```
// Update cumulative price with the previous average over the elapsed time
snapshot.cumulativePrice += snapshot.averagePrice * elapsedTime;

// Update the average price to reflect the current price
uint256 averagePrice = (snapshot.cumulativePrice + (currentPrice * elapsedTime)) /
    ((snapshot.cumulativePrice / snapshot.averagePrice) + elapsedTime);
```

This implementation breaks the fundamental TWAP formula in multiple ways:

**Issue 1: Accumulating `averagePrice` instead of `lastPrice`**

The `snapshot.cumulativePrice` price should accumulate the actual observed price over each time period. Instead,

```
// Update cumulative price with the previous average over the elapsed time
snapshot.cumulativePrice += snapshot.averagePrice * elapsedTime;
```

the code accumulates `snapshot.averagePrice`, which is itself a derived average. This creates a recursive averaging effect where:

- First update: accumulates some initial price
- Second update: accumulates the average of the first update (not the actual price that was valid during that period)
- Third update: accumulates an average of averages

This fundamentally breaks the TWAP property because it doesn’t weight each actual price observation by its duration.

**Issue 2: Incorrect average calculation**

A proper TWAP formula is:

```
TWAP = Σ(price_i × duration_i) / Σ(duration_i)
```

The implemented formula attempts to recover the total elapsed time by dividing `snapshot.cumulativePrice / snapshot.averagePrice`, which:

- Loses precision through integer division
- Assumes the relationship `cumulativePrice = averagePrice × totalTime` holds, which it doesn’t after the first update due to Issue 1
- Becomes increasingly inaccurate over time as rounding errors compound

**Impact**

This broken TWAP implementation has severe consequences:

1. **Oracle Manipulation**: The slippage check validates `currentPrice` against the calculated `averagePrice`. Since the average doesn’t reflect true time-weighted prices, an attacker can:

   - Manipulate the Balancer pool price after the `minUpdateTimePeriod`
   - Call `updatePrice()` with the manipulated price
   - The broken TWAP formula will not properly account for the manipulation duration
   - Subsequent price updates will use this corrupted average, allowing further manipulation

#### Recommendation

Implement a proper TWAP calculation that accumulates actual prices weighted by time. For this you can use the observation pattern similar to UniswapV3 where observations (timeStamp, priceCumulative) are saved in a circular buffer. Let a keeper call updatePrice on a regular basis to ensure continues data. Also consider implementing a TWAP time range (e.g. 15 minutes) to ensure a proper time frame for the result.

The update function and the getPrice functions could look like this:

```
function update() external {
    uint256 timeElapsed = block.timestamp - lastUpdateTimestamp;

    if (timeElapsed > 0) {
        // Get spot price from Balancer pool
        uint256 spotPrice = getBalancerSpotPrice();

        // Update accumulator
        priceAccumulator += spotPrice * timeElapsed;
        lastUpdateTimestamp = block.timestamp;

        // Store observation
        observations.push(Observation({
            timestamp: block.timestamp,
            priceCumulative: priceAccumulator
        }));
    }
}

function getTWAP() public view returns (uint256) {
    uint256 currentTime = block.timestamp;
    uint256 targetTime = currentTime - PERIOD;

    // Find observation closest to targetTime
    Observation memory oldObservation = findObservation(targetTime);

    uint256 priceDelta = priceAccumulator - oldObservation.priceCumulative;
    uint256 timeDelta = currentTime - oldObservation.timestamp;

    return priceDelta / timeDelta;
}
```

---


## [H-05] Insolvency via Cross-Service Reentrancy in StakingBase._withdraw

Final report: [F-8](https://code4rena.com/audits/2026-01-olas/submissions/F-8)

*Submitted by [fullstop](https://code4rena.com/audits/2026-01-olas/submissions/S-229), also found by [0xbrett8571](https://code4rena.com/audits/2026-01-olas/submissions/S-148), [0xnija](https://code4rena.com/audits/2026-01-olas/submissions/S-1082), [1ultimat3](https://code4rena.com/audits/2026-01-olas/submissions/S-1014), [Agontuk](https://code4rena.com/audits/2026-01-olas/submissions/S-902), [BlueSheep](https://code4rena.com/audits/2026-01-olas/submissions/S-1141), [brandon](https://code4rena.com/audits/2026-01-olas/submissions/S-648), [bransdotcom](https://code4rena.com/audits/2026-01-olas/submissions/S-834), [chuvak](https://code4rena.com/audits/2026-01-olas/submissions/S-258), [coinsspor](https://code4rena.com/audits/2026-01-olas/submissions/S-73), [Cryptor](https://code4rena.com/audits/2026-01-olas/submissions/S-1022), [demonhat](https://code4rena.com/audits/2026-01-olas/submissions/S-738), [Dest1ny\_rs](https://code4rena.com/audits/2026-01-olas/submissions/S-192), [Diavolo](https://code4rena.com/audits/2026-01-olas/submissions/S-1218), [Drothon](https://code4rena.com/audits/2026-01-olas/submissions/S-848), [edoscoba](https://code4rena.com/audits/2026-01-olas/submissions/S-610), [eightzerofour](https://code4rena.com/audits/2026-01-olas/submissions/S-211), [hexcoded0033](https://code4rena.com/audits/2026-01-olas/submissions/S-924), [hiram](https://code4rena.com/audits/2026-01-olas/submissions/S-899), [ht111111](https://code4rena.com/audits/2026-01-olas/submissions/S-251), [ifex445](https://code4rena.com/audits/2026-01-olas/submissions/S-467), [kind0dev](https://code4rena.com/audits/2026-01-olas/submissions/S-260), [Konzy](https://code4rena.com/audits/2026-01-olas/submissions/S-762), [LMLLayersystem](https://code4rena.com/audits/2026-01-olas/submissions/S-202), [noxpenguin](https://code4rena.com/audits/2026-01-olas/submissions/S-962), [psyone](https://code4rena.com/audits/2026-01-olas/submissions/S-417), [recr4sh](https://code4rena.com/audits/2026-01-olas/submiss... [truncated]

`autonolas-registries/../contracts/staking/StakingBase.sol` [#L929-L948](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/staking/StakingBase.sol#L929-L948)

#### Finding description and impact

The `_withdraw` function in `StakingBase.sol` violates the **Checks-Effects-Interactions (CEI)** pattern. It caches the global `balance` into a local variable `updatedBalance`, performs external calls (transfers) via a loop, and only updates the global `balance` state variable at the very end of the function.

**Root Cause:**

1. **State Update Lag:** The global `balance` is updated *after* external calls return.
2. **Lack of Reentrancy Guard:** The contract lacks a global `nonReentrant` modifier, allowing cross-service reentrancy even if single-service reentrancy is blocked by state deletion.

**Attack Scenario:**

An attacker controls two service IDs (Service A and Service B).

1. Attacker calls `unstake(Service A)`.
2. `_withdraw` reads `balance` (e.g., 100 ETH) into `updatedBalance`.
3. The contract sends rewards for Service A.
4. The attacker intercepts control in the `receive()` fallback and calls `unstake(Service B)`.
5. **Reentrancy:** The inner `unstake(Service B)` execution reads the *stale* global `balance` (still 100 ETH) because the outer execution has not yet updated it.
6. The inner execution calculates the new balance (e.g., 90 ETH) and writes it to storage.
7. The inner execution finishes. Control returns to the outer `unstake(Service A)`.
8. **State Overwrite:** The outer execution continues using its local `updatedBalance` (calculated based on the initial 100 ETH). It overwrites the global `balance` (e.g., setting it to 90 ETH), effectively erasing the deduction made by Service B.

**Impact:**

The contract’s recorded `balance` becomes higher than its actual physical ETH balance (Insolvency). This accounting discrepancy accumulates with every attack.

#### Recommended mitigation steps

1. **Add Reentrancy Guard:** Inherit from `ReentrancyGuard` and apply the `nonReentrant` modifier to all external state-changing functions (`stake`, `unstake`, `claim`, `checkpointAndClaim`, `forcedUnstake`).
2. **Fix CEI Pattern:** Refactor `_withdraw` to update the global state *before* performing external transfers.

#### Proof of Concept

[View detailed Proof of Concept](https://code4rena.com/audits/2026-01-olas/submissions/S-229)

---


## [H-06] Service owner can steal protocol tokens by exploiting reentrancy in create

Final report: [F-123](https://code4rena.com/audits/2026-01-olas/submissions/F-123)

*Submitted by [SpicyMeatball](https://code4rena.com/audits/2026-01-olas/submissions/S-578), also found by [Cecuro](https://code4rena.com/audits/2026-01-olas/submissions/S-506) and [Race](https://code4rena.com/audits/2026-01-olas/submissions/S-111)*

- `autonolas-registries/../contracts/ServiceManager.sol` [#L168](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/ServiceManager.sol#L168)
- `autonolas-registries/../contracts/ServiceRegistry.sol` [#L270](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/ServiceRegistry.sol#L270)

`ServiceManager.create()` does not follow the Checks-Effects-Interactions (CEI) pattern. This allows a malicious service creator to reenter the contract and modify service parameters before `ServiceRegistryTokenUtility.createWithToken()` is executed:

```
    function create(
        address serviceOwner,
        address token,
        bytes32 configHash,
        uint32[] memory agentIds,
        IService.AgentParams[] memory agentParams,
        uint32 threshold
    ) external returns (uint256 serviceId) {
        --- SNIP ---
        } else {
            --- SNIP ---
            // Call the original ServiceRegistry contract function
>>>         serviceId = IService(serviceRegistry).create(serviceOwner, configHash, agentIds, agentParams, threshold);
            // Create a token-related record for the service
>>>         IServiceTokenUtility(serviceRegistryTokenUtility).createWithToken(serviceId, token, agentIds, bonds);
        }
    }
```

**Attack Scenario**

- The attacker creates a service with a single agent and specifies a large USDC bond (e.g. `ServiceRegistryTokenUtility` balance);
- `ServiceRegistry.create()` mints a service NFT to the attacker using `_safeMint`;
- During the `onERC721Received` callback, the attacker reenters `ServiceManager` by calling `update()` and changes the bond amount to 1 wei;
- The attacker then calls `ServiceManager.activateRegistration()` and only pays the reduced bond amount;
- Execution resumes after the callback, and `ServiceRegistryTokenUtility.createWithToken()` is called using the stale bond configuration captured before reentrancy;
- Finally, the attacker terminates the service and withdraws the originally specified USDC bond from `ServiceRegistryTokenUtility`, effectively draining its funds.

#### Recommended mitigation steps

To enforce a secure CEI pattern and prevent reentrancy:

- Since `ServiceRegistry.totalSupply()` is known prior to minting, derive the expected `serviceId` in advance and call `serviceRegistryTokenUtility.createWithToken()` before invoking `ServiceRegistry.create()`. This ensures all state related to token bonds is finalized before any external calls occur.

Additionally or alternatively:

- Introduce a reentrancy guard on `ServiceManager.create()` and `ServiceManager.update()`.

#### Proof of Concept

[View detailed Proof of Concept](https://code4rena.com/audits/2026-01-olas/submissions/S-578)

---


## [H-07] Missing deadline parameter in register signatures

Final report: [F-166](https://code4rena.com/audits/2026-01-olas/submissions/F-166)

*Submitted by [santipu\_](https://code4rena.com/audits/2026-01-olas/submissions/S-858), also found by [Dinesh11G](https://code4rena.com/audits/2026-01-olas/submissions/S-597) and [SpicyMeatball](https://code4rena.com/audits/2026-01-olas/submissions/S-586)*

`autonolas-registries/../contracts/ServiceManager.sol` [#L421](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/ServiceManager.sol#L421)

The `registerAgentsWithSignature` function in the `ServiceManager` contract allows a service owner to register agent instances on behalf of an operator using a signed message.

```
function registerAgentsWithSignature(
        address operator,
        uint256 serviceId,
        address[] memory agentInstances,
        uint32[] memory agentIds,
        bytes memory signature
    ) external payable returns (bool success) {
        // Check the service owner
        address serviceOwner = IERC721(serviceRegistry).ownerOf(serviceId);
        if (msg.sender != serviceOwner) {
            revert OwnerOnly(msg.sender, serviceOwner);
        }

        // Get the (operator | serviceId) nonce for the registerAgents message
        // Push a pair of key defining variables into one key. Service Id or operator are not enough by themselves
        // as another service might use the operator address at the same time frame
        // operator occupies first 160 bits
        uint256 operatorService = uint256(uint160(operator));
        // serviceId occupies next 32 bits as serviceId is limited by the 2^32 - 1 value
        operatorService |= serviceId << 160;
        uint256 nonce = mapOperatorRegisterAgentsNonces[operatorService];
        // Get register agents message hash
        bytes32 msgHash = getRegisterAgentsHash(operator, serviceOwner, serviceId, agentInstances, agentIds, nonce);

        // Verify the signed hash against the operator address
        _verifySignedHash(operator, msgHash, signature);

        // ...
    }
```

The signature is computed over the following parameters:

- operator address
- service owner address
- service ID
- agent instance addresses
- agent IDs
- nonce

However, the message hash omits a critical parameter: a **deadline**. Without a deadline, the operator’s signature remains valid indefinitely, unless invalidated by a nonce change. This allows the service owner to store a valid signature and use it arbitrarily far into the future.

For example:

1. Bob creates a service and requests Alice to register agents using her signature.
2. Alice signs the message, allowing Bob to register on her behalf.
3. For whatever reason, Bob does ends up not using the signature. Instead, Alice registers the agents directly.
4. Some time later, Alice unbonds from Bob and retrieves her deposit.
5. Bob reconfigures the service and opens registrations again.
6. Bob reuses Alice’s old signature to register her agents without consent.
7. This triggers a bond transfer from Alice’s account, effectively locking her funds again.

This behavior is possible because `registerAgentsWithSignature` eventually calls `registerAgentsTokenDeposit` with the operator’s address:

```
        // Record the actual ERC20 bond
        bool isTokenSecured =
            IServiceTokenUtility(serviceRegistryTokenUtility).registerAgentsTokenDeposit(operator, serviceId, agentIds);
```

And within `registerAgentsTokenDeposit`, the contract transfers tokens directly from the operator:

```
safeTransferFrom(token, operator, address(this), totalBond);
```

As long as the operator has an active allowance for the `ServiceRegistryTokenUtility` contract, the bond can be forcibly transferred. Operators commonly maintain infinite allowances to save on gas when interacting with multiple services, increasing the likelihood of unintended bond transfers.

An operator’s valid signature can be reused at any point in the future, enabling a service owner to forcibly register agent instances and trigger bond transfers from the operator’s account without current consent. This undermines operator autonomy and can lead to unexpected token lockups. Because the token transfer depends only on a previously issued signature and an existing token allowance, malicious or careless reuse can silently lock operator funds in services they no longer intend to participate in.

#### Recommended mitigation steps

Introduce a deadline parameter to the signed message and include it in the hash computation. Then, enforce that the deadline has not passed before accepting the signature during execution.

---


## [H-08] Critical Logic Inversion in Price Guard Allows Flash-Loan Manipulation of Liquidity Operations

Final report: [F-204](https://code4rena.com/audits/2026-01-olas/submissions/F-204)

*Submitted by [prazzix86](https://code4rena.com/audits/2026-01-olas/submissions/S-347), also found by [ayazwx](https://code4rena.com/audits/2026-01-olas/submissions/S-868), [jkk812812](https://code4rena.com/audits/2026-01-olas/submissions/S-1097), [M4v3r1ck](https://code4rena.com/audits/2026-01-olas/submissions/S-1254), and [Nyx](https://code4rena.com/audits/2026-01-olas/submissions/S-1144)*

`autonolas-tokenomics/../contracts/pol/LiquidityManagerCore.sol` [#L1104-L1116](https://github.com/valory-xyz/autonolas-tokenomics/blob/bbec5ac12721a62672fb7a5ffba5c40f5a46d8cb/contracts/pol/LiquidityManagerCore.sol#L1104-L1116)

The `checkPoolAndGetCenterPrice` function in `LiquidityManagerCore.sol` is intended to be a security gate that prevents the protocol from interacting with Uniswap V3 pools at manipulated “instant” prices. It is designed to verify the slot0 price against a 30-minute Time-Weighted Average Price (TWAP).

However, two critical flaws in the implementation render this protection completely ineffective:

**1. Logic Inversion in History Check (Mature Pools)**
The contract uses the following check to decide whether to bypass the TWAP verification:

```
1104: if (oldestTimestamp + SECONDS_AGO < block.timestamp) {
1105:     return centerSqrtPriceX96;
1106: }
```

In Uniswap V3, `oldestTimestamp` is the timestamp of the earliest recorded price point in the observation buffer.

**If the pool is mature** (has ≥ 30 mins of history), the condition `oldestTimestamp + 1800 < block.timestamp` is TRUE.
**The Result**: The function returns the untrusted slot0 price immediately, bypassing the TWAP check for exactly the pools that have sufficient data to be checked.

**2. Fail-Open Architecture on Verification Failure (New Pools)**
If the pool is new (history < 30 mins), the code proceeds to call `getTwapFromOracle`. This call will typically revert because the Uniswap observe function requires data reaching back the full SECONDS\_AGO period.

```
1111: (bool success, bytes memory returnData) = address(this).staticcall(payload);
1112:
1113: // If the call has failed - observe was not successful...
1114: if (!success) {
1115:     return centerSqrtPriceX96;
1116: }
```

Instead of reverting (Fail-Closed), the protocol **catches the error and returns the untrusted price**. This creates a trivial bypass: an attacker can create a new pool, manipulate its price, and the protocol will use that manipulated price because the “security check” failed to execute.

**Step-by-Step Exploit Scenario**

- **Preparation**: Attacker identifies a liquidity operation (e.g., ConvertedToV3).
- **Manipulation**: Attacker creates a fresh Uniswap V3 pool for OLAS / SHITCOIN.
- **Flash Loan**: Attacker uses a flash loan to buy OLAS in this new pool, pushing the slot0 price to 100x the fair market value.
- **Protocol Trigger**: Attacker triggers the protocol to provide liquidity to this pool.

Bypass:

- checkPoolAndGetCenterPrice is called.
- The pool is new, so it tries getTwapFromOracle.
  observe([1800, 0]) reverts because the pool is only seconds old.
- The protocol catches the revert and returns the 100x manipulated slot0 price.
  **Profit**: The protocol mints a position or converts tokens based on the 100x price, allowing the attacker to effectively drain OLAS from the protocol in exchange for worthless tokens.

#### Impact

This is a Critical severity issue as it breaks the primary security assumption for price safety in the Protocol-Owned Liquidity (POL) module. It allows for the total drainage of assets committed to V3 liquidity operations via standard flash-loan price manipulation.

#### Recommended mitigation steps

The protocol should adopt a Fail-Closed security model and correct the history logic:

```
-        if (oldestTimestamp + SECONDS_AGO < block.timestamp) {
-            return centerSqrtPriceX96;
-        }
+        // Ensure the pool is mature enough to have TWAP data
+        if (oldestTimestamp + SECONDS_AGO > block.timestamp) {
+            revert PoolTooNew();
+        }

         uint256 twapPrice;
         bytes memory payload = abi.encodeCall(this.getTwapFromOracle, (pool));
         (bool success, bytes memory returnData) = address(this).staticcall(payload);

-        if (!success) {
-            return centerSqrtPriceX96;
-        }
+        require(success, "TWAP check failed");
```

#### Proof of Concept

[View detailed Proof of Concept](https://code4rena.com/audits/2026-01-olas/submissions/S-347)

---


## [H-09] Missing maximum bond signature parameter

Final report: [F-215](https://code4rena.com/audits/2026-01-olas/submissions/F-215)

*Submitted by [santipu\_](https://code4rena.com/audits/2026-01-olas/submissions/S-862), also found by [aestheticbhai](https://code4rena.com/audits/2026-01-olas/submissions/S-1238), [Evo](https://code4rena.com/audits/2026-01-olas/submissions/S-807), [fullstop](https://code4rena.com/audits/2026-01-olas/submissions/S-250), [SiderSoner](https://code4rena.com/audits/2026-01-olas/submissions/S-687), [SpicyMeatball](https://code4rena.com/audits/2026-01-olas/submissions/S-568), and [Tupaia](https://code4rena.com/audits/2026-01-olas/submissions/S-1040)*

`autonolas-registries/../contracts/ServiceManager.sol`[#L421](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/ServiceManager.sol#L421)

The `registerAgentsWithSignature` function in the `ServiceManager` contract allows a service owner to register agent instances on behalf of an operator using a signed message.

The signature is computed over the following parameters:

- operator address
- service owner address
- service ID
- agent instance addresses
- agent IDs
- nonce

However, this message does not include any upper bound on the bond amount. As a result, if the service configuration changes after the operator has signed the message (specifically, if the bond requirement increases) the operator may unintentionally lock significantly more funds than originally intended.

Example scenario:

1. Bob creates a service requiring Agent1 instances, each with a bond of 1e18.
2. Alice agrees to participate and signs a message authorizing Bob to register her agent instances.
3. Bob then updates the service and increases the bond to 100e18 per agent. The exact path for Bob is to first terminate the service before any register occurs, then update the service, and activate registrations again.
4. Bob uses Alice’s original signature to register her agents with the updated bond amounts, locking 100x more funds than she intended.
5. Alice’s excess funds remain locked and unavailable until the service is terminated.

This issue occurs because the signed message lacks a reference to the bond amounts, giving the service owner unilateral control over the financial implications of a previously signed authorization.

The absence of a maximum bond parameter in the signed message enables a service owner to increase the required bond after a signature has been issued, then reuse the original signature to register the operator’s agents. This can lead to operators having large amounts of tokens bonded without their consent. These funds remain locked until the service is terminated, which is decided solely by the service’s owner.

#### Recommended mitigation steps

Include a new parameter in the signed message that defines the maximum acceptable bond per agent instance. This value should be used in both the signature hash and enforced during execution to prevent unintended over-bonding.

---


## [H-10] Token Callback Reentrancy

Final report: [F-397](https://code4rena.com/audits/2026-01-olas/submissions/F-397)

*Found by [v12](https://v12.zellic.io)*

- `autonolas-registries/../contracts/staking/StakingBase.sol`[#L540](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/staking/StakingBase.sol#L540)
- `autonolas-registries/../contracts/staking/StakingBase.sol`[#L929](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/staking/StakingBase.sol#L929)
- `autonolas-registries/../contracts/ServiceManager.sol`[#L126](https://github.com/valory-xyz/autonolas-registries/blob/be1057a5e37f17f26b13c41311fe0e8e40259484/contracts/ServiceManager.sol#L126)

#### Checks-Effects-Interactions violation in StakingBase: virtual `_transfer` allows reentrancy and balance desynchronization

**Targets**

- \_claim (StakingBase)
- \_withdraw (StakingBase)
- *claim/*withdraw (StakingBase)

**Description**

The StakingBase contract violates the checks-effects-interactions (CEI) pattern in its claim/withdraw flow by performing external interactions through an overridable internal function \_transfer(…) before persisting updated balances to storage. \_claim zeroes per-service rewards and calls internal \_withdraw, which computes a local updatedBalance and issues transfers by calling the internal virtual \_transfer for each receiver. Because \_transfer is abstract/virtual and the implementation may perform external calls or invoke token callbacks, a malicious receiver or token can re-enter the contract during these transfers. The contract only writes the final updatedBalance to storage after all transfers complete, so any reentrant withdrawal occurring during the external call window will observe stale stored balances and can pass checks multiple times. When control returns to the outer \_withdraw, it overwrites storage with a stale balance derived before the reentrant deduction, desynchronizing stored accounting from actual token holdings and enabling theft.

**Root cause**

Violation of checks-effects-interactions plus unsafe use of an overridable/external-facing transfer hook. The contract computes and uses a local updatedBalance while performing potentially reentrant external interactions via an internal virtual \_transfer, and only writes the persistent balance after those interactions complete. There is no reentrancy guard and the abstract/virtual \_transfer can trigger external callbacks (e.g., token hooks, receiver fallback), enabling reentrant entry into claim/withdraw logic.

**Impact**

High — An attacker who can act as a payment receiver or controls a malicious token contract can reenter claim/withdraw during \_transfer and cause overlapping withdrawals that individually pass checks but cumulatively drain more tokens than the contract’s stored balance should allow. This can result in: complete or partial draining of contract-held funds, corruption/desynchronization of internal accounting, and loss of user funds. The attack requires the attacker to be a recipient (or control a recipient/token hook) and to have other claimable rewards to trigger reentrancy, but these are realistic in staking/reward systems.

#### Unsafe external call ordering in ServiceManager.create allows reentrant token-utility interaction via onERC721Received

**Targets**

- create (ServiceManager)

**Description**

ServiceManager.create performs an external call to serviceRegistry.create (which may safe-mint an ERC721) before completing or protecting subsequent cross-contract work (calling the token-utility). The safe-mint can invoke the recipient’s onERC721Received callback while serviceRegistry.create is still executing. Because ServiceManager does not persist state or use a reentrancy guard around these interactions, a malicious recipient can run arbitrary code during the callback and invoke token-utility.createWithToken or re-enter ServiceManager, causing ordering races and inconsistent state.

**Root cause**

Improper ordering of external interactions and lack of reentrancy protection. The contract calls an untrusted external contract (serviceRegistry.create) that can synchronously call back into user-controlled code (via ERC721Receiver hook) before the manager completes or secures the subsequent critical operation (createWithToken). No persistent state updates or a reentrancy guard are used to prevent reentrant or out-of-order calls to the token-utility or manager functions.

**Impact**

High (context-dependent). An attacker who controls the recipient/serviceOwner (or otherwise triggers code during the registry’s safeMint) can: (1) call token-utility.createWithToken prematurely or with manipulated inputs, (2) re-enter ServiceManager to create ordering races (leading to double registrations, skipped initializations, or corrupted invariants), or (3) produce inconsistent token/registry state. The exploitability and severity depend on access controls in the token-utility: if createWithToken is publicly callable, the issue is directly exploitable (high); if restricted, the impact may be lower but ordering/invariant violations remain possible.

---


## [H-11] cumulativePrice is corrupted when price updates are rejected

Final report: [F-461](https://code4rena.com/audits/2026-01-olas/submissions/F-461)

*Submitted by [santipu\_](https://code4rena.com/audits/2026-01-olas/submissions/S-1068), also found by [coinsspor](https://code4rena.com/audits/2026-01-olas/submissions/S-121), [rox\_k](https://code4rena.com/audits/2026-01-olas/submissions/S-809), [Silvermist](https://code4rena.com/audits/2026-01-olas/submissions/S-217), [StrangerMontana](https://code4rena.com/audits/2026-01-olas/submissions/S-1207), [sunnyshrma](https://code4rena.com/audits/2026-01-olas/submissions/S-1107), and [taronsung](https://code4rena.com/audits/2026-01-olas/submissions/S-1026)*

`autonolas-tokenomics/../contracts/oracles/BalancerPriceOracle.sol`[#L109](https://github.com/valory-xyz/autonolas-tokenomics/blob/bbec5ac12721a62672fb7a5ffba5c40f5a46d8cb/contracts/oracles/BalancerPriceOracle.sol#L109)

The `BalancerPriceOracle` contract updates `cumulativePrice` before checking whether the price deviation exceeds `maxSlippage`. When the slippage check fails and the update is rejected, the function returns `false` but the `cumulativePrice` has already been permanently modified. This corrupts the TWAP calculation, causing it to diverge from the expected value.

The root cause is the ordering of operations in `updatePrice()`:

```
    function updatePrice() public returns (bool) {
        // ...

        // Update cumulative price with the previous average over the elapsed time
>>      snapshot.cumulativePrice += snapshot.averagePrice * elapsedTime;

        // Update the average price to reflect the current price
        uint256 averagePrice = (snapshot.cumulativePrice + (currentPrice * elapsedTime)) /
            ((snapshot.cumulativePrice / snapshot.averagePrice) + elapsedTime);

        // Check if price deviation is too high
        if (currentPrice < averagePrice - (averagePrice * maxSlippage / 100) ||
            currentPrice > averagePrice + (averagePrice * maxSlippage / 100))
        {
>>          return false;
        }

        // ...
    }
```

When the function returns `false`:

- `snapshot.cumulativePrice` has been increased
- `snapshot.averagePrice` remains unchanged (old value)
- `snapshot.lastUpdated` remains unchanged (old timestamp)

**Example Scenario**

1. Initial state:

   - `cumulativePrice = 10,000`
   - `averagePrice = 100`
   - `lastUpdated = T₀`
2. After 100 seconds, someone calls `updatePrice()` with a price that exceeds slippage:

   - `elapsedTime = 100`
   - `currentPrice = 200` (exceeds `maxSlippage`, let’s say 10%)
   - `cumulativePrice = 10,000 + (100 × 100) = 20,000` ✗ (modified!)
   - Slippage check fails → returns `false`
   - `averagePrice` stays at 100
   - `lastUpdated` stays at T₀
3. After another 100 seconds, legitimate update at price 105:

   - `elapsedTime = 200` (time since T₀, not 100!)
   - `cumulativePrice = 20,000 + (100 × 200) = 40,000`

The problem: The `cumulativePrice` is now 40,000, but it should only be 30,000 if the rejected update hadn’t corrupted it:

- Correct: `10,000 + (100 × 200) = 30,000`
- Actual: `20,000 + (100 × 200) = 40,000`

The cumulative price has an extra 10,000 from the rejected update. This error persists and affects all future TWAP calculations.

**Impact**

The corrupted `cumulativePrice` causes `validatePrice()` to compute an incorrect TWAP:

1. Denial of Service: The skewed TWAP may fall outside the acceptable slippage range from the current spot price, causing `validatePrice()` to incorrectly return false for legitimate operations.
2. Sandwich Attacks: When the corrupted TWAP happens to align with a manipulated spot price, attackers can exploit `BuyBackBurner` and `LiquidityManagerOptimism` by sandwiching transactions that should have been rejected.

The severity compounds over time as multiple rejected updates each add erroneous values to `cumulativePrice`.

#### Recommended mitigation steps

Move the slippage check before updating `cumulativePrice`, or use a local variable for the calculation and only persist to storage after validation passes.

---


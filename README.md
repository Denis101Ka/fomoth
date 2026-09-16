# FOMOTH

**A second brain for your Solana memecoin trading. Paste a wallet, see what you fumbled.**

Every tracker shows you dry PnL for taxes. FOMOTH computes the number nobody else does: how much
you left on the table by selling before the top. It reads your trades off the chain, marks every
sell against the peak that came after it, grades the habits that cost you, and coaches you from
your own history with worked, per-token examples.

It reads your public wallet, never a key. It shows its work.

## Architecture

The compute-heavy pass is written in **C++**; the data, orchestration and the web layer are in
**Python**. The two talk over a tiny process boundary, and the Python side falls back to a pure
implementation when the native core is not built, so the project works with or without a compiler.

```
 wallet ─▶ Python (Solana Tracker / price data) ─▶ trades + daily candles
                                                        │
                                                        ▼
                                        C++ core (core/):  the regret engine
                                        suffix-max of daily highs + a binary
                                        search per sell → fumble, peak_mult
                                                        │
                                                        ▼
                        Python report + coach ─▶ JSON ─▶ web/ demo page
```

- **`core/` — C++17 engine.** The regret engine (`regret.cpp`) values every sell against the
  highest price the token reached afterward:
  `fumble = tokens_sold * max(0, peak_high_after_sell - price_at_sell)`, computed with a suffix-max
  over the daily highs and a binary search per sell so it stays fast over a full trade history.
  `coach.cpp` derives expectancy, payoff, win rate and the median hold times. Shipped as a static
  library, a CLI (`fumble`) and its own unit tests.
- **`fomoth/` — Python package.** The Solana Tracker client, price history, trade derivation from
  balance deltas, the report builder, the coach copy and a stdlib-only web server.
- **`fomoth/native.py` — the bridge.** Serialises the inputs, runs the `fumble` binary and parses
  its JSON; falls back to `fomoth/regret.py` when the binary is absent.
- **`web/` — the demo page** that renders a report (not part of the engine).

## Build the core

Needs a C++17 compiler and CMake.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure   # C++ unit tests
```

or just `scripts/build.sh`. The Python layer discovers `build/core/fumble` automatically.

The `fumble` CLI reads a wallet's sells and daily candles from stdin and prints the regret report
as JSON, so it is usable on its own:

```bash
printf '1\nTKN 3 2\n0 2 1\n86400 10 3\n172800 5 4\n0 100\n172800 50\n' | ./build/core/fumble
# {"total_fumble":950,"priced":1,"tokens":[{"mint":"TKN","sold_tokens":150,"fumble_usd":950,...}]}
```

## Run it

```bash
python -m fomoth <wallet-address>          # CLI report
SOLANATRACKER_KEY=... python -m fomoth.server 8090   # web server, then open localhost:8090
```

## How it reads a trade

FOMOTH does not decode any DEX. For each transaction it looks at how the balances moved: a memecoin
up and SOL down is a buy, a memecoin down and SOL in is a sell. That one rule works across pump.fun,
Raydium and Jupiter because they all end in the same balance change. The method is in
[`fomoth/trades.py`](fomoth/trades.py), and the maths is documented, not hidden.

## Layout

```
core/            C++17 engine: regret + coach, CLI, unit tests, CMake
fomoth/          Python: reader, prices, trades, report, coach, server, native bridge
web/             demo page (rendered report)
scripts/         build.sh, run.sh
.github/         CI: builds the core, runs ctest and the Python↔C++ bridge end to end
```

## License

MIT. See [LICENSE](LICENSE).

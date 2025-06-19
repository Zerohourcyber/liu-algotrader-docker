# liu-algotrader-docker

This repository provides a Docker-based setup for running Liu Algo Trader and
helper scripts.  The `engine-wrapper/fix_it_bot.py` tool can modify
`liu_samples/tradeplan.toml` by injecting a data block and a sample strategy.

If you want to restore the original trade plan, copy the clean sample provided
in `liu_samples/tradeplan.sample.toml` back to `tradeplan.toml`:

```bash
cp liu_samples/tradeplan.sample.toml liu_samples/tradeplan.toml
```


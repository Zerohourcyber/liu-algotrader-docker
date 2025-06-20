-- add_backtests.sql
CREATE TABLE IF NOT EXISTS backtests (
    batch_id   TEXT            PRIMARY KEY,
    run_at     TIMESTAMPTZ     NOT NULL DEFAULT now(),
    symbols    TEXT[]          NOT NULL,
    win_rate   DOUBLE PRECISION NOT NULL,
    net_profit NUMERIC         NOT NULL
);

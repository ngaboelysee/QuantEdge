"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

import { getTrade } from "../lib/api";
import StatCard from "../components/StatCard";

const CandleChart = dynamic(
  () => import("../components/CandleChart"),
  { ssr: false }
);

const PAIRS = [
  "EURUSD",
  "GBPUSD",
  "USDJPY",
  "USDCHF",
  "USDCAD",
  "AUDUSD",
  "NZDUSD",
  "XAUUSD",
];

export default function Page() {
  const [pair, setPair] = useState("EURUSD");
  const [balance, setBalance] = useState(1000);
  const [risk, setRisk] = useState(2);

  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const [history, setHistory] = useState<any[]>([]);

  async function analyze() {
    setLoading(true);

    try {
      const res = await getTrade(pair, balance, risk);
      setData(res);

      const trade = {
        pair,
        signal: res.signal.direction,
        confidence: res.signal.confidence,
        balance,
        risk,
        time: new Date().toLocaleTimeString(),
      };

      const updated = [trade, ...history];
      setHistory(updated);

      localStorage.setItem("trade_history", JSON.stringify(updated));

    } catch (err) {
      console.log(err);
    }

    setLoading(false);
  }

  useEffect(() => {
    const saved = localStorage.getItem("trade_history");
    if (saved) setHistory(JSON.parse(saved));
  }, []);

  const direction = data?.signal?.direction;

  const signalColor =
    direction === "BUY"
      ? "text-green-400"
      : direction === "SELL"
      ? "text-red-400"
      : "text-gray-400";

  // 🔥 SAFE FORMATTER (TradingView-style display)
  const formatPrice = (value: any) => {
    if (value === null || value === undefined) return "-";
    return Number(value).toFixed(
      pair === "USDJPY" ? 3 : pair === "XAUUSD" ? 2 : 5
    );
  };

  return (
    <div className="min-h-screen px-4 lg:px-8 py-6">

      {/* HEADER */}
      <div className="max-w-[1600px] mx-auto mb-8">
        <h1 className="text-4xl font-black">
          FX Intelligence Terminal
        </h1>
        <p className="text-gray-500">
          AI-powered trading engine + real market visualization
        </p>
      </div>

      {/* GRID */}
      <div className="max-w-[1600px] mx-auto grid grid-cols-1 xl:grid-cols-12 gap-6">

        {/* LEFT PANEL */}
        <div className="xl:col-span-3 glass p-6">

          <p className="text-gray-400 text-sm mb-4">
            Trade Setup
          </p>

          <select
            className="input mb-4"
            value={pair}
            onChange={(e) => setPair(e.target.value)}
          >
            {PAIRS.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </select>

          <input
            className="input mb-4"
            type="number"
            value={balance}
            onChange={(e) => setBalance(Number(e.target.value))}
          />

          <input
            className="input mb-6"
            type="number"
            value={risk}
            onChange={(e) => setRisk(Number(e.target.value))}
          />

          <button
            onClick={analyze}
            className="primary-btn w-full py-3 rounded-xl font-bold"
          >
            {loading ? "Analyzing..." : "Analyze Trade"}
          </button>
        </div>

        {/* RIGHT PANEL */}
        <div className="xl:col-span-9 space-y-6">

          {/* SIGNAL + CHART */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

            {/* SIGNAL */}
            <div className="xl:col-span-2 glass p-6">

              {!data ? (
                <div className="text-gray-500">
                  Run analysis to generate signal
                </div>
              ) : (
                <>
                  <h2 className={`text-6xl font-black ${signalColor}`}>
                    {direction}
                  </h2>

                  <p className="text-gray-400 mt-3">
                    Confidence: {data.signal.confidence}%
                  </p>

                  <div className="w-full h-2 bg-black/40 rounded mt-4">
                    <div
                      className="h-2 bg-green-400 rounded"
                      style={{
                        width: `${data.signal.confidence}%`,
                      }}
                    />
                  </div>
                </>
              )}
            </div>

            {/* CHART */}
            <div className="glass p-4">
              {!data ? (
                <div className="text-gray-500">
                  Chart appears after analysis
                </div>
              ) : (
                <CandleChart />
              )}
            </div>
          </div>

          {/* STATS + TRADE LEVELS */}
          {data && (
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">

              <StatCard
                title="Sentiment"
                value={data.news?.sentiment || "N/A"}
                color="yellow"
              />

              <StatCard
                title="Volatility"
                value={data.volatility?.regime || "N/A"}
                color="blue"
              />

              <StatCard
                title="Lot Size"
                value={data.risk.lot_size}
                color="green"
              />

              <StatCard
                title="Risk"
                value={`$${data.risk.risk_amount}`}
                color="red"
              />

              {/* 🔥 CLEAN TRADINGVIEW LEVELS */}
              <StatCard
                title="Entry"
                value={formatPrice(data.risk.entry_price)}
                color="white"
              />

              <StatCard
                title="Stop Loss"
                value={formatPrice(data.risk.stop_loss_price)}
                color="red"
              />

              <StatCard
                title="Take Profit"
                value={formatPrice(data.risk.take_profit_price)}
                color="green"
              />

              <StatCard
                title="RR Ratio"
                value={`1:${data.risk.risk_reward_ratio}`}
                color="yellow"
              />

            </div>
          )}

          {/* MONTE CARLO */}
          {data && (
            <div className="glass p-6">

              <h2 className="text-2xl font-black mb-4">
                Monte Carlo Simulation
              </h2>

              <div className="grid grid-cols-3 gap-4">

                <div>
                  <p className="text-gray-400">Expected</p>
                  <p className="text-2xl font-bold">
                    ${data.simulation.expected}
                  </p>
                </div>

                <div>
                  <p className="text-gray-400">Best</p>
                  <p className="text-2xl font-bold text-green-400">
                    ${data.simulation.best}
                  </p>
                </div>

                <div>
                  <p className="text-gray-400">Worst</p>
                  <p className="text-2xl font-bold text-red-400">
                    ${data.simulation.worst}
                  </p>
                </div>

              </div>
            </div>
          )}

          {/* HISTORY */}
          {history.length > 0 && (
            <div className="glass p-6">

              <h2 className="text-xl font-bold mb-4">
                Trade History
              </h2>

              <div className="space-y-2 text-sm">

                {history.map((t, i) => (
                  <div
                    key={i}
                    className="flex justify-between border-b border-white/5 py-2"
                  >
                    <span>{t.pair}</span>
                    <span>{t.signal}</span>
                    <span>{t.confidence}%</span>
                    <span className="text-gray-500">
                      {t.time}
                    </span>
                  </div>
                ))}

              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

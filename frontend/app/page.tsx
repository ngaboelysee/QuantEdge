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
  const [error, setError] = useState<string | null>(null);

  const [history, setHistory] = useState<any[]>([]);

  async function analyze() {
    setLoading(true);
    setError(null);

    try {
      const res = await getTrade(pair, balance, risk);
      setData(res);

      const trade = {
        pair,
        signal: res?.signal?.direction || "N/A",
        confidence: res?.signal?.confidence || 0,
        balance,
        risk,
        time: new Date().toLocaleTimeString(),
      };

      const updated = [trade, ...history];
      setHistory(updated);

      localStorage.setItem("trade_history", JSON.stringify(updated));
    } catch (err: any) {
      console.log(err);
      setError("Failed to fetch trade data");
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

        {error && (
          <p className="text-red-400 mt-2">{error}</p>
        )}
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
            disabled={loading}
            className="primary-btn w-full py-3 rounded-xl font-bold"
          >
            {loading ? "Analyzing..." : "Analyze Trade"}
          </button>
        </div>

        {/* RIGHT PANEL */}
        <div className="xl:col-span-9 space-y-6">

          {/* SIGNAL */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

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
                </>
              )}
            </div>

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

          {/* STATS */}
          {data && (
            <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">

              <StatCard title="Pair" value={data.pair} />
              <StatCard title="Price" value={data.price} />
              <StatCard title="Direction" value={data.signal.direction} />
              <StatCard title="Confidence" value={`${data.signal.confidence}%`} />
              <StatCard title="Score" value={data.signal.score} />

              <StatCard title="Risk" value={`$${data.risk.risk_amount}`} />
              <StatCard title="Lot Size" value={data.risk.lot_size} />
              <StatCard title="RR" value={`1:${data.risk.risk_reward_ratio}`} />
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

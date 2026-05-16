"use client";

import dynamic from "next/dynamic";

const Chart = dynamic(
  () => import("react-apexcharts"),
  { ssr: false }
);

export default function CandleChart() {

  const series = [
    {
      data: [
        {
          x: new Date(2026, 4, 1),
          y: [1.1200, 1.1280, 1.1150, 1.1250],
        },
        {
          x: new Date(2026, 4, 2),
          y: [1.1250, 1.1320, 1.1200, 1.1290],
        },
        {
          x: new Date(2026, 4, 3),
          y: [1.1290, 1.1380, 1.1240, 1.1360],
        },
        {
          x: new Date(2026, 4, 4),
          y: [1.1360, 1.1400, 1.1280, 1.1310],
        },
        {
          x: new Date(2026, 4, 5),
          y: [1.1310, 1.1450, 1.1300, 1.1420],
        },
        {
          x: new Date(2026, 4, 6),
          y: [1.1420, 1.1500, 1.1380, 1.1470],
        },
      ],
    },
  ];

  const options: any = {
    chart: {
      type: "candlestick",
      toolbar: {
        show: false,
      },
      background: "transparent",
    },

    theme: {
      mode: "dark",
    },

    grid: {
      borderColor: "rgba(255,255,255,0.06)",
    },

    xaxis: {
      type: "datetime",

      labels: {
        style: {
          colors: "#666",
        },
      },
    },

    yaxis: {
      tooltip: {
        enabled: true,
      },

      labels: {
        style: {
          colors: "#666",
        },
      },
    },

    plotOptions: {
      candlestick: {
        colors: {
          upward: "#22c55e",
          downward: "#ef4444",
        },
      },
    },
  };

  return (
    <div className="w-full h-full">

      <Chart
        options={options}
        series={series}
        type="candlestick"
        height={320}
      />

    </div>
  );
}
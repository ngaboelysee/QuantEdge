type Props = {
  title: string;
  value: any;
  color?: "green" | "red" | "yellow" | "blue" | "white";
};

export default function StatCard({
  title,
  value,
  color = "white",
}: Props) {

  const colorMap = {
    green: {
      text: "text-green-400",
      glow: "shadow-[0_0_25px_rgba(34,197,94,0.15)]",
      border: "border-green-500/20",
    },

    red: {
      text: "text-red-400",
      glow: "shadow-[0_0_25px_rgba(239,68,68,0.15)]",
      border: "border-red-500/20",
    },

    yellow: {
      text: "text-yellow-400",
      glow: "shadow-[0_0_25px_rgba(250,204,21,0.15)]",
      border: "border-yellow-500/20",
    },

    blue: {
      text: "text-sky-400",
      glow: "shadow-[0_0_25px_rgba(56,189,248,0.15)]",
      border: "border-sky-500/20",
    },

    white: {
      text: "text-white",
      glow: "",
      border: "border-white/10",
    },
  };

  return (
    <div
      className={`
        glass
        hover-float
        p-5
        border
        ${colorMap[color].border}
        ${colorMap[color].glow}
      `}
    >

      {/* HEADER */}
      <div className="flex items-center justify-between">

        <p className="text-[11px] uppercase tracking-[0.25em] text-gray-500">
          {title}
        </p>

        {/* LIVE DOT */}
        <div className={`
          w-2 h-2 rounded-full animate-pulse
          ${
            color === "green"
              ? "bg-green-400"
              : color === "red"
              ? "bg-red-400"
              : color === "yellow"
              ? "bg-yellow-400"
              : color === "blue"
              ? "bg-sky-400"
              : "bg-white"
          }
        `} />

      </div>

      {/* VALUE */}
      <div className="mt-5">

        <h2 className={`
          text-2xl lg:text-3xl font-black tracking-tight
          ${colorMap[color].text}
        `}>
          {value}
        </h2>

      </div>

      {/* BOTTOM GLOW LINE */}
      <div className="mt-5">

        <div className="w-full h-[1px] bg-white/5 relative overflow-hidden rounded-full">

          <div
            className={`
              absolute left-0 top-0 h-full w-1/2 rounded-full blur-sm
              ${
                color === "green"
                  ? "bg-green-400"
                  : color === "red"
                  ? "bg-red-400"
                  : color === "yellow"
                  ? "bg-yellow-400"
                  : color === "blue"
                  ? "bg-sky-400"
                  : "bg-white"
              }
            `}
          />

        </div>

      </div>

    </div>
  );
}
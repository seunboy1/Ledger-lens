import React from "react";

/** A plain, modern phone: dark bezel, dynamic island, soft realistic shadow. */
export const SCREEN_W = 390;
export const SCREEN_H = 844;
const BEZEL = 13;

export function Device({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        position: "relative",
        width: SCREEN_W + BEZEL * 2,
        height: SCREEN_H + BEZEL * 2,
        borderRadius: 64,
        background: "linear-gradient(145deg, #2a2e36, #0c0e12 45%, #1b1e24)",
        padding: BEZEL,
        boxShadow:
          "0 0 0 1.5px rgba(255,255,255,0.08) inset, 0 60px 120px rgba(5,10,40,0.55), 0 18px 40px rgba(5,10,40,0.45)",
      }}
    >
      {/* side buttons */}
      <div style={{ position: "absolute", left: -3, top: 170, width: 3, height: 60, borderRadius: 2, background: "#1b1e24" }} />
      <div style={{ position: "absolute", right: -3, top: 210, width: 3, height: 90, borderRadius: 2, background: "#1b1e24" }} />
      <div
        style={{
          position: "relative",
          width: SCREEN_W,
          height: SCREEN_H,
          borderRadius: 52,
          overflow: "hidden",
          background: "var(--bg)",
        }}
      >
        {children}
        <div style={{ position: "absolute", top: 11, left: "50%", width: 120, height: 34, marginLeft: -60, borderRadius: 20, background: "#000", zIndex: 50 }} />
      </div>
    </div>
  );
}

export function StatusBar() {
  return (
    <div className="relative z-20 flex items-center justify-between bg-bg px-8 pt-4 text-[15px] font-semibold" style={{ height: 54 }}>
      <span>9:41</span>
      <span className="flex items-center gap-1.5" aria-hidden>
        <span className="flex items-end gap-[2px]">
          {[5, 8, 11, 14].map((h) => (
            <span key={h} className="w-[3px] rounded-[1px] bg-ink" style={{ height: h }} />
          ))}
        </span>
        <span className="ml-1 inline-block h-[12px] w-[24px] rounded-[4px] border-[1.5px] border-ink p-[1.5px]">
          <span className="block h-full w-[70%] rounded-[2px] bg-ink" />
        </span>
      </span>
    </div>
  );
}

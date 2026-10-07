import { loadFont as loadGeist } from "@remotion/google-fonts/Geist";
import { loadFont as loadGeistMono } from "@remotion/google-fonts/GeistMono";

// Same type and colour tokens as the Ledger Lens app (frontend/src/app/globals.css).
export const sans = loadGeist("normal", { weights: ["400", "500", "600", "700", "800", "900"], subsets: ["latin"] }).fontFamily;
export const mono = loadGeistMono("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;

export const c = {
  stage: "#0b0d11",
  stageGlow: "rgba(43, 69, 212, 0.38)",
  white: "#f4f5f7",
  dim: "rgba(244, 245, 247, 0.62)",
  // Product UI (light theme of the app)
  bg: "#f4f5f7",
  surface: "#fcfcfd",
  sunken: "#eef0f3",
  border: "#e1e4e9",
  ink: "#0f1217",
  inkSoft: "#454c58",
  muted: "#646b77",
  accent: "#2b45d4",
  accentSoft: "#e9ecfd",
  credit: "#0c6e46",
  creditSoft: "#e4f3ec",
  debit: "#b4361c",
  debitSoft: "#fbebe6",
  error: "#9b2c4a",
  errorSoft: "#f8e6ec",
};

export const FPS = 30;

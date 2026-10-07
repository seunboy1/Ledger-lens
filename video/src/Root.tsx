import React from "react";
import { Composition } from "remotion";
import { FPS } from "./theme";
import { LedgerLensVideo, TOTAL_FRAMES } from "./Video";
import { PHONE_TOTAL, PhoneReel } from "./phone/PhoneReel";
import { PROMO_TOTAL, PromoReel } from "./promo/PromoReel";

export function Root() {
  return (
    <>
      {/* 9:16 for Reels, Shorts and TikTok */}
      <Composition id="LedgerLensReel" component={LedgerLensVideo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1080} height={1920} />
      {/* Promo built from brag-output/promo/PROMPT.md, 18s vertical */}
      <Composition id="LedgerLensPromo" component={PromoReel} durationInFrames={PROMO_TOTAL} fps={FPS} width={1080} height={1920} />
      {/* Phone promo, 18s vertical */}
      <Composition id="LedgerLensPhone" component={PhoneReel} durationInFrames={PHONE_TOTAL} fps={FPS} width={1080} height={1920} />
      {/* 4:5 for the LinkedIn feed */}
      <Composition id="LedgerLensFeed" component={LedgerLensVideo} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1080} height={1350} />
    </>
  );
}

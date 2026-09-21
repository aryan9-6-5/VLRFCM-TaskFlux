import { useEffect, useState } from "react";

// Same palette as the CSS variables in styles.css. Framer Motion interpolates real colour values,
// so the animated SVG needs them in JS as well.
export const palettes = {
  light: {
    paper: "#ECEFED", panel: "#F5F7F6", ink: "#15202B", ink2: "#485663", rule: "#C3CCC9",
    keep: "#2A7654", undo: "#B92F27", build: "#1F5FBF", amber: "#855A00", leave: "#77837F",
    keepBg: "#DAEDE3", undoBg: "#F5DDDA", buildBg: "#DAE5F6", leaveBg: "#E2E6E4", onSolid: "#FFFFFF",
  },
  dark: {
    paper: "#11171D", panel: "#171F27", ink: "#E7EDF1", ink2: "#A2B1BD", rule: "#2B3743",
    keep: "#5FC495", undo: "#F17C71", build: "#82ABF6", amber: "#E4B440", leave: "#7F8C95",
    keepBg: "#173226", undoBg: "#3B1F1C", buildBg: "#192A49", leaveBg: "#212C34", onSolid: "#0E1319",
  },
};

export function usePalette() {
  const q = typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  const [dark, setDark] = useState(q ? q.matches : false);
  useEffect(() => {
    if (!q) return undefined;
    const on = (e) => setDark(e.matches);
    q.addEventListener("change", on);
    return () => q.removeEventListener("change", on);
  }, [q]);
  return palettes[dark ? "dark" : "light"];
}

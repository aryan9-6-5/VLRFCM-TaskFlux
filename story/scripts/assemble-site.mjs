// Assemble the deployable static site in ../site:
//   /              the new story (this build)
//   /classic/      the earlier, detailed story (kept as built; source in story/classic-src)
//   /demo/         the interactive demo (built by `python -m demo.build_demo`)
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const site = resolve(here, "..", "..", "site");
const put = (from, to) => {
  if (!existsSync(from)) { console.warn("missing, skipped:", from); return; }
  mkdirSync(dirname(to), { recursive: true });
  copyFileSync(from, to);
  console.log("wrote", to);
};
put(resolve(here, "..", "dist", "index.html"), resolve(site, "index.html"));
put(resolve(here, "..", "..", "demo", "index.html"), resolve(site, "demo", "index.html"));
if (!existsSync(resolve(site, "classic", "index.html"))) console.warn("site/classic/index.html is missing");

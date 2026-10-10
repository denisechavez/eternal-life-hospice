// Compile the existing Studio with the correct environment's Clerk key.
// The public server protects every dynamic content chunk before delivery.
import { spawnSync } from "node:child_process";
const production = process.argv.includes("--published") || process.env.REPLIT_DEPLOYMENT === "1";
const result = spawnSync("npm", [
  "run", "build", "--prefix", "artifacts/review-design-sandbox", "--",
  "--outDir", "../../website/studio-build", "--manifest",
], {
  stdio: "inherit",
  env: {...process.env, PORT: "21921", BASE_PATH: "/studio/",
    VITE_CLERK_PUBLISHABLE_KEY: process.env.CLERK_PUBLISHABLE_KEY,
    VITE_CLERK_PROXY_URL: production ? "/api/__clerk" : ""},
});
process.exit(result.status ?? 1);

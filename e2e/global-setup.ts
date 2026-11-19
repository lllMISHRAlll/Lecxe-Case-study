import { execFileSync } from "node:child_process";
import path from "node:path";

/** Fresh, seeded and normalised database before every run (local Docker Postgres). */
export default function globalSetup() {
  const backend = path.resolve(__dirname, "../backend");
  execFileSync(path.join(backend, ".venv/bin/python"), ["-m", "scripts.seed_e2e"], {
    cwd: backend,
    stdio: "inherit",
  });
}

#!/usr/bin/env node
import { runNativeCli } from "./native/semantic-decision.mjs";
try {
  process.exitCode = runNativeCli(process.argv.slice(2));
} catch (error) {
  console.error(error.message);
  process.exitCode = 2;
}

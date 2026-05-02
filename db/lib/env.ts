// Load environment variables for the hoisted db/ setup scripts.
//
// The starter has separate .env.local files inside agent-py/ and agent-ts/.
// Whichever runtime the developer set up first will have populated values
// (MONGODB_URI, VOYAGE_API_KEY). Probe both — plus a root .env.local for
// developers who prefer a single shared file — and load the first match.

import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import dotenv from 'dotenv';

const CANDIDATE_PATHS = [
  'agent-py/.env.local',
  'agent-ts/.env.local',
  '.env.local',
];

export function loadEnv(): { source: string } {
  const cwd = process.cwd();
  for (const candidate of CANDIDATE_PATHS) {
    const abs = resolve(cwd, candidate);
    if (existsSync(abs)) {
      dotenv.config({ path: abs });
      return { source: candidate };
    }
  }
  throw new Error(
    `No .env.local found. Looked in (relative to ${cwd}): ` +
      CANDIDATE_PATHS.join(', ') +
      '. Run `pnpm setup` to create one from .env.example.',
  );
}

export function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(
      `Required environment variable ${name} is not set. ` +
        'Check your .env.local file.',
    );
  }
  return value;
}

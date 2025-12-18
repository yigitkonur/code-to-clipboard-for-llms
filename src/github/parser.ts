import { existsSync } from 'node:fs';
import type { GitHubRepo } from '../types/index.js';

const HTTPS_PATTERN = /^https?:\/\/github\.com\/([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?(?:\/tree\/([^/]+))?(?:\/.*)?$/;
const SHORT_URL_PATTERN = /^github\.com\/([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?(?:\/tree\/([^/]+))?(?:\/.*)?$/;
const SSH_PATTERN = /^git@github\.com:([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git)?$/;
const SHORTHAND_PATTERN = /^([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:@([a-zA-Z0-9_./-]+))?$/;

export function parseGitHubUrl(input: string): GitHubRepo | null {
  const trimmed = input.trim();

  // If it's a valid local path that exists, it's not a GitHub URL
  if (existsSync(trimmed)) {
    return null;
  }

  // Pattern 1: Full HTTPS URL
  let match = HTTPS_PATTERN.exec(trimmed);
  if (match) {
    return {
      owner: match[1]!,
      name: match[2]!,
      branch: match[3],
    };
  }

  // Pattern 2: github.com/owner/repo without https
  match = SHORT_URL_PATTERN.exec(trimmed);
  if (match) {
    return {
      owner: match[1]!,
      name: match[2]!,
      branch: match[3],
    };
  }

  // Pattern 3: SSH format git@github.com:owner/repo.git
  match = SSH_PATTERN.exec(trimmed);
  if (match) {
    return {
      owner: match[1]!,
      name: match[2]!,
    };
  }

  // Pattern 4: owner/repo[@branch] shorthand
  match = SHORTHAND_PATTERN.exec(trimmed);
  if (match) {
    const owner = match[1]!;
    const name = match[2]!;
    const branch = match[3];

    // Exclude things that look like relative paths
    if (owner.startsWith('.') || owner.startsWith('-') || owner.startsWith('_')) {
      return null;
    }

    return { owner, name, branch };
  }

  return null;
}

export function getCloneUrl(repo: GitHubRepo): string {
  return `https://github.com/${repo.owner}/${repo.name}.git`;
}

export function getDisplayName(repo: GitHubRepo): string {
  if (repo.branch) {
    return `${repo.owner}/${repo.name}@${repo.branch}`;
  }
  return `${repo.owner}/${repo.name}`;
}

export function getFullName(repo: GitHubRepo): string {
  return `${repo.owner}/${repo.name}`;
}

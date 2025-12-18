import { mkdtempSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { simpleGit } from 'simple-git';
import ora from 'ora';
import type { GitHubRepo } from '../types/index.js';
import { getCloneUrl, getDisplayName } from './parser.js';

const tempDirs: string[] = [];
let cleanupRegistered = false;

function registerCleanup(): void {
  if (!cleanupRegistered) {
    process.on('exit', cleanupAll);
    process.on('SIGINT', () => {
      cleanupAll();
      process.exit(130);
    });
    process.on('SIGTERM', () => {
      cleanupAll();
      process.exit(143);
    });
    cleanupRegistered = true;
  }
}

function cleanupAll(): void {
  for (const dir of tempDirs) {
    try {
      if (existsSync(dir)) {
        rmSync(dir, { recursive: true, force: true });
      }
    } catch {
      // Ignore cleanup errors
    }
  }
}

export async function fetchRepository(repo: GitHubRepo, keepGit = false): Promise<string> {
  registerCleanup();

  const spinner = ora(`Cloning ${getDisplayName(repo)}...`).start();

  // Create temp directory
  const tempDir = mkdtempSync(join(tmpdir(), `repo-to-prompt-${repo.name}-`));
  tempDirs.push(tempDir);

  const clonePath = join(tempDir, repo.name);
  const cloneUrl = getCloneUrl(repo);

  try {
    const git = simpleGit();

    const cloneOptions = ['--depth', '1', '--single-branch'];
    if (repo.branch) {
      cloneOptions.push('--branch', repo.branch);
    }

    await git.clone(cloneUrl, clonePath, cloneOptions);

    // Remove .git directory unless keepGit is true
    if (!keepGit) {
      const gitDir = join(clonePath, '.git');
      if (existsSync(gitDir)) {
        rmSync(gitDir, { recursive: true, force: true });
      }
    }

    spinner.succeed('Cloned to temporary directory');
    return clonePath;
  } catch (error) {
    spinner.fail('Failed to clone repository');

    const message = error instanceof Error ? error.message : String(error);

    if (message.includes('not found') || message.includes('Repository not found')) {
      throw new Error(
        `Repository '${repo.owner}/${repo.name}' not found. ` +
          'Please check the owner/repo name and ensure it\'s public.'
      );
    }

    if (message.includes('Could not find remote branch')) {
      throw new Error(
        `Branch '${repo.branch}' not found in ${repo.owner}/${repo.name}. ` +
          'Please check the branch name.'
      );
    }

    throw new Error(`Failed to clone repository: ${message}`);
  }
}

export function cleanupRepository(path: string): void {
  const index = tempDirs.findIndex((dir) => path.startsWith(dir));
  if (index !== -1) {
    const dir = tempDirs[index]!;
    try {
      if (existsSync(dir)) {
        rmSync(dir, { recursive: true, force: true });
      }
      tempDirs.splice(index, 1);
    } catch {
      // Ignore cleanup errors
    }
  }
}

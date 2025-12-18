import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { execSync } from 'node:child_process';
import ignore, { type Ignore } from 'ignore';

export function loadGitignore(rootDir: string): Ignore | null {
  const gitignorePath = join(rootDir, '.gitignore');
  
  if (!existsSync(gitignorePath)) {
    return null;
  }

  try {
    const content = readFileSync(gitignorePath, 'utf-8');
    const ig = ignore();
    ig.add(content);
    return ig;
  } catch {
    return null;
  }
}

export function getTrackedFiles(rootDir: string): Set<string> | null {
  try {
    // Check if inside git work tree
    execSync('git rev-parse --is-inside-work-tree', {
      cwd: rootDir,
      stdio: 'pipe',
    });

    // Get list of tracked files
    const output = execSync('git ls-files', {
      cwd: rootDir,
      encoding: 'utf-8',
      stdio: 'pipe',
    });

    const files = new Set<string>();
    for (const line of output.split('\n')) {
      const trimmed = line.trim();
      if (trimmed) {
        files.add(trimmed.replace(/\\/g, '/'));
      }
    }

    return files;
  } catch {
    return null;
  }
}

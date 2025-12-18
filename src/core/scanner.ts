import { globby } from 'globby';
import { lstatSync } from 'node:fs';
import { relative } from 'node:path';
import type { ScanConfig } from '../types/index.js';

export interface ScanStats {
  totalScanned: number;
  includedPaths: string[];
}

export async function scanDirectory(config: ScanConfig): Promise<ScanStats> {
  const { rootDir, maxDepth, excludedDirs, excludedPatterns, includedPatterns, includeOnlyMode } = config;

  // Build ignore patterns for globby
  const ignorePatterns: string[] = [
    ...Array.from(excludedDirs).map((dir) => `**/${dir}/**`),
    ...Array.from(excludedPatterns),
  ];

  // Build include patterns
  let patterns: string[];
  if (includeOnlyMode && includedPatterns.size > 0) {
    patterns = Array.from(includedPatterns);
  } else {
    patterns = ['**/*'];
  }

  try {
    const globbyOptions: Parameters<typeof globby>[1] = {
      cwd: rootDir,
      gitignore: config.gitMode !== 'none',
      ignore: ignorePatterns,
      onlyFiles: true,
      followSymbolicLinks: false,
      absolute: true,
      dot: true,
    };

    if (maxDepth !== undefined) {
      globbyOptions.deep = maxDepth;
    }

    const paths = await globby(patterns, globbyOptions);

    // Filter out symlinks and apply additional filters
    const includedPaths: string[] = [];
    let totalScanned = 0;

    for (const absPath of paths) {
      totalScanned++;

      try {
        const stat = lstatSync(absPath);
        if (stat.isSymbolicLink()) {
          continue;
        }

        includedPaths.push(absPath);
      } catch {
        // Skip files we can't stat
      }
    }

    return {
      totalScanned,
      includedPaths,
    };
  } catch (error) {
    throw new Error(`Failed to scan directory: ${error instanceof Error ? error.message : String(error)}`);
  }
}

export function getRelativePath(absPath: string, rootDir: string): string {
  return relative(rootDir, absPath).split('\\').join('/');
}

export function toPosixPath(path: string): string {
  return path.split('\\').join('/');
}

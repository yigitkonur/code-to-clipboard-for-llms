import { readFileSync, statSync, openSync, readSync, closeSync } from 'node:fs';
import { basename, extname, relative } from 'node:path';
import { minimatch } from 'minimatch';
import type { Ignore } from 'ignore';
import type { ScanConfig, FilterResult } from '../types/index.js';
import {
  AlwaysSkip,
  AlwaysInclude,
  ExcludedPatterns,
  DataPatterns,
  ConfigSkip,
} from '../constants/defaults.js';

function getRelPath(absPath: string, rootDir: string): string {
  return relative(rootDir, absPath).split('\\').join('/');
}

export interface FilterRule {
  check(absPath: string, config: ScanConfig): FilterResult;
}

class SkipListRule implements FilterRule {
  check(absPath: string, _config: ScanConfig): FilterResult {
    const name = basename(absPath);
    if (AlwaysSkip.has(name)) {
      return { passes: false, reason: `In skip list: ${name}` };
    }
    return { passes: true, reason: '' };
  }
}

class DirectoryRule implements FilterRule {
  check(absPath: string, config: ScanConfig): FilterResult {
    const relPath = getRelPath(absPath, config.rootDir);
    const parts = relPath.split('/');
    
    // Check all parent directories (not the file itself)
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i]!;
      
      // Check if in excluded dirs
      if (config.excludedDirs.has(part)) {
        return { passes: false, reason: `In excluded dir: ${part}` };
      }
      
      // Check if dir matches any excluded pattern
      for (const pattern of config.excludedPatterns) {
        if (minimatch(part, pattern)) {
          return { passes: false, reason: `Dir matches pattern: ${pattern}` };
        }
      }
    }
    
    return { passes: true, reason: '' };
  }
}

class PatternRule implements FilterRule {
  check(absPath: string, config: ScanConfig): FilterResult {
    const name = basename(absPath);
    const relPath = getRelPath(absPath, config.rootDir);
    
    // Check excludes first
    for (const pattern of config.excludedPatterns) {
      if (minimatch(name, pattern) || minimatch(relPath, pattern)) {
        return { passes: false, reason: `Matches exclude: ${pattern}` };
      }
    }
    
    // Include-only mode
    if (config.includeOnlyMode && config.includedPatterns.size > 0) {
      for (const pattern of config.includedPatterns) {
        if (minimatch(name, pattern) || minimatch(relPath, pattern) || minimatch(`**/${name}`, pattern)) {
          return { passes: true, reason: '' };
        }
      }
      return { passes: false, reason: 'No include pattern matched' };
    }
    
    return { passes: true, reason: '' };
  }
}

class SizeRule implements FilterRule {
  check(absPath: string, config: ScanConfig): FilterResult {
    if (config.maxSizeBytes === undefined) {
      return { passes: true, reason: '' };
    }
    try {
      const stat = statSync(absPath);
      if (stat.size > config.maxSizeBytes) {
        return { passes: false, reason: `Too large: ${stat.size.toLocaleString()} > ${config.maxSizeBytes.toLocaleString()}` };
      }
    } catch {
      return { passes: false, reason: 'Cannot stat file' };
    }
    return { passes: true, reason: '' };
  }
}

class BinaryRule implements FilterRule {
  check(absPath: string, config: ScanConfig): FilterResult {
    if (config.includeBinary) {
      return { passes: true, reason: '' };
    }
    try {
      const buffer = Buffer.alloc(8192);
      const fd = openSync(absPath, 'r');
      const bytesRead = readSync(fd, buffer, 0, 8192, 0);
      closeSync(fd);

      for (let i = 0; i < bytesRead; i++) {
        if (buffer[i] === 0) {
          return { passes: false, reason: 'Binary file' };
        }
      }
    } catch {
      return { passes: false, reason: 'Cannot read file' };
    }
    return { passes: true, reason: '' };
  }
}

class DefaultPatternRule implements FilterRule {
  check(absPath: string, config: ScanConfig): FilterResult {
    const name = basename(absPath);
    const ext = extname(absPath).toLowerCase();
    const relPath = getRelPath(absPath, config.rootDir);

    // Always include special files
    if (AlwaysInclude.has(name)) {
      return { passes: true, reason: '' };
    }

    // Check type overrides
    const override = config.typeOverrides.get(ext);
    if (override === true) {
      return { passes: true, reason: '' };
    }

    // Check if explicitly included
    for (const pattern of config.includedPatterns) {
      if (minimatch(name, pattern) || minimatch(relPath, pattern)) {
        return { passes: true, reason: '' };
      }
    }

    // Check default excluded patterns
    for (const pattern of ExcludedPatterns) {
      if (minimatch(name, pattern)) {
        return { passes: false, reason: `Default exclude: ${pattern}` };
      }
    }

    // Check data patterns
    for (const pattern of DataPatterns) {
      if (minimatch(name, pattern)) {
        return { passes: false, reason: `Data format excluded: ${pattern}` };
      }
    }

    // Check config skip
    for (const pattern of ConfigSkip) {
      if (minimatch(name, pattern)) {
        return { passes: false, reason: `Config file excluded: ${pattern}` };
      }
    }

    return { passes: true, reason: '' };
  }
}

class GitignoreRule implements FilterRule {
  private matcher: Ignore | null;

  constructor(matcher: Ignore | null) {
    this.matcher = matcher;
  }

  check(absPath: string, config: ScanConfig): FilterResult {
    if (!this.matcher || config.gitMode === 'none') {
      return { passes: true, reason: '' };
    }

    const relPath = getRelPath(absPath, config.rootDir);
    
    if (this.matcher.ignores(relPath)) {
      // Check if explicitly included despite gitignore
      const name = basename(absPath);
      for (const pattern of config.includedPatterns) {
        if (minimatch(name, pattern) || minimatch(relPath, pattern)) {
          return { passes: true, reason: '' };
        }
      }
      return { passes: false, reason: 'Matched .gitignore' };
    }
    
    return { passes: true, reason: '' };
  }
}

class GitTrackingRule implements FilterRule {
  private tracked: Set<string> | null;

  constructor(tracked: Set<string> | null) {
    this.tracked = tracked;
  }

  check(absPath: string, config: ScanConfig): FilterResult {
    if (!this.tracked || config.gitMode !== 'full') {
      return { passes: true, reason: '' };
    }

    const relPath = getRelPath(absPath, config.rootDir);
    
    if (!this.tracked.has(relPath)) {
      // Allow special files
      const name = basename(absPath);
      if (AlwaysInclude.has(name)) {
        return { passes: true, reason: '' };
      }
      for (const pattern of config.includedPatterns) {
        if (minimatch(name, pattern)) {
          return { passes: true, reason: '' };
        }
      }
      return { passes: false, reason: 'Not tracked by git' };
    }
    
    return { passes: true, reason: '' };
  }
}

class CharLimitRule implements FilterRule {
  check(absPath: string, config: ScanConfig): FilterResult {
    if (!config.skipLargeFiles || !config.maxFileChars) {
      return { passes: true, reason: '' };
    }
    try {
      const content = readFileSync(absPath, 'utf-8');
      if (content.length > config.maxFileChars) {
        return { passes: false, reason: `Too many chars: ${content.length.toLocaleString()}` };
      }
    } catch {
      return { passes: false, reason: 'Cannot read for char check' };
    }
    return { passes: true, reason: '' };
  }
}

export class FileFilter {
  private rules: FilterRule[];
  private config: ScanConfig;

  constructor(
    config: ScanConfig,
    gitignoreMatcher: Ignore | null = null,
    trackedFiles: Set<string> | null = null
  ) {
    this.config = config;
    this.rules = this.buildRules(gitignoreMatcher, trackedFiles);
  }

  private buildRules(
    gitignoreMatcher: Ignore | null,
    trackedFiles: Set<string> | null
  ): FilterRule[] {
    const rules: FilterRule[] = [
      new SkipListRule(),
      new DirectoryRule(),
    ];

    // Git rules
    if (this.config.gitMode === 'gitignore' || this.config.gitMode === 'full') {
      rules.push(new GitignoreRule(gitignoreMatcher));
    }

    if (this.config.gitMode === 'full') {
      rules.push(new GitTrackingRule(trackedFiles));
    }

    rules.push(
      new PatternRule(),
      new SizeRule(),
      new BinaryRule(),
      new DefaultPatternRule(),
      new CharLimitRule()
    );

    return rules;
  }

  shouldInclude(absPath: string): FilterResult {
    for (const rule of this.rules) {
      const result = rule.check(absPath, this.config);
      if (!result.passes) {
        return result;
      }
    }
    return { passes: true, reason: 'Passed all filters' };
  }
}

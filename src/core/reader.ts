import { readFileSync, statSync } from 'node:fs';
import { basename, extname } from 'node:path';
import type { FileInfo, ScanConfig } from '../types/index.js';
import { getLanguage } from '../constants/languages.js';
import { getRelativePath } from './scanner.js';

export function readFiles(paths: string[], config: ScanConfig): FileInfo[] {
  const results: FileInfo[] = [];

  for (const absPath of paths) {
    try {
      let content = readFileSync(absPath, 'utf-8');
      const originalLen = content.length;
      let truncated = false;

      // Truncate if needed
      if (config.truncateLargeFiles && config.maxFileChars && originalLen > config.maxFileChars) {
        content = content.slice(0, config.maxFileChars);
        content += `\n\n... [TRUNCATED: ${originalLen.toLocaleString()} → ${config.maxFileChars.toLocaleString()} chars]`;
        truncated = true;
      }

      const lines = content ? content.split('\n').length : 0;
      const name = basename(absPath);
      const ext = extname(absPath);
      const language = getLanguage(name, ext);

      const stat = statSync(absPath);

      results.push({
        relativePath: getRelativePath(absPath, config.rootDir),
        absolutePath: absPath,
        content,
        sizeBytes: stat.size,
        lineCount: lines,
        charCount: content.length,
        language,
        percentage: 0, // Calculated later
        wasTruncated: truncated,
      });
    } catch (error) {
      const relPath = getRelativePath(absPath, config.rootDir);
      results.push({
        relativePath: relPath,
        absolutePath: absPath,
        content: `# Error reading file: ${error instanceof Error ? error.message : String(error)}`,
        sizeBytes: 0,
        lineCount: 0,
        charCount: 0,
        language: 'text',
        percentage: 0,
        wasTruncated: false,
      });
    }
  }

  return results;
}

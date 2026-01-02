import type { ScanResult, FileInfo, TreeNode } from '../types/index.js';
import { getDisplayName, getFullName } from '../github/parser.js';
import { GLYPH_CHILD, GLYPH_LAST, GLYPH_PIPE, GLYPH_SPACE } from '../constants/defaults.js';
import { homedir } from 'node:os';

const LINE_NUMBERS_NOTE = '> Note: Line numbers are for reference only—not part of the source code.';

export function formatPreview(result: ScanResult): string {
  const lines: string[] = ['# 📁 Preview - Files to be Included', ''];

  const totalLines = result.files.reduce((sum, f) => sum + f.lineCount, 0);
  const totalChars = result.files.reduce((sum, f) => sum + f.charCount, 0);

  lines.push(`**Files:** ${result.files.length.toLocaleString()}`);
  lines.push(`**Lines:** ${totalLines.toLocaleString()}`);
  lines.push(`**Characters:** ${totalChars.toLocaleString()}`);
  lines.push('');
  lines.push('## File List');
  lines.push('```');

  for (const f of result.files) {
    lines.push(`  ${f.relativePath} (${f.lineCount.toLocaleString()}L, ${f.charCount.toLocaleString()}C)`);
  }

  lines.push('```');
  return lines.join('\n');
}

export function formatSummary(result: ScanResult): string {
  const sourceLine = result.config.githubRepo
    ? `*GitHub: ${getDisplayName(result.config.githubRepo)}*`
    : `*Directory: ${formatPath(result.config.rootDir)}*`;

  const lines: string[] = ['# 📁 Project Structure', sourceLine, ''];

  const tech = result.techStack.size > 0 ? [...result.techStack].join(', ') : 'Unknown';
  lines.push(`**Stack:** ${tech}`);
  lines.push(`**Files:** ${result.files.length.toLocaleString()} of ${result.totalScanned.toLocaleString()} scanned`);
  lines.push('');

  lines.push('## Project Tree');
  lines.push('```');
  lines.push('.');
  formatTree(result.tree, lines, '');
  lines.push('```');

  return lines.join('\n');
}

export function formatFull(result: ScanResult): string {
  const sourceLine = result.config.githubRepo
    ? `*GitHub: [\`${getDisplayName(result.config.githubRepo)}\`](https://github.com/${getFullName(result.config.githubRepo)})*`
    : `*Directory: \`${formatPath(result.config.rootDir)}\`*`;

  const lines: string[] = ['# 📁 Project Context', sourceLine, ''];

  const totalLines = result.files.reduce((sum, f) => sum + f.lineCount, 0);
  const totalChars = result.files.reduce((sum, f) => sum + f.charCount, 0);
  const tech = result.techStack.size > 0 ? [...result.techStack].join(', ') : 'Unknown';

  lines.push('## Overview');
  lines.push(`- **Stack:** ${tech}`);
  lines.push(`- **Files:** ${result.files.length.toLocaleString()}`);
  lines.push(`- **Lines:** ${totalLines.toLocaleString()}`);
  lines.push(`- **Size:** ~${(totalChars / 1024).toFixed(1)} KB`);
  lines.push('');
  lines.push('## Structure');
  lines.push('```');
  lines.push('.');
  formatTree(result.tree, lines, '');
  lines.push('```');
  lines.push('');
  lines.push('---');
  lines.push('');
  lines.push('## Source Files');
  lines.push('');

  for (const f of result.files) {
    const header = getFileHeader(f);
    lines.push(header);
    lines.push(`*${f.lineCount.toLocaleString()} lines • ${f.charCount.toLocaleString()} chars*`);
    lines.push('');
    if (result.config.lineNumbers) {
      lines.push(LINE_NUMBERS_NOTE);
      lines.push('');
    }
    lines.push(`\`\`\`${f.language}`);
    const content = result.config.lineNumbers ? addLineNumbers(f.content) : f.content;
    lines.push(content);
    lines.push('```');
    lines.push('');
  }

  return lines.join('\n').trim();
}

function formatPath(path: string): string {
  const home = homedir();
  if (path.startsWith(home)) {
    return `~${path.slice(home.length)}`;
  }
  return path;
}

function formatTree(nodes: TreeNode[], lines: string[], prefix: string): void {
  for (let i = 0; i < nodes.length; i++) {
    const node = nodes[i]!;
    const isLast = i === nodes.length - 1;
    const connector = isLast ? GLYPH_LAST : GLYPH_CHILD;

    if (!node.included && node.children.length === 0) {
      continue;
    }

    const icon = node.isDir ? '📁' : '📄';
    let line = `${prefix}${connector} ${icon} ${node.name}`;

    if (!node.isDir && node.included) {
      line += ` (${node.lines.toLocaleString()}L)`;
    }

    lines.push(line);

    if (node.children.length > 0) {
      const childPrefix = prefix + (isLast ? GLYPH_SPACE : GLYPH_PIPE);
      formatTree(node.children, lines, childPrefix);
    }
  }
}

function addLineNumbers(content: string): string {
  const lines = content.split('\n');
  const width = String(lines.length).length;
  return lines
    .map((line, i) => `${String(i + 1).padStart(width)}\t${line}`)
    .join('\n');
}

function getFileHeader(f: FileInfo): string {
  const name = f.relativePath.split('/').pop()?.toLowerCase() ?? '';
  const ext = name.includes('.') ? `.${name.split('.').pop()}` : '';

  const icons: Record<string, string> = {
    readme: '📖',
    '.py': '🐍',
    '.go': '🐹',
    '.rs': '🦀',
    '.ts': '📘',
    '.tsx': '📘',
    '.js': '📒',
    '.jsx': '📒',
    '.json': '⚙️',
    '.md': '📝',
  };

  let icon = '📄';
  for (const [key, emoji] of Object.entries(icons)) {
    if (name.includes(key) || ext === key) {
      icon = emoji;
      break;
    }
  }

  return `### ${icon} \`${f.relativePath}\``;
}

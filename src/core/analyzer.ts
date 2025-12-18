import type { FileInfo, ScanResult, ScanConfig, TreeNode } from '../types/index.js';
import { TECH_STACK_MAPPING } from '../constants/languages.js';
import { AlwaysInclude } from '../constants/defaults.js';
import { extname, dirname } from 'node:path';

export function analyzeProject(
  files: FileInfo[],
  config: ScanConfig,
  totalScanned: number,
  duration: number
): ScanResult {
  // Calculate percentages
  const totalChars = files.reduce((sum, f) => sum + f.charCount, 0);
  for (const f of files) {
    f.percentage = totalChars > 0 ? (f.charCount / totalChars) * 100 : 0;
  }

  // Sort files
  const sortedFiles = sortFiles(files, config);

  // Detect tech stack
  const techStack = detectTechStack(sortedFiles);

  // Find key directories
  const keyDirs = findKeyDirectories(sortedFiles);

  // Build tree
  const tree = buildTree(sortedFiles);

  return {
    config,
    files: sortedFiles,
    tree,
    totalScanned,
    techStack,
    keyDirs,
    duration,
  };
}

function sortFiles(files: FileInfo[], config: ScanConfig): FileInfo[] {
  if (config.sortAlphabetically) {
    return [...files].sort((a, b) => a.relativePath.toLowerCase().localeCompare(b.relativePath.toLowerCase()));
  }

  // Check for numbered files
  const numberedCount = files.filter((f) => /^\d+_/.test(f.relativePath.split('/').pop() ?? '')).length;
  if (numberedCount > files.length / 2) {
    return sortNumbered(files);
  }

  return sortByImportance(files);
}

function sortNumbered(files: FileInfo[]): FileInfo[] {
  return [...files].sort((a, b) => {
    const aName = a.relativePath.split('/').pop() ?? '';
    const bName = b.relativePath.split('/').pop() ?? '';
    const aMatch = /^(\d+)_/.exec(aName);
    const bMatch = /^(\d+)_/.exec(bName);

    if (aMatch && bMatch) {
      return parseInt(aMatch[1]!, 10) - parseInt(bMatch[1]!, 10);
    }
    if (aMatch) return -1;
    if (bMatch) return 1;
    return aName.toLowerCase().localeCompare(bName.toLowerCase());
  });
}

function sortByImportance(files: FileInfo[]): FileInfo[] {
  return [...files].sort((a, b) => {
    const aName = a.relativePath.split('/').pop() ?? '';
    const bName = b.relativePath.split('/').pop() ?? '';
    const aDepth = a.relativePath.split('/').length;
    const bDepth = b.relativePath.split('/').length;

    // README first
    if (aName.toLowerCase().startsWith('readme')) return -1;
    if (bName.toLowerCase().startsWith('readme')) return 1;

    // AlwaysInclude files next
    if (AlwaysInclude.has(aName) && !AlwaysInclude.has(bName)) return -1;
    if (AlwaysInclude.has(bName) && !AlwaysInclude.has(aName)) return 1;

    // Then by depth
    if (aDepth !== bDepth) return aDepth - bDepth;

    return aName.toLowerCase().localeCompare(bName.toLowerCase());
  });
}

function detectTechStack(files: FileInfo[]): Set<string> {
  const tech = new Set<string>();

  for (const file of files) {
    const ext = extname(file.relativePath).toLowerCase();
    for (const [techName, extensions] of Object.entries(TECH_STACK_MAPPING)) {
      if (extensions.includes(ext)) {
        tech.add(techName);
        break;
      }
    }
  }

  return tech;
}

function findKeyDirectories(files: FileInfo[]): string[] {
  const counts = new Map<string, number>();

  for (const file of files) {
    const dir = dirname(file.relativePath);
    if (dir !== '.') {
      counts.set(dir, (counts.get(dir) ?? 0) + 1);
    }
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([dir]) => dir);
}

function buildTree(files: FileInfo[]): TreeNode[] {
  const fileMap = new Map<string, FileInfo>();
  for (const f of files) {
    fileMap.set(f.relativePath, f);
  }

  // Collect all paths including parent directories
  const allPaths = new Set<string>();
  for (const f of files) {
    allPaths.add(f.relativePath);
    const parts = f.relativePath.split('/');
    for (let i = 1; i < parts.length; i++) {
      allPaths.add(parts.slice(0, i).join('/'));
    }
  }

  // Build nested structure
  type TreeDict = { [key: string]: TreeDict };
  const treeDict: TreeDict = {};

  for (const path of [...allPaths].sort()) {
    const parts = path.split('/');
    let current = treeDict;
    for (const part of parts) {
      if (!(part in current)) {
        current[part] = {};
      }
      current = current[part]!;
    }
  }

  // Convert to TreeNode
  function convert(dict: TreeDict, currentPath: string): TreeNode[] {
    const nodes: TreeNode[] = [];

    for (const name of Object.keys(dict).sort()) {
      const childDict = dict[name]!;
      const path = currentPath ? `${currentPath}/${name}` : name;
      const isDir = Object.keys(childDict).length > 0;

      if (isDir) {
        const children = convert(childDict, path);
        const included = children.some((c) => c.included);
        nodes.push({
          name,
          path,
          isDir: true,
          included,
          children,
          lines: 0,
          chars: 0,
          percentage: 0,
        });
      } else {
        const file = fileMap.get(path);
        const included = file !== undefined;
        nodes.push({
          name,
          path,
          isDir: false,
          included,
          children: [],
          lines: file?.lineCount ?? 0,
          chars: file?.charCount ?? 0,
          percentage: file?.percentage ?? 0,
        });
      }
    }

    return nodes;
  }

  return convert(treeDict, '');
}

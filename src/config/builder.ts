import type { CLIOptions, ScanConfig, GitHubRepo, GitMode, OutputMode } from '../types/index.js';
import { ExcludedDirs, Defaults } from '../constants/defaults.js';

export function parseSize(sizeStr: string): number | undefined {
  if (!sizeStr) return undefined;

  const normalized = sizeStr.trim().toLowerCase();
  if (normalized === '0') return undefined;

  const multipliers: Record<string, number> = {
    k: 1024,
    m: 1024 ** 2,
    g: 1024 ** 3,
  };

  const lastChar = normalized.slice(-1);
  if (lastChar in multipliers) {
    const num = parseInt(normalized.slice(0, -1), 10);
    if (!isNaN(num)) {
      return num * multipliers[lastChar]!;
    }
  }

  const num = parseInt(normalized, 10);
  return isNaN(num) ? undefined : num;
}

export function buildConfig(
  rootDir: string,
  options: CLIOptions,
  githubRepo?: GitHubRepo
): ScanConfig {
  // Determine output mode
  let outputMode: OutputMode;
  if (options.output) {
    outputMode = 'file';
  } else if (options.stdout) {
    outputMode = 'stdout';
  } else if (options.noClipboard) {
    outputMode = 'stdout';
  } else {
    outputMode = 'clipboard';
  }

  // Determine git mode
  let gitMode: GitMode;
  if (options.noGitignore) {
    gitMode = 'none';
  } else if (options.useGit) {
    gitMode = 'full';
  } else {
    gitMode = 'gitignore';
  }

  // Build excluded patterns
  const excludedPatterns = new Set<string>();
  for (const pattern of options.exclude) {
    excludedPatterns.add(pattern);
  }
  for (const ext of options.excludeExtension) {
    const normalized = ext.startsWith('.') ? ext : `.${ext}`;
    excludedPatterns.add(`*${normalized}`);
  }

  // Build included patterns
  const includedPatterns = new Set<string>();
  for (const pattern of options.include) {
    includedPatterns.add(pattern);
  }
  for (const ext of options.includeExtension) {
    const normalized = ext.startsWith('.') ? ext : `.${ext}`;
    includedPatterns.add(`*${normalized}`);
  }

  // Build type overrides
  const typeOverrides = new Map<string, boolean>([
    ['.json', options.includeJson],
    ['.jsonc', options.includeJson],
    ['.yaml', options.includeYaml],
    ['.yml', options.includeYaml],
    ['.xml', options.includeXml],
    ['.html', options.includeHtml],
    ['.htm', options.includeHtml],
    ['.css', options.includeCss],
    ['.sql', options.includeSql],
    ['.csv', options.includeCsv],
    ['.tsv', options.includeCsv],
    ['.md', options.includeMarkdown],
    ['.markdown', options.includeMarkdown],
    ['.rst', options.includeMarkdown],
  ]);

  return {
    rootDir,
    gitMode,
    outputMode,
    outputFile: options.output,
    outputFormat: options.format,
    maxSizeBytes: parseSize(options.maxSize),
    maxFileChars: options.maxFileChars,
    maxDepth: options.maxDepth,
    includeBinary: options.includeBinary,
    sortAlphabetically: options.sortAlpha,
    includeOnlyMode: options.includeOnly,
    truncateLargeFiles: options.truncateLargeFiles,
    skipLargeFiles: options.skipLargeFiles,
    excludedDirs: new Set(ExcludedDirs),
    excludedPatterns,
    includedPatterns,
    typeOverrides,
    githubRepo,
  };
}

export function getDefaultOptions(): CLIOptions {
  return {
    stdout: false,
    noClipboard: false,
    format: 'markdown',
    exclude: [],
    include: [],
    includeOnly: false,
    excludeExtension: [],
    includeExtension: [],
    maxSize: Defaults.MAX_SIZE,
    includeBinary: false,
    noGitignore: false,
    gitignoreOnly: false,
    useGit: false,
    includeJson: false,
    includeYaml: false,
    includeXml: false,
    includeHtml: false,
    includeCss: false,
    includeSql: false,
    includeCsv: false,
    includeMarkdown: true,
    maxFileChars: Defaults.MAX_FILE_CHARS,
    skipLargeFiles: false,
    truncateLargeFiles: false,
    preview: false,
    dryRun: false,
    interactive: false,
    showStats: false,
    sortAlpha: false,
    checkUpdates: false,
  };
}

export type GitMode = 'none' | 'gitignore' | 'full';
export type OutputMode = 'clipboard' | 'file' | 'stdout';
export type OutputFormat = 'markdown' | 'json';

export interface GitHubRepo {
  owner: string;
  name: string;
  branch?: string | undefined;
}

export interface ScanConfig {
  rootDir: string;
  gitMode: GitMode;
  outputMode: OutputMode;
  outputFile?: string | undefined;
  outputFormat: OutputFormat;

  maxSizeBytes?: number | undefined;
  maxFileChars: number;
  maxDepth?: number | undefined;

  includeBinary: boolean;
  sortAlphabetically: boolean;
  lineNumbers: boolean;
  includeOnlyMode: boolean;
  truncateLargeFiles: boolean;
  skipLargeFiles: boolean;

  excludedDirs: Set<string>;
  excludedPatterns: Set<string>;
  includedPatterns: Set<string>;

  typeOverrides: Map<string, boolean>;

  githubRepo?: GitHubRepo | undefined;
}

export interface FileInfo {
  relativePath: string;
  absolutePath: string;
  content: string;
  sizeBytes: number;
  lineCount: number;
  charCount: number;
  language: string;
  percentage: number;
  wasTruncated: boolean;
}

export interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  included: boolean;
  children: TreeNode[];
  lines: number;
  chars: number;
  percentage: number;
}

export interface ScanResult {
  config: ScanConfig;
  files: FileInfo[];
  tree: TreeNode[];
  totalScanned: number;
  techStack: Set<string>;
  keyDirs: string[];
  duration: number;
}

export interface CLIOptions {
  output?: string | undefined;
  stdout: boolean;
  noClipboard: boolean;
  format: OutputFormat;

  exclude: string[];
  include: string[];
  includeOnly: boolean;
  excludeExtension: string[];
  includeExtension: string[];

  maxSize: string;
  maxDepth?: number | undefined;
  includeBinary: boolean;

  noGitignore: boolean;
  gitignoreOnly: boolean;
  useGit: boolean;

  includeJson: boolean;
  includeYaml: boolean;
  includeXml: boolean;
  includeHtml: boolean;
  includeCss: boolean;
  includeSql: boolean;
  includeCsv: boolean;
  includeMarkdown: boolean;

  maxFileChars: number;
  skipLargeFiles: boolean;
  truncateLargeFiles: boolean;

  preview: boolean;
  dryRun: boolean;
  interactive: boolean;
  showStats: boolean;
  sortAlpha: boolean;
  lineNumbers: boolean;

  checkUpdates: boolean;
}

export interface FilterResult {
  passes: boolean;
  reason: string;
}

import { Command } from 'commander';
import { existsSync } from 'node:fs';
import { basename, resolve } from 'node:path';
import chalk from 'chalk';
import ora from 'ora';

import type { CLIOptions, GitHubRepo } from './types/index.js';
import { parseGitHubUrl } from './github/parser.js';
import { fetchRepository } from './github/fetcher.js';
import { buildConfig, getDefaultOptions } from './config/builder.js';
import { scanDirectory } from './core/scanner.js';
import { FileFilter } from './core/filter.js';
import { loadGitignore, getTrackedFiles } from './core/git.js';
import { readFiles } from './core/reader.js';
import { analyzeProject } from './core/analyzer.js';
import { formatPreview, formatSummary, formatFull } from './formatters/markdown.js';
import { formatJson } from './formatters/json.js';
import { writeOutput } from './output/writer.js';
import { runInteractiveConfig } from './interactive/wizard.js';
import { ensureFirstRunSetup } from './interactive/firstRun.js';
import { Defaults } from './constants/defaults.js';
import { checkForUpdates } from './version.js';

const VERSION = '1.1.0';

const program = new Command();

program
  .name('repo-to-prompt')
  .description('Gather project context for LLMs - intelligently scan repositories and format for AI consumption')
  .version(VERSION)
  .argument('[root_dir]', 'Root project directory or GitHub repo (owner/repo, URL)', '.')

  // Output options
  .option('-o, --output <file>', 'Write to file')
  .option('--stdout', 'Print to stdout')
  .option('--no-clipboard', "Don't copy to clipboard")
  .option('--format <format>', 'Output format (markdown, json)', 'markdown')

  // Filtering
  .option('--exclude <pattern...>', 'Glob pattern to exclude')
  .option('--include <pattern...>', 'Glob pattern to include')
  .option('--include-only', 'Include ONLY matching --include patterns')
  .option('--exclude-extension <ext...>', 'Extension to exclude')
  .option('--include-extension <ext...>', 'Extension to include')
  .option('--max-size <size>', 'Max file size (default: 2M)', Defaults.MAX_SIZE)
  .option('--max-depth <n>', 'Max directory depth')
  .option('--include-binary', 'Include binary files')

  // Git options
  .option('--no-gitignore', 'Ignore .gitignore completely')
  .option('--gitignore-only', 'Use .gitignore only (default)')
  .option('--use-git', 'Use full git integration (tracked files only)')

  // File types
  .option('--include-json', 'Include JSON files')
  .option('--include-yaml', 'Include YAML files')
  .option('--include-xml', 'Include XML files')
  .option('--include-html', 'Include HTML files')
  .option('--include-css', 'Include CSS files')
  .option('--include-sql', 'Include SQL files')
  .option('--include-csv', 'Include CSV files')
  .option('--include-markdown', 'Include Markdown files')

  // Large files
  .option('--max-file-chars <n>', 'Max chars per file', String(Defaults.MAX_FILE_CHARS))
  .option('--skip-large-files', 'Skip files exceeding char limit')
  .option('--truncate-large-files', 'Truncate large files')

  // Features
  .option('--preview', 'Preview files without content')
  .option('--dry-run', 'Simulate without output')
  .option('--interactive', 'Interactive configuration')
  .option('--show-stats', 'Show stats alongside output')
  .option('--sort-alpha', 'Sort files alphabetically')
  .option('-n, --line-numbers', 'Add line numbers to code output (like cat -n)')

  // Meta
  .option('--check-updates', 'Check for updates')

  .action(async (rootDirArg: string, opts: Record<string, unknown>) => {
    try {
      await run(rootDirArg, opts);
    } catch (error) {
      console.error(chalk.red(`❌ Error: ${error instanceof Error ? error.message : String(error)}`));
      process.exit(1);
    }
  });

async function run(rootDirArg: string, opts: Record<string, unknown>): Promise<void> {
  // Parse options into CLIOptions
  let options: CLIOptions = {
    ...getDefaultOptions(),
    output: opts.output as string | undefined,
    stdout: Boolean(opts.stdout),
    noClipboard: opts.clipboard === false,
    format: (opts.format as 'markdown' | 'json') ?? 'markdown',
    exclude: (opts.exclude as string[]) ?? [],
    include: (opts.include as string[]) ?? [],
    includeOnly: Boolean(opts.includeOnly),
    excludeExtension: (opts.excludeExtension as string[]) ?? [],
    includeExtension: (opts.includeExtension as string[]) ?? [],
    maxSize: (opts.maxSize as string) ?? Defaults.MAX_SIZE,
    maxDepth: opts.maxDepth ? parseInt(String(opts.maxDepth), 10) : undefined,
    includeBinary: Boolean(opts.includeBinary),
    noGitignore: opts.gitignore === false,
    gitignoreOnly: Boolean(opts.gitignoreOnly),
    useGit: Boolean(opts.useGit),
    includeJson: Boolean(opts.includeJson),
    includeYaml: Boolean(opts.includeYaml),
    includeXml: Boolean(opts.includeXml),
    includeHtml: Boolean(opts.includeHtml),
    includeCss: Boolean(opts.includeCss),
    includeSql: Boolean(opts.includeSql),
    includeCsv: Boolean(opts.includeCsv),
    includeMarkdown: Boolean(opts.includeMarkdown),
    maxFileChars: opts.maxFileChars ? parseInt(String(opts.maxFileChars), 10) : Defaults.MAX_FILE_CHARS,
    skipLargeFiles: Boolean(opts.skipLargeFiles),
    truncateLargeFiles: Boolean(opts.truncateLargeFiles),
    preview: Boolean(opts.preview),
    dryRun: Boolean(opts.dryRun),
    interactive: Boolean(opts.interactive),
    showStats: Boolean(opts.showStats),
    sortAlpha: Boolean(opts.sortAlpha),
    lineNumbers: Boolean(opts.lineNumbers),
    checkUpdates: Boolean(opts.checkUpdates),
  };

  // Check for updates
  if (options.checkUpdates) {
    console.log('🔍 Checking for updates...');
    const update = await checkForUpdates();
    if (update) {
      console.log(`🚀 Update available: v${update.current} → v${update.latest}`);
      console.log(`   Run: ${update.command}`);
    } else {
      console.log(chalk.green('✅ You\'re running the latest version!'));
    }
    return;
  }

  const invokedName = basename(process.argv[1] ?? '') || 'repo-to-prompt';
  await ensureFirstRunSetup(invokedName === 'cli.js' ? 'repo-to-prompt' : invokedName);

  // Check if input is a GitHub URL/reference
  let rootDir = rootDirArg;
  let githubRepo: GitHubRepo | undefined;

  const parsedRepo = parseGitHubUrl(rootDirArg);
  if (parsedRepo) {
    githubRepo = parsedRepo;
    rootDir = await fetchRepository(parsedRepo);
  } else {
    rootDir = resolve(rootDirArg);
  }

  // Interactive mode
  if (options.interactive) {
    const result = await runInteractiveConfig(options, rootDir);
    options = result.options;
    rootDir = result.rootDir;
  }

  // Validate root directory
  if (!existsSync(rootDir)) {
    throw new Error(`Directory not found: ${rootDir}`);
  }

  const startTime = performance.now();

  // Build configuration
  const config = buildConfig(rootDir, options, githubRepo);

  // Load git data
  let gitignoreMatcher = null;
  let trackedFiles = null;

  if (config.gitMode === 'gitignore' || config.gitMode === 'full') {
    gitignoreMatcher = loadGitignore(config.rootDir);
  }

  if (config.gitMode === 'full') {
    trackedFiles = getTrackedFiles(config.rootDir);
  }

  // Scan directory
  const spinner = ora('Scanning files...').start();
  const scanResult = await scanDirectory(config);

  // Apply filters
  const filter = new FileFilter(config, gitignoreMatcher, trackedFiles);
  const filteredPaths = scanResult.includedPaths.filter((path) => {
    const result = filter.shouldInclude(path);
    return result.passes;
  });

  if (filteredPaths.length === 0) {
    spinner.warn('No files matched the filters');
    if (!options.dryRun) {
      if (config.outputMode === 'stdout') {
        console.log('# No files included');
      }
    }
    return;
  }

  spinner.text = `Reading ${filteredPaths.length} files...`;

  // Read files
  const files = readFiles(filteredPaths, config);

  spinner.text = 'Analyzing project...';

  // Analyze
  const duration = (performance.now() - startTime) / 1000;
  const result = analyzeProject(files, config, scanResult.totalScanned, duration);

  spinner.succeed(`Found ${result.files.length} files`);

  // Format output
  let content: string;
  let summary: string;

  if (config.outputFormat === 'json') {
    content = formatJson(result, true);
    summary = formatJson(result, false);
  } else {
    if (options.preview) {
      content = formatPreview(result);
      summary = content;
    } else {
      content = formatFull(result);
      summary = formatSummary(result);
    }
  }

  // Handle dry run
  if (options.dryRun) {
    console.log(chalk.cyan('\n🔍 Dry Run Complete'));
    console.log(`   Files: ${result.files.length.toLocaleString()}`);
    console.log(`   Output size: ${content.length.toLocaleString()} chars`);
    return;
  }

  // Show stats if requested
  if (options.showStats) {
    console.error(summary);
  }

  // Write output
  const success = await writeOutput(content, summary, config);
  process.exit(success ? 0 : 1);
}

program.parse();

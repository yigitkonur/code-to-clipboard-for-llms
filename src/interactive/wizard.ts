import { input, select, checkbox } from '@inquirer/prompts';
import type { CLIOptions } from '../types/index.js';

export async function runInteractiveConfig(options: CLIOptions, rootDir: string): Promise<{ options: CLIOptions; rootDir: string }> {
  console.log('\n🔧 Interactive Configuration\n');
  console.log('Press Enter to accept defaults, or type new value.\n');

  // Root directory
  const newRootDir = await input({
    message: 'Root directory',
    default: rootDir,
  });

  // Output format
  const format = await select({
    message: 'Output format',
    choices: [
      { name: 'Markdown', value: 'markdown' as const },
      { name: 'JSON', value: 'json' as const },
    ],
    default: options.format,
  });

  // Include file types
  const fileTypes = await checkbox({
    message: 'Include additional file types',
    choices: [
      { name: 'JSON files', value: 'json', checked: options.includeJson },
      { name: 'YAML files', value: 'yaml', checked: options.includeYaml },
      { name: 'Markdown files', value: 'markdown', checked: options.includeMarkdown },
      { name: 'HTML files', value: 'html', checked: options.includeHtml },
      { name: 'CSS files', value: 'css', checked: options.includeCss },
      { name: 'SQL files', value: 'sql', checked: options.includeSql },
    ],
  });

  // Max depth
  const maxDepthStr = await input({
    message: 'Max directory depth (empty for unlimited)',
    default: options.maxDepth?.toString() ?? '',
  });
  const maxDepth = maxDepthStr ? parseInt(maxDepthStr, 10) : undefined;

  // Output destination
  const destination = await select({
    message: 'Output destination',
    choices: [
      { name: 'Clipboard', value: 'clipboard' },
      { name: 'File', value: 'file' },
      { name: 'Stdout', value: 'stdout' },
    ],
    default: 'clipboard',
  });

  let outputFile: string | undefined;
  if (destination === 'file') {
    outputFile = await input({
      message: 'Output file path',
      default: 'context.md',
    });
  }

  console.log('\n✅ Configuration complete!\n');

  return {
    rootDir: newRootDir,
    options: {
      ...options,
      format,
      includeJson: fileTypes.includes('json'),
      includeYaml: fileTypes.includes('yaml'),
      includeMarkdown: fileTypes.includes('markdown'),
      includeHtml: fileTypes.includes('html'),
      includeCss: fileTypes.includes('css'),
      includeSql: fileTypes.includes('sql'),
      maxDepth: isNaN(maxDepth ?? NaN) ? undefined : maxDepth,
      output: outputFile,
      stdout: destination === 'stdout',
      noClipboard: destination !== 'clipboard',
    },
  };
}

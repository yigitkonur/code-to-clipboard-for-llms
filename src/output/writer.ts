import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import clipboard from 'clipboardy';
import chalk from 'chalk';
import type { ScanConfig } from '../types/index.js';

export async function writeOutput(
  content: string,
  summary: string,
  config: ScanConfig
): Promise<boolean> {
  switch (config.outputMode) {
    case 'file':
      return writeToFile(content, summary, config.outputFile);
    case 'stdout':
      return writeToStdout(content);
    case 'clipboard':
      return writeToClipboard(content, summary);
    default:
      return writeToStdout(content);
  }
}

function writeToFile(content: string, summary: string, outputFile?: string): boolean {
  if (!outputFile) {
    console.error(chalk.red('❌ No output file specified'));
    return false;
  }

  try {
    mkdirSync(dirname(outputFile), { recursive: true });
    writeFileSync(outputFile, content, 'utf-8');
    console.error(summary);
    console.error(chalk.green(`\n✅ Written to ${outputFile}`));
    return true;
  } catch (error) {
    console.error(chalk.red(`❌ Error writing file: ${error instanceof Error ? error.message : String(error)}`));
    return false;
  }
}

function writeToStdout(content: string): boolean {
  try {
    console.log(content);
    return true;
  } catch (error) {
    console.error(chalk.red(`❌ Error writing to stdout: ${error instanceof Error ? error.message : String(error)}`));
    return false;
  }
}

async function writeToClipboard(content: string, summary: string): Promise<boolean> {
  try {
    console.error(summary);
    await clipboard.write(content);
    console.error(chalk.green(`\n✅ ${content.length.toLocaleString()} chars copied to clipboard`));
    return true;
  } catch (error) {
    console.error(chalk.yellow('⚠️ Clipboard not available, printing to stdout'));
    return writeToStdout(content);
  }
}

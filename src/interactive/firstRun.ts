import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { basename, join } from 'node:path';
import { confirm, input, select } from '@inquirer/prompts';

interface FirstRunConfig {
  completed: boolean;
  preferredAlias?: string | undefined;
}

function getConfigPath(): string {
  const dir = join(homedir(), '.config', 'repo-to-prompt');
  return join(dir, 'config.json');
}

function readConfig(): FirstRunConfig | null {
  const path = getConfigPath();
  if (!existsSync(path)) return null;
  try {
    const raw = readFileSync(path, 'utf-8');
    const parsed = JSON.parse(raw) as unknown;
    if (typeof parsed !== 'object' || parsed === null) return null;
    const cfg = parsed as Partial<FirstRunConfig>;
    const preferredAlias = typeof cfg.preferredAlias === 'string' ? cfg.preferredAlias : undefined;
    return preferredAlias === undefined
      ? { completed: Boolean(cfg.completed) }
      : { completed: Boolean(cfg.completed), preferredAlias };
  } catch {
    return null;
  }
}

function writeConfig(cfg: FirstRunConfig): void {
  const path = getConfigPath();
  const dir = join(homedir(), '.config', 'repo-to-prompt');
  mkdirSync(dir, { recursive: true });
  writeFileSync(path, JSON.stringify(cfg, null, 2), 'utf-8');
}

function detectShellRc(): { shellName: string; rcPath: string } | null {
  const shell = process.env.SHELL;
  if (!shell) return null;

  const name = basename(shell);

  if (name === 'zsh') return { shellName: 'zsh', rcPath: join(homedir(), '.zshrc') };
  if (name === 'bash') return { shellName: 'bash', rcPath: join(homedir(), '.bashrc') };
  if (name === 'fish') return { shellName: 'fish', rcPath: join(homedir(), '.config', 'fish', 'config.fish') };

  return null;
}

function aliasLine(shellName: string, aliasName: string): string {
  if (shellName === 'fish') {
    return `alias ${aliasName}='repo-to-prompt'`;
  }
  return `alias ${aliasName}="repo-to-prompt"`;
}

function fileContains(path: string, needle: string): boolean {
  if (!existsSync(path)) return false;
  try {
    const content = readFileSync(path, 'utf-8');
    return content.includes(needle);
  } catch {
    return false;
  }
}

export async function ensureFirstRunSetup(commandName: string): Promise<void> {
  if (process.env.REPO_TO_PROMPT_SKIP_SETUP === '1') return;
  if (!process.stdin.isTTY) return;

  const existing = readConfig();
  if (existing?.completed) return;

  console.log('\n🧩 First-time setup\n');

  const platform = process.platform;
  const copyAllowed = platform === 'darwin';

  const chosen = await select<string>({
    message: 'Pick the alias you want to use',
    choices: [
      { name: 'context', value: 'context' },
      { name: copyAllowed ? 'copy' : 'copy (not supported on this OS)', value: 'copy' },
      { name: 'repo2prompt', value: 'repo2prompt' },
      { name: 'repo2cp', value: 'repo2cp' },
      { name: 'repo-to-prompt', value: 'repo-to-prompt' },
      { name: 'others (custom)', value: 'custom' },
    ],
    default: commandName === 'repo-to-prompt' ? 'repo-to-prompt' : commandName,
  });

  let aliasName = chosen;

  if (aliasName === 'copy' && !copyAllowed) {
    console.log('\n`copy` is not supported on Linux/Windows. Please choose a different alias.\n');
    aliasName = await input({ message: 'Alias name', default: 'context' });
  }

  if (aliasName === 'custom') {
    aliasName = await input({ message: 'Enter your alias name', default: 'context' });
  }

  aliasName = aliasName.trim();

  if (!aliasName) {
    writeConfig({ completed: true });
    return;
  }

  // If user picked one of our npm bin aliases, no shell changes are strictly required.
  // Still offer to add a shell alias for convenience.
  const wantsShell = await confirm({
    message: 'Add a shell alias so you can run it as a command in your terminal?',
    default: true,
  });

  if (!wantsShell) {
    writeConfig({ completed: true, preferredAlias: aliasName });
    return;
  }

  if (platform === 'win32') {
    console.log('\nWindows detected. Add an alias manually (PowerShell):');
    console.log(`  Set-Alias ${aliasName} repo-to-prompt`);
    console.log('Or install globally and use the provided bin aliases.\n');
    writeConfig({ completed: true, preferredAlias: aliasName });
    return;
  }

  const shellRc = detectShellRc();
  if (!shellRc) {
    console.log('\nCould not detect your shell rc file. You can add this manually:');
    console.log(`  ${aliasLine('bash', aliasName)}`);
    console.log('');
    writeConfig({ completed: true, preferredAlias: aliasName });
    return;
  }

  const line = aliasLine(shellRc.shellName, aliasName);

  if (fileContains(shellRc.rcPath, line)) {
    console.log(`\nAlias already present in ${shellRc.rcPath}\n`);
    writeConfig({ completed: true, preferredAlias: aliasName });
    return;
  }

  const ok = await confirm({
    message: `Write alias to ${shellRc.rcPath}?`,
    default: true,
  });

  if (!ok) {
    console.log('\nSkipped writing shell config. Add this manually if you want:');
    console.log(`  ${line}`);
    console.log('');
    writeConfig({ completed: true, preferredAlias: aliasName });
    return;
  }

  try {
    if (shellRc.shellName === 'fish') {
      mkdirSync(join(homedir(), '.config', 'fish'), { recursive: true });
    }
    appendFileSync(shellRc.rcPath, `\n# repo-to-prompt\n${line}\n`, 'utf-8');
    console.log(`\n✅ Added alias. Restart your terminal or run: source ${shellRc.rcPath}\n`);
  } catch {
    console.log('\nFailed to write shell config. Add this manually:');
    console.log(`  ${line}`);
    console.log('');
  }

  writeConfig({ completed: true, preferredAlias: aliasName });
}

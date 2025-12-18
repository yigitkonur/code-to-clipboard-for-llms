import https from 'node:https';

const VERSION = '1.0.0';

interface UpdateInfo {
  current: string;
  latest: string;
  command: string;
}

export function getVersion(): string {
  return VERSION;
}

export async function checkForUpdates(): Promise<UpdateInfo | null> {
  const current = getVersion();

  try {
    const latest = await fetchLatestVersion();
    if (latest && isNewer(current, latest)) {
      return {
        current,
        latest,
        command: 'npm install -g repo-to-prompt',
      };
    }
  } catch {
    // Ignore network errors
  }

  return null;
}

function fetchLatestVersion(): Promise<string | null> {
  return new Promise((resolve) => {
    const req = https.get(
      'https://registry.npmjs.org/repo-to-prompt/latest',
      { timeout: 3000 },
      (res) => {
        let data = '';
        res.on('data', (chunk) => (data += chunk));
        res.on('end', () => {
          try {
            const json = JSON.parse(data);
            resolve(json.version ?? null);
          } catch {
            resolve(null);
          }
        });
      }
    );

    req.on('error', () => resolve(null));
    req.on('timeout', () => {
      req.destroy();
      resolve(null);
    });
  });
}

function isNewer(current: string, latest: string): boolean {
  const parse = (v: string): number[] => {
    try {
      return v
        .replace(/^v/, '')
        .split('.')
        .slice(0, 3)
        .map((x) => parseInt(x, 10) || 0);
    } catch {
      return [0, 0, 0];
    }
  };

  const c = parse(current);
  const l = parse(latest);

  for (let i = 0; i < 3; i++) {
    if ((l[i] ?? 0) > (c[i] ?? 0)) return true;
    if ((l[i] ?? 0) < (c[i] ?? 0)) return false;
  }

  return false;
}

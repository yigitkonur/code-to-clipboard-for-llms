import type { ScanResult } from '../types/index.js';

export function formatJson(result: ScanResult, includeContent = false): string {
  const totalLines = result.files.reduce((sum, f) => sum + f.lineCount, 0);
  const totalChars = result.files.reduce((sum, f) => sum + f.charCount, 0);

  interface ProjectInfo {
    files: number;
    lines: number;
    chars: number;
    scanned: number;
    tech_stack: string[];
    github?: {
      owner: string;
      repo: string;
      branch?: string | undefined;
      url: string;
    };
    root?: string;
  }

  const projectInfo: ProjectInfo = {
    files: result.files.length,
    lines: totalLines,
    chars: totalChars,
    scanned: result.totalScanned,
    tech_stack: [...result.techStack],
  };

  if (result.config.githubRepo) {
    projectInfo.github = {
      owner: result.config.githubRepo.owner,
      repo: result.config.githubRepo.name,
      branch: result.config.githubRepo.branch,
      url: `https://github.com/${result.config.githubRepo.owner}/${result.config.githubRepo.name}`,
    };
  } else {
    projectInfo.root = result.config.rootDir;
  }

  const output = {
    project: projectInfo,
    files: result.files.map((f) => ({
      path: f.relativePath,
      lines: f.lineCount,
      chars: f.charCount,
      percentage: Math.round(f.percentage * 100) / 100,
      language: f.language,
      ...(includeContent ? { content: f.content } : {}),
    })),
  };

  return JSON.stringify(output, null, 2);
}

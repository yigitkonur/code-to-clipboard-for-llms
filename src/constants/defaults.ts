export const Defaults = {
  MAX_SIZE: '2M',
  MAX_FILE_CHARS: 50000,
  OUTPUT_FORMAT: 'markdown' as const,
} as const;

export const ExcludedDirs = new Set([
  // Version control
  '.git', '.svn', '.hg', '.bzr',
  // Dependencies
  'node_modules', 'vendor', 'bower_components',
  // Virtual environments
  'venv', 'env', '.venv', 'ENV', 'virtualenv', '.virtualenv',
  // Build outputs
  'build', 'dist', 'target', 'out', 'bin', 'obj', '_build',
  // Cache directories
  '__pycache__', '.cache', 'cache', '.pytest_cache',
  '.mypy_cache', '.tox', '.nox', '.ruff_cache',
  // IDE directories
  '.idea', '.vscode', '.vs',
  // Logs and coverage
  'logs', 'log', 'coverage', 'htmlcov', '.nyc_output',
  // Framework specific
  '.terraform', '.next', '.nuxt', '.svelte-kit',
  // Static assets (usually not code)
  'public', 'static', 'assets', 'images', 'img', 'icons',
  'fonts', 'media', 'uploads', 'downloads',
  // Documentation and tests (can be included via flags)
  'docs', 'documentation', 'tests', '__tests__', 'test', 'spec',
]);

export const ExcludedPatterns = new Set([
  // Compiled/binary files
  '*.pyc', '*.pyo', '*.pyd', '*.so', '*.o', '*.a', '*.lib',
  '*.dylib', '*.dll', '*.exe', '*.class', '*.jar', '*.war',
  // Build artifacts
  '*.log', '*.tsbuildinfo', '*.d.ts.map',
  // Editor files
  '*.swp', '*.swo', '*~', '#*#', '.DS_Store', 'Thumbs.db',
  // Patches
  '*.patch', '*.diff',
  // Lock files
  '*.lock', 'pnpm-lock.yaml', 'yarn.lock', 'package-lock.json',
  'poetry.lock', 'composer.lock', 'Gemfile.lock', 'bun.lockb',
  // State files
  '*.tfstate', '*.tfstate.backup',
  // Temp files
  '*.bak', '*.tmp', '*.temp',
  // Minified and maps
  '*.min.js', '*.min.css', '*.map',
  // Media files
  '*.svg', '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.webp',
  '*.bmp', '*.tiff', '*.tif', '*.woff', '*.woff2', '*.ttf',
  '*.eot', '*.otf', '*.mp3', '*.mp4', '*.avi', '*.mov', '*.wmv',
  '*.flv', '*.webm', '*.wav', '*.ogg',
  // Archives
  '*.zip', '*.tar', '*.gz', '*.rar', '*.7z', '*.bz2',
  // Design files
  '*.psd', '*.ai', '*.eps', '*.sketch', '*.fig', '*.xd',
  // 3D files
  '*.blend', '*.obj', '*.fbx', '*.dae', '*.3ds',
  // Documents
  '*.pdf', '*.doc', '*.docx', '*.xls', '*.xlsx', '*.ppt', '*.pptx',
]);

export const DataPatterns = new Set([
  '*.json', '*.jsonc', '*.yaml', '*.yml', '*.xml',
  '*.html', '*.htm', '*.css', '*.sql', '*.csv', '*.tsv',
  '*.md', '*.markdown', '*.rst',
]);

export const ConfigSkip = new Set([
  '.editorconfig', '.gitattributes', '.gitmodules',
  'tsconfig.json', 'tsconfig.*.json', 'jsconfig.json',
  '.eslintrc*', '.prettierrc*', '.stylelintrc*',
]);

export const AlwaysInclude = new Set([
  'README.md', 'README.rst', 'README.txt', 'README',
  '.env.example', '.env.sample',
  'docker-compose.yml', 'docker-compose.yaml', 'Dockerfile',
  'requirements.txt', 'pyproject.toml', 'setup.py', 'setup.cfg',
  'go.mod', 'go.sum', 'Cargo.toml', 'Cargo.lock',
  'Makefile', 'CMakeLists.txt',
]);

export const AlwaysSkip = new Set([
  '.gitignore', '.dockerignore', '.npmignore',
  'package.json', 'package-lock.json', 'pnpm-lock.yaml',
  'yarn.lock', 'bun.lockb',
  '.env', '.env.local', '.env.development', '.env.production',
  'LICENSE', 'LICENSE.md', 'LICENSE.txt',
  'CHANGELOG.md', 'CHANGELOG', 'HISTORY.md',
  '.prettierignore', '.eslintignore',
]);

export const GLYPH_CHILD = '├──';
export const GLYPH_LAST = '└──';
export const GLYPH_PIPE = '│   ';
export const GLYPH_SPACE = '    ';

// Reviewed external runtime; never loads an application's ESLint config/plugins.
import { createRequire } from 'node:module';
import path from 'node:path';
const [runtime, workspace, ...files] = process.argv.slice(2);
try {
  const require = createRequire(path.join(runtime, 'package.json'));
  const { ESLint } = require('eslint');
  const ts = require('typescript-eslint');
  const engine = new ESLint({
    cwd: workspace, overrideConfigFile: true, ignore: false,
    overrideConfig: [{
      files: ['**/*.ts', '**/*.tsx', '**/*.mts', '**/*.cts'],
      languageOptions: { parser: ts.parser, parserOptions: {
        projectService: true, tsconfigRootDir: workspace,
      } },
      plugins: { '@typescript-eslint': ts.plugin },
      linterOptions: { noInlineConfig: true },
      rules: {
        '@typescript-eslint/no-floating-promises': ['error', { ignoreVoid: false }],
        '@typescript-eslint/no-misused-promises': 'error',
      },
    }],
  });
  const results = await engine.lintFiles(files);
  const diagnostics = results.flatMap(r => r.messages.map(m => ({
    file: path.relative(workspace, r.filePath), rule: m.ruleId,
    line: m.line, column: m.column, severity: m.severity, message: m.message,
  })));
  const passed = results.length === files.length && results.every(r => r.errorCount === 0 && r.warningCount === 0);
  console.log(JSON.stringify({ passed, diagnostics, files: results.map(r => path.relative(workspace, r.filePath)) }));
  process.exitCode = passed ? 0 : 1;
} catch (error) {
  console.log(JSON.stringify({ passed: false, unavailable: String(error) }));
  process.exitCode = 2;
}

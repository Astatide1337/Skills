// Supplemental checks: native TypeScript context, reviewed rules, no app ESLint code.
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const [runtimeArg, workspaceArg, ...args] = process.argv.slice(2);
const result = {
  passed: false, diagnostics: [], files: [], stages: [],
  context: { configs: [], inputs: {}, tool_versions: {} }, unchanged_inputs: false,
};
const hash = data => createHash('sha256').update(data).digest('hex');
const within = (root, file) => file === root || file.startsWith(root + path.sep);
const sensitive = file => file.split(path.sep).some(part =>
  /^(?:\.git|\.aws|\.ssh|\.gnupg|\.codex|\.agents|\.env(?:\..*)?|credentials(?:\..*)?|id_rsa|id_ed25519)$/i.test(part));
// Match check_profile.sensitive_path for project inputs, not trusted tool libraries.
const sensitiveProjectPath = relative => relative.split(path.sep).some(part =>
  /^(?:\.env|\.ssh|\.aws)/i.test(part)
  || /^(?:\.config|credentials|secrets|private|keys\.txt)$/i.test(part)
  || /credential|secret|password|token|private-key/i.test(part))
  || /\.(?:pem|key|p12|pfx)$/i.test(relative);
const stage = (id, status, reason) => result.stages.push({ id, status, ...(reason ? { reason } : {}) });

try {
  if (!runtimeArg || !workspaceArg || !args.length) throw new Error('Expected runtime, workspace and explicit files');
  const runtime = path.resolve(runtimeArg);
  const workspace = path.resolve(workspaceArg);
  for (const root of [runtime, workspace]) {
    if (sensitive(root) || fs.realpathSync(root) !== root) throw new Error('Runtime/workspace must be existing physical, nonsensitive directories');
  }
  if (within(workspace, runtime)) throw new Error('Runtime must be outside the target workspace');
  const relative = file => path.relative(workspace, file).split(path.sep).join('/');
  const permitted = file => !sensitive(file) && (within(workspace, file)
    ? !sensitiveProjectPath(relative(file)) : within(runtime, file));
  const guard = file => {
    const absolute = path.resolve(file);
    if (!permitted(absolute)) throw new Error(`Unsafe context path: ${relative(absolute)}`);
    if (fs.existsSync(absolute) && !permitted(fs.realpathSync(absolute))) {
      throw new Error(`Context symlink escapes approved roots: ${relative(absolute)}`);
    }
    return absolute;
  };
  const read = file => {
    const absolute = guard(file);
    const bytes = fs.readFileSync(absolute);
    const digest = hash(bytes);
    if (result.context.inputs[absolute] && result.context.inputs[absolute] !== digest) {
      throw new Error(`Context changed during read: ${relative(absolute)}`);
    }
    result.context.inputs[absolute] = digest;
    return bytes.toString('utf8');
  };
  const exists = file => {
    if (!permitted(path.resolve(file))) return false;
    return fs.existsSync(guard(file));
  };
  let project;
  if (args[0] === '--project') {
    project = guard(path.resolve(workspace, args[1] || ''));
    if (!within(workspace, project) || !fs.statSync(project).isFile()) throw new Error('--project requires an existing target configuration file');
    args.splice(0, 2);
  }
  if (!args.length || args.some(file => file.startsWith('--'))) throw new Error('Expected explicit files after optional --project');
  const selected = [...new Set(args.map(file => guard(path.resolve(workspace, file))))];
  for (const file of selected) {
    if (!within(workspace, file) || !/\.(?:[cm]?[jt]s|[jt]sx)$/.test(file)) throw new Error(`Unsupported target: ${relative(file)}`);
    if (!fs.statSync(file).isFile()) throw new Error(`Target is not a regular file: ${relative(file)}`);
    read(file);
  }
  const require = createRequire(path.join(runtime, 'package.json'));
  const pins = { eslint: '10.12.0', 'typescript-eslint': '8.71.1', typescript: '6.0.2', 'eslint-plugin-react-hooks': '7.1.1' };
  read(path.join(runtime, 'package.json'));
  read(path.join(runtime, 'package-lock.json'));
  for (const [name, version] of Object.entries(pins)) {
    const metadata = JSON.parse(read(path.join(runtime, 'node_modules', name, 'package.json')));
    if (metadata.version !== version) throw new Error(`${name} requires exact version ${version}, found ${metadata.version}`);
    read(require.resolve(name));
    result.context.tool_versions[name] = metadata.version;
  }
  result.context.tool_versions.node = process.version;
  const { ESLint } = require('eslint');
  const typed = require('typescript-eslint');
  const ts = require('typescript');
  const hooks = require('eslint-plugin-react-hooks');
  // Use native include/exclude semantics; inspect symlinks before traversal.
  const readDirectory = (root, extensions, excludes, includes, depth) => ts.matchFiles(
    guard(root), extensions, excludes, includes, ts.sys.useCaseSensitiveFileNames,
    workspace, depth, directory => {
      const entries = fs.readdirSync(guard(directory), { withFileTypes: true });
      const files = [], directories = [];
      for (const entry of entries) {
        const file = path.join(directory, entry.name);
        if (!permitted(file)) continue;
        if (entry.isSymbolicLink()) guard(file);
        const stat = entry.isSymbolicLink() ? fs.statSync(file) : entry;
        if (stat.isDirectory()) directories.push(entry.name);
        else if (stat.isFile()) files.push(entry.name);
      }
      return { files, directories };
    }, file => guard(fs.realpathSync(guard(file))),
  );
  const system = {
    ...ts.sys, readDirectory,
    readFile: file => exists(file) ? read(file) : undefined,
    fileExists: exists,
    directoryExists: file => exists(file) && fs.statSync(file).isDirectory(),
    getDirectories: directory => !exists(directory) ? [] : fs.readdirSync(guard(directory), { withFileTypes: true })
      .filter(entry => permitted(path.join(directory, entry.name)))
      .filter(entry => entry.isSymbolicLink() ? fs.statSync(guard(path.join(directory, entry.name))).isDirectory() : entry.isDirectory())
      .map(entry => entry.name),
    realpath: file => guard(fs.realpathSync(guard(file))),
    getCurrentDirectory: () => workspace,
  };
  const strict = {
    strict: true, noImplicitAny: true, strictNullChecks: true,
    strictFunctionTypes: true, strictBindCallApply: true, strictPropertyInitialization: true,
    noImplicitThis: true, alwaysStrict: true, useUnknownInCatchVariables: true,
    strictBuiltinIteratorReturn: true, noUncheckedIndexedAccess: true,
    exactOptionalPropertyTypes: true, noCheck: false,
    skipLibCheck: false, skipDefaultLibCheck: false,
  };
  const configs = new Map();
  const configPaths = new Set();
  const parseConfig = config => {
    config = guard(config);
    if (configs.has(config)) return configs.get(config);
    const host = { ...system, onUnRecoverableConfigFileDiagnostic: diagnostic => { throw new Error(ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n')); } };
    const parsed = ts.getParsedCommandLineOfConfigFile(config, strict, host);
    if (!parsed) throw new Error(`Cannot parse project ${relative(config)}`);
    if (parsed.options.allowJs) parsed.options.checkJs = true;
    configs.set(config, parsed);
    configPaths.add(config);
    for (const extended of parsed.options.configFile?.extendedSourceFiles || []) configPaths.add(guard(extended));
    for (const reference of parsed.projectReferences || []) parseConfig(ts.resolveProjectReferencePath(reference));
    return parsed;
  };
  const nearestConfig = file => {
    for (let directory = path.dirname(file); within(workspace, directory); directory = path.dirname(directory)) {
      const config = path.join(directory, 'tsconfig.json');
      const jsconfig = path.join(directory, 'jsconfig.json');
      if (exists(config)) return config;
      if (/\.[cm]?jsx?$/.test(file) && exists(jsconfig)) return jsconfig;
      if (directory === workspace) break;
    }
    return undefined;
  };
  const memberships = new Map();
  const contextErrors = [];
  for (const file of selected) {
    const config = project || nearestConfig(file);
    if (!config) { contextErrors.push(`No native TypeScript/JavaScript project for ${relative(file)}`); continue; }
    const visited = new Set();
    const findMember = candidate => {
      if (visited.has(candidate)) return undefined;
      visited.add(candidate);
      const parsed = parseConfig(candidate);
      if (parsed.fileNames.some(name => path.resolve(name) === file)) return candidate;
      for (const reference of parsed.projectReferences || []) {
        const member = findMember(ts.resolveProjectReferencePath(reference));
        if (member) return member;
      }
      return undefined;
    };
    const member = findMember(config);
    if (!member) contextErrors.push(`Selected file is excluded from native project: ${relative(file)}`);
    else memberships.set(file, member);
  }
  result.context.configs = [...configPaths].map(relative).sort();
  const programs = new Map();
  const diagnosticKeys = new Set();
  const addDiagnostic = diagnostic => {
    const key = JSON.stringify(diagnostic);
    if (!diagnosticKeys.has(key)) { diagnosticKeys.add(key); result.diagnostics.push(diagnostic); }
  };
  const compilerDiagnostic = diagnostic => {
    const start = diagnostic.file && diagnostic.start !== undefined ? diagnostic.file.getLineAndCharacterOfPosition(diagnostic.start) : undefined;
    const end = start ? diagnostic.file.getLineAndCharacterOfPosition(diagnostic.start + (diagnostic.length || 0)) : undefined;
    return {
      file: diagnostic.file ? relative(diagnostic.file.fileName) : '', rule: `typescript/TS${diagnostic.code}`,
      message: ts.flattenDiagnosticMessageText(diagnostic.messageText, '\n'), severity: 2,
      line: start ? start.line + 1 : 1, column: start ? start.character + 1 : 1,
      end_line: end ? end.line + 1 : 1, end_column: end ? end.character + 1 : 1,
    };
  };
  const unavailableCodes = new Set([2307, 2688, 2792, 2875, 6053, 6305, 7016, 7026, 17004]);
  let compilerFailed = false;
  for (const config of new Set(memberships.values())) {
    const parsed = configs.get(config);
    if (parsed.errors.length) contextErrors.push(`Native configuration diagnostics in ${relative(config)}`);
    const host = ts.createCompilerHost(parsed.options);
    Object.assign(host, system);
    host.useCaseSensitiveFileNames = () => ts.sys.useCaseSensitiveFileNames;
    host.getParsedCommandLine = parseConfig;
    host.writeFile = () => { throw new Error('Supplemental compiler must never emit files'); };
    const program = ts.createProgram({ rootNames: parsed.fileNames, options: { ...parsed.options, noEmit: true }, projectReferences: parsed.projectReferences, host });
    programs.set(config, program);
    for (const diagnostic of [...parsed.errors, ...ts.getPreEmitDiagnostics(program)]) {
      addDiagnostic(compilerDiagnostic(diagnostic));
      if (unavailableCodes.has(diagnostic.code)) contextErrors.push(`Native module/type context unavailable (TS${diagnostic.code})`);
      else compilerFailed = true;
    }
    for (const source of program.getSourceFiles()) {
      // Includes actual project-reference redirects and compiler libraries.
      read(source.fileName);
      if (!within(workspace, source.fileName) || source.fileName.includes(`${path.sep}node_modules${path.sep}`)) continue;
      const scanner = ts.createScanner(ts.ScriptTarget.Latest, false, source.languageVariant, source.text);
      for (let token = scanner.scan(); token !== ts.SyntaxKind.EndOfFileToken; token = scanner.scan()) {
        if (![ts.SyntaxKind.SingleLineCommentTrivia, ts.SyntaxKind.MultiLineCommentTrivia].includes(token)) continue;
        if (!/@ts-(?:nocheck|ignore|expect-error)\b/.test(scanner.getTokenText())) continue;
        const start = source.getLineAndCharacterOfPosition(scanner.getTokenPos());
        addDiagnostic({ file: relative(source.fileName), rule: 'typescript/suppression', severity: 2,
          line: start.line + 1, column: start.character + 1, end_line: start.line + 1, end_column: start.character + 1,
          message: 'TypeScript suppression cannot satisfy supplemental strict checking; inspect the native suppressed diagnostic separately.' });
        compilerFailed = true;
      }
    }
  }
  stage('typescript-compiler', contextErrors.length ? 'unavailable' : compilerFailed ? 'failed' : 'accepted', contextErrors.join('; '));
  const strictRules = {
    '@typescript-eslint/no-floating-promises': ['error', { ignoreVoid: false }],
    '@typescript-eslint/no-misused-promises': 'error',
    '@typescript-eslint/no-unsafe-assignment': 'error',
    '@typescript-eslint/no-unsafe-return': 'error',
    '@typescript-eslint/no-unsafe-type-assertion': 'error',
    '@typescript-eslint/switch-exhaustiveness-check': ['error', { considerDefaultExhaustiveForUnions: false }],
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unsafe-call': 'error',
    '@typescript-eslint/no-unsafe-member-access': 'error',
    '@typescript-eslint/no-unsafe-argument': 'error',
    '@typescript-eslint/await-thenable': 'error',
    '@typescript-eslint/no-non-null-assertion': 'error',
  };
  let lintFailed = false, hooksFailed = false, parserUnavailable = false;
  for (const file of selected) {
    const program = programs.get(memberships.get(file));
    const engine = new ESLint({
      cwd: workspace, overrideConfigFile: true, ignore: false, allowInlineConfig: false,
      fix: false, cache: false, applySuppressions: false,
      overrideConfig: [{
        files: ['**/*.{ts,tsx,mts,cts,js,jsx,mjs,cjs}'],
        languageOptions: { parser: typed.parser, parserOptions: {
          ...(program ? { programs: [program] } : {}), tsconfigRootDir: workspace,
          ecmaFeatures: { jsx: true }, onUnsupportedTypeScriptVersion: 'error',
        } },
        plugins: { '@typescript-eslint': typed.plugin, 'react-hooks': hooks },
        rules: {
          ...(program ? strictRules : { '@typescript-eslint/no-explicit-any': 'error' }),
          'react-hooks/rules-of-hooks': 'error', 'react-hooks/exhaustive-deps': 'error',
        },
      }],
    });
    // Bypasses app config, ignore discovery and persisted bulk suppressions.
    const lintResults = await engine.lintText(read(file), { filePath: file });
    if (lintResults.length !== 1 || path.resolve(lintResults[0].filePath) !== file) {
      throw new Error(`Incomplete selected-file coverage: ${relative(file)}`);
    }
    result.files.push(relative(file));
    for (const message of lintResults[0].messages) {
      addDiagnostic({ file: relative(file), rule: message.ruleId || 'eslint/parser',
        line: message.line || 1, column: message.column || 1,
        end_line: message.endLine || message.line || 1, end_column: message.endColumn || message.column || 1,
        severity: message.severity, message: message.message });
      if (message.fatal || !message.ruleId) parserUnavailable = true;
      else if (message.ruleId.startsWith('react-hooks/')) hooksFailed = true;
      else lintFailed = true;
    }
  }
  stage('typescript-eslint', contextErrors.length || parserUnavailable ? 'unavailable' : lintFailed ? 'failed' : 'accepted',
    contextErrors.length ? contextErrors.join('; ') : parserUnavailable ? 'Parser or selected-file context unavailable' : undefined);
  stage('react-hooks', parserUnavailable ? 'unavailable' : hooksFailed ? 'failed' : 'accepted');
  result.unchanged_inputs = Object.entries(result.context.inputs).every(([file, digest]) => hash(fs.readFileSync(guard(file))) === digest);
  if (!result.unchanged_inputs) stage('unchanged-inputs', 'unavailable', 'Consumed source/config/dependency/library bytes changed');
  result.passed = result.unchanged_inputs && result.files.length === selected.length && result.stages.every(check => check.status === 'accepted');
  if (result.stages.some(check => check.status === 'unavailable')) result.unavailable = 'Required typed tooling, membership or native context is unavailable';
} catch (error) {
  result.unavailable = String(error);
  stage('typescript-context', 'unavailable', String(error));
}
console.log(JSON.stringify(result));
process.exitCode = result.passed ? 0 : result.unavailable ? 2 : 1;

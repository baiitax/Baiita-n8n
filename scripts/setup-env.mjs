import { randomBytes } from 'node:crypto';
import { chmod, readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const templatePath = path.join(root, '.env.example');
const outputPath = path.join(root, '.env');

let template;
try {
  template = await readFile(templatePath, 'utf8');
} catch {
  console.error('Could not read .env.example. Run this script from a complete Baiita-n8n checkout.');
  process.exit(1);
}

const replacements = {
  N8N_ENCRYPTION_KEY: randomBytes(32).toString('hex'),
  POSTGRES_PASSWORD: randomBytes(32).toString('hex'),
};

if (Object.values(replacements).some((secret) => secret.length < 32)) {
  throw new Error('Generated secrets did not meet the minimum length.');
}

let output = template;
for (const [name, value] of Object.entries(replacements)) {
  output = output.replace(`${name}=__GENERATE_WITH_NPM_RUN_SETUP__`, `${name}=${value}`);
}

try {
  await writeFile(outputPath, output, { encoding: 'utf8', mode: 0o600, flag: 'wx' });
  await chmod(outputPath, 0o600);
  console.log('Created .env with unique secrets (permissions: 0600). Keep it private and back it up securely.');
  console.log('Next: docker compose up --build -d');
} catch (error) {
  if (error.code === 'EEXIST') {
    console.error('.env already exists. It was left untouched so existing encryption keys are not lost.');
    process.exit(1);
  }
  throw error;
}

const fs = require('fs');
const path = require('path');

// Caminhos dos arquivos
const requirementsPath = path.join(__dirname, 'requirements', 'requirementsJS.txt');
const packageJsonPath = path.join(__dirname, 'package.json');

// Lê o arquivo requirementsJS.txt
const requirements = fs.readFileSync(requirementsPath, 'utf-8').split('\n').filter(Boolean);

// Lê o package.json
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8'));

// Adiciona as dependências ao package.json
packageJson.dependencies = packageJson.dependencies || {};
requirements.forEach(dep => {
  if (!packageJson.dependencies[dep]) {
    packageJson.dependencies[dep] = "latest"; // Define a versão como "latest"
  }
});

// Salva o package.json atualizado
fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));
console.log('Dependências atualizadas no package.json!');
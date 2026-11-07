// dupnames.cjs <acorn dir> <app.js...>: parse each staged bundle as one module and list top-level names declared twice.
const acorn = require(process.argv[2]);
const fs = require("fs");
function patNames(p, out) {
  if (!p) return;
  switch (p.type) {
    case "Identifier": out.push(p.name); break;
    case "ObjectPattern": p.properties.forEach((q) => patNames(q.type === "RestElement" ? q.argument : q.value, out)); break;
    case "ArrayPattern": p.elements.forEach((e) => patNames(e, out)); break;
    case "RestElement": patNames(p.argument, out); break;
    case "AssignmentPattern": patNames(p.left, out); break;
  }
}
let bad = 0;
for (const f of process.argv.slice(3)) {
  const src = fs.readFileSync(f, "utf8");
  let ast;
  try { ast = acorn.parse(src, { ecmaVersion: "latest", sourceType: "module", locations: true }); }
  catch (e) { console.log(`${f}: PARSE ERROR ${e.message}`); bad++; continue; }
  const seen = new Map(); const dups = []; let imports = 0;
  for (let node of ast.body) {
    if (node.type === "ImportDeclaration") { imports++; continue; }
    if ((node.type === "ExportNamedDeclaration") && node.declaration) node = node.declaration;
    const names = [];
    if (node.type === "VariableDeclaration") node.declarations.forEach((d) => patNames(d.id, names));
    else if ((node.type === "FunctionDeclaration" || node.type === "ClassDeclaration") && node.id) names.push(node.id.name);
    for (const n of names) {
      if (seen.has(n)) dups.push(`${n} (lines ${seen.get(n)} and ${node.loc.start.line})`);
      else seen.set(n, node.loc.start.line);
    }
  }
  console.log(`${f}: ${seen.size} top-level names, ${imports} imports left, ${dups.length} duplicates${dups.length ? ": " + dups.join("; ") : ""}`);
  if (dups.length || imports) bad++;
}
process.exit(bad ? 1 : 0);

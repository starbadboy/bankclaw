const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const pageSource = fs.readFileSync(path.join(__dirname, "page-transactions.jsx"), "utf8");
const styleSource = fs.readFileSync(path.join(__dirname, "styles.css"), "utf8");
const titleStyle = styleSource.match(/\.ledger \.transaction-title\s*\{([^}]*)\}/)?.[1] || "";

test("transaction titles expose the full description while using the compact title style", () => {
  assert.match(pageSource, /className="transaction-title"/);
  assert.match(pageSource, /title=\{t\.description\}/);
  assert.match(pageSource, /aria-label=\{t\.description\}/);
  assert.match(styleSource, /\.ledger \.transaction-title/);
  assert.match(styleSource, /inline-size: min\(100%, 64ch\)/);
  assert.match(styleSource, /text-overflow: ellipsis/);
  assert.match(titleStyle, /text-align: center;/);
});

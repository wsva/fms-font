// Minimal static server for the font probes: Chromium needs an http:// origin for
// @font-face, and the WSL instance is in NAT mode so a server inside it is not
// reachable as 127.0.0.1 from the Windows browser.
//   node work/serve.mjs [port] [--root <dir>]
// serves the font/ directory, or <dir> - a probe that has to load the app's own
// stylesheet (markdown.css) runs with --root .. to reach src/ as well.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const argv = process.argv.slice(2);
const at = argv.indexOf("--root");
const ROOT = resolve(at < 0 ? resolve(fileURLToPath(import.meta.url), "..", "..")
                            : argv[at + 1]);
const TYPES = { ".ttf": "font/ttf", ".woff2": "font/woff2", ".html": "text/html; charset=utf-8",
                ".css": "text/css", ".png": "image/png", ".pdf": "application/pdf" };

createServer(async (req, res) => {
  const path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!path.startsWith(ROOT)) { res.writeHead(403); return res.end("no"); }
  try {
    const body = await readFile(path);
    // never let a rebuilt face be served from cache - the probe compares builds
    res.writeHead(200, { "content-type": TYPES[extname(path)] || "application/octet-stream",
                         "cache-control": "no-store" });
    res.end(body);
  } catch { res.writeHead(404); res.end("404"); }
}).listen(Number(argv[0] || 8099), "127.0.0.1",
  () => console.log(`serving ${ROOT} on http://127.0.0.1:${Number(argv[0] || 8099)}`));

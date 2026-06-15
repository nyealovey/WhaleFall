import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

const frontendRoot = process.cwd();
const repoRoot = path.resolve(frontendRoot, "..");

function readText(relativePath: string): string {
  return readFileSync(path.resolve(repoRoot, relativePath), "utf8");
}

describe("console static asset contract", () => {
  it("keeps the React build-time font stylesheet aligned with the legacy static font stylesheet", () => {
    const indexHtml = readText("frontend/index.html");
    const legacyFontsCss = readText("app/static/css/fonts.css");
    const consoleFontsCss = readText("frontend/public/static/css/fonts.css");

    expect(indexHtml).toContain('href="/static/css/fonts.css"');
    expect(consoleFontsCss).toBe(legacyFontsCss);

    const fontUrls = [...consoleFontsCss.matchAll(/url\('([^']+)'\)/g)].map((match) => match[1]);
    expect(fontUrls.length).toBeGreaterThan(0);
    for (const fontUrl of fontUrls) {
      const fontPath = path.resolve(repoRoot, "frontend/public/static/css", fontUrl);
      expect(existsSync(fontPath), fontUrl).toBe(true);
    }
  });
});

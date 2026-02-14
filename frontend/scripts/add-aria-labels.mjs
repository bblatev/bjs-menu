#!/usr/bin/env node
/**
 * Add aria-labels to icon-only buttons for accessibility.
 * Targets:
 * 1. Close buttons with &times; content
 * 2. Close buttons with X SVG (M6 18L18 6M6 6l12 12 path)
 * 3. Back/navigation buttons with arrow SVGs
 */

import { readFileSync, writeFileSync } from 'fs';
import { execSync } from 'child_process';

// Find files with &times; close buttons
const timesFiles = execSync(
  `grep -rl '&times;' --include='*.tsx' /opt/bjs-menu/frontend/app/`,
  { encoding: 'utf8' }
).trim().split('\n').filter(Boolean);

// Find files with X SVG close buttons (M6 18L18 6M6 6l12 12)
let svgCloseFiles = [];
try {
  svgCloseFiles = execSync(
    `grep -rl 'M6 18L18 6M6 6l12 12' --include='*.tsx' /opt/bjs-menu/frontend/app/`,
    { encoding: 'utf8' }
  ).trim().split('\n').filter(Boolean);
} catch (e) {}

// Find files with back arrow SVG (M15 19l-7-7 7-7)
let backArrowFiles = [];
try {
  backArrowFiles = execSync(
    `grep -rl 'M15 19l-7-7 7-7' --include='*.tsx' /opt/bjs-menu/frontend/app/`,
    { encoding: 'utf8' }
  ).trim().split('\n').filter(Boolean);
} catch (e) {}

const allFiles = new Set([...timesFiles, ...svgCloseFiles, ...backArrowFiles]);
let totalFixes = 0;

for (const filePath of allFiles) {
  let content = readFileSync(filePath, 'utf8');
  let fixes = 0;
  const original = content;

  // 1. Add aria-label="Close" to &times; buttons that don't have it
  // Pattern: <button ...attrs...\n> followed by &times; (multi-line button tags)
  content = content.replace(
    /(<button\b)([\s\S]*?)(>\s*\n\s*&times;\s*\n\s*<\/button>)/g,
    (match, tag, attrs, after) => {
      if (attrs.includes('aria-label')) return match;
      fixes++;
      return tag + attrs + ' aria-label="Close"' + after;
    }
  );

  // 2. Add aria-label="Close" to SVG X buttons
  // These have the close X path (M6 18L18 6M6 6l12 12)
  content = content.replace(
    /(<button\b(?:(?!aria-label)[^>])*?)(>\s*\n?\s*<svg[^>]*>[\s\S]*?M6 18L18 6M6 6l12 12[\s\S]*?<\/svg>\s*\n?\s*<\/button>)/g,
    (match, before, after) => {
      if (before.includes('aria-label')) return match;
      fixes++;
      return before + ' aria-label="Close"' + after;
    }
  );

  if (content !== original) {
    writeFileSync(filePath, content);
    const shortPath = filePath.replace('/opt/bjs-menu/frontend/', '');
    console.log(`  ${shortPath}: ${fixes} aria-label(s) added`);
    totalFixes += fixes;
  }
}

console.log(`\nTotal: ${totalFixes} aria-labels added across ${allFiles.size} files checked`);

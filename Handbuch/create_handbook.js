/**
 * create_handbook.js
 * Erstellt das CREDO Benutzerhandbuch als Word-Dokument (.docx)
 * Corporate Design: CREDO Verwaltung (Grau/Gelb/Grün/Rot/Blau)
 *
 * Ausführen: node Handbuch/create_handbook.js
 */

'use strict';

const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat, VerticalAlign,
  NumberFormat, Tab, TabStopType, TabStopPosition
} = require('docx');

const fs   = require('fs');
const path = require('path');

// ============================================================
// CREDO Verwaltung Corporate Identity
// ============================================================

const COLORS = {
  primary:   'DADADA',  // Hellgrau
  dark:      '575756',  // Dunkelgrau
  yellow:    'FBC900',
  green:     '6BAA24',
  red:       'E2001A',
  blue:      '009AC6',
  black:     '000000',
  white:     'FFFFFF',
  warnBg:    'FFF3CD',  // Gelb-beige für ⚠️
  infoBg:    'D1ECF1',  // Blau-hell für ℹ️
  tipBg:     'D4EDDA',  // Grün-hell für ✅
  codeBg:    'F2F2F2',  // Hellgrau für Code-Blöcke
  screenshotBg: 'F8F9FA',
  tableHeader: 'DADADA',
};

// Font-Größen (in Half-Points: 22 = 11pt)
const FONT = {
  h1:   64,  // 32pt
  h2:   48,  // 24pt
  h3:   36,  // 18pt
  body: 22,  // 11pt
  small: 18, // 9pt
  footer: 16,// 8pt
  code:  20, // 10pt
};

// ============================================================
// Handbuch-Inhalt einlesen
// ============================================================

const handbuchPath = path.join(__dirname, '02_handbuch_entwurf.md');
const handbuchContent = fs.readFileSync(handbuchPath, 'utf8');

// ============================================================
// Styles und Numbering
// ============================================================

const numbering = {
  config: [
    {
      reference: 'bullets',
      levels: [{
        level: 0,
        format: LevelFormat.BULLET,
        text: '\u2022',
        alignment: AlignmentType.LEFT,
        style: {
          paragraph: { indent: { left: 720, hanging: 360 } },
          run: { font: 'Arial', size: FONT.body }
        }
      }]
    },
    {
      reference: 'numbers',
      levels: [{
        level: 0,
        format: LevelFormat.DECIMAL,
        text: '%1.',
        alignment: AlignmentType.LEFT,
        style: {
          paragraph: { indent: { left: 720, hanging: 360 } },
          run: { font: 'Arial', size: FONT.body }
        }
      }]
    }
  ]
};

const styles = {
  default: {
    document: {
      run: { font: 'Arial', size: FONT.body, color: COLORS.black }
    }
  },
  paragraphStyles: [
    {
      id: 'Heading1',
      name: 'Heading 1',
      basedOn: 'Normal',
      next: 'Normal',
      quickFormat: true,
      run: { size: FONT.h1, bold: true, font: 'Arial', color: COLORS.dark },
      paragraph: { spacing: { before: 480, after: 240 } }
    },
    {
      id: 'Heading2',
      name: 'Heading 2',
      basedOn: 'Normal',
      next: 'Normal',
      quickFormat: true,
      run: { size: FONT.h2, bold: true, font: 'Arial', color: COLORS.dark },
      paragraph: { spacing: { before: 360, after: 180 } }
    },
    {
      id: 'Heading3',
      name: 'Heading 3',
      basedOn: 'Normal',
      next: 'Normal',
      quickFormat: true,
      run: { size: FONT.h3, bold: true, font: 'Arial', color: COLORS.black },
      paragraph: { spacing: { before: 240, after: 120 } }
    }
  ]
};

// ============================================================
// Inline-Formatierung: **bold**, *italic*, `code`
// ============================================================

function parseInline(text) {
  if (!text) return [new TextRun({ text: '', font: 'Arial', size: FONT.body })];

  const runs = [];
  // Regex: **bold** | *italic* | `code`
  const regex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    // Text before match
    if (match.index > lastIndex) {
      runs.push(new TextRun({
        text: text.slice(lastIndex, match.index),
        font: 'Arial', size: FONT.body
      }));
    }
    const m = match[0];
    if (m.startsWith('**')) {
      runs.push(new TextRun({
        text: m.slice(2, -2), bold: true, font: 'Arial', size: FONT.body
      }));
    } else if (m.startsWith('*')) {
      runs.push(new TextRun({
        text: m.slice(1, -1), italics: true, font: 'Arial', size: FONT.body
      }));
    } else if (m.startsWith('`')) {
      runs.push(new TextRun({
        text: m.slice(1, -1), font: 'Courier New', size: FONT.code
      }));
    }
    lastIndex = match.index + m.length;
  }

  // Remaining text
  if (lastIndex < text.length) {
    runs.push(new TextRun({
      text: text.slice(lastIndex), font: 'Arial', size: FONT.body
    }));
  }

  return runs.length > 0 ? runs : [new TextRun({ text, font: 'Arial', size: FONT.body })];
}

// ============================================================
// Tabellen aus Markdown-Zeilen erstellen
// ============================================================

function buildTable(rows) {
  if (!rows || rows.length === 0) return null;

  const tableRows = rows.map((row, rowIndex) => {
    // Split by | and remove first/last empty elements
    const cells = row.split('|').slice(1, -1).map(c => c.trim());
    const isHeader = rowIndex === 0;

    const tableCells = cells.map(cellText => new TableCell({
      children: [new Paragraph({
        children: parseInline(cellText),
        spacing: { before: 60, after: 60 }
      })],
      shading: isHeader
        ? { fill: COLORS.tableHeader, type: ShadingType.CLEAR }
        : { fill: COLORS.white, type: ShadingType.CLEAR },
      margins: { top: 60, bottom: 60, left: 120, right: 120 },
      verticalAlign: VerticalAlign.CENTER
    }));

    return tableCells.length > 0
      ? new TableRow({ children: tableCells, tableHeader: isHeader })
      : null;
  }).filter(Boolean);

  if (tableRows.length === 0) return null;

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: tableRows,
    margins: { top: 120, bottom: 120, left: 120, right: 120 },
    borders: {
      top:         { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
      bottom:      { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
      left:        { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
      right:       { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
      insideH:     { style: BorderStyle.SINGLE, size: 2, color: COLORS.primary },
      insideV:     { style: BorderStyle.SINGLE, size: 2, color: COLORS.primary },
    }
  });
}

// ============================================================
// Trennseite für TEIL A / B / C / D / E
// ============================================================

function buildSectionPage(partLabel, partTitle) {
  return [
    new Paragraph({ children: [new PageBreak()] }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: COLORS.primary, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text: ' '.repeat(200), font: 'Arial', size: 48 })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: COLORS.primary, type: ShadingType.CLEAR },
      spacing: { before: 2880, after: 480 },
      children: [new TextRun({
        text: partLabel, font: 'Arial', size: 80, bold: true, color: COLORS.dark
      })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: COLORS.primary, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 2880 },
      children: [new TextRun({
        text: partTitle, font: 'Arial', size: 48, color: COLORS.dark
      })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      shading: { fill: COLORS.primary, type: ShadingType.CLEAR },
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text: ' '.repeat(200), font: 'Arial', size: 48 })]
    }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ============================================================
// Hinweis-Box Helfer
// ============================================================

function buildBox(icon, text, bgColor, iconColor) {
  return new Paragraph({
    children: [
      new TextRun({ text: icon + '  ', font: 'Arial', size: FONT.body, bold: true, color: iconColor }),
      ...parseInline(text)
    ],
    shading: { fill: bgColor, type: ShadingType.CLEAR },
    spacing: { before: 160, after: 160 },
    indent: { left: 360, right: 360 }
  });
}

// ============================================================
// Haupt-Parser: Markdown → docx Elemente
// ============================================================

function parseMarkdown(content) {
  const lines   = content.split('\n');
  const result  = [];        // Array of Paragraphs/Tables
  let i         = 0;

  let inCodeBlock  = false;
  let codeLines    = [];
  let inTable      = false;
  let tableRows    = [];
  let skipNextEmpty = false;

  // Helper: flush table
  function flushTable() {
    if (tableRows.length === 0) return;
    // Filter out separator rows (|---|---|)
    const dataRows = tableRows.filter(r => !r.match(/^\|[\s\-:|]+\|$/));
    const tbl = buildTable(dataRows);
    if (tbl) {
      result.push(tbl);
      result.push(new Paragraph({ spacing: { before: 80, after: 80 }, children: [new TextRun('')] }));
    }
    tableRows = [];
    inTable = false;
  }

  while (i < lines.length) {
    const raw  = lines[i];
    const line = raw.trimEnd();

    // ── Code blocks ────────────────────────────────────────────
    if (line.startsWith('```')) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeLines   = [];
      } else {
        inCodeBlock = false;
        if (codeLines.length > 0) {
          const codeText = codeLines.join('\n');
          result.push(new Paragraph({
            children: [new TextRun({
              text: codeText, font: 'Courier New', size: FONT.code, color: '333333'
            })],
            shading: { fill: COLORS.codeBg, type: ShadingType.CLEAR },
            spacing: { before: 160, after: 160 },
            indent: { left: 360, right: 360 }
          }));
        }
      }
      i++; continue;
    }

    if (inCodeBlock) {
      codeLines.push(raw);
      i++; continue;
    }

    // ── Tables ─────────────────────────────────────────────────
    if (line.startsWith('|')) {
      if (!inTable) { inTable = true; tableRows = []; }
      tableRows.push(line);
      i++;
      if (i >= lines.length || !lines[i].startsWith('|')) {
        flushTable();
      }
      continue;
    } else if (inTable) {
      flushTable();
    }

    // ── Skip TOC links  [Text](#anchor) ────────────────────────
    if (line.match(/^- \[.+\]\(#.+\)/)) {
      i++; continue;
    }

    // ── Skip document title line ────────────────────────────────
    if (line === '# Benutzerhandbuch – Betreuer-App') {
      i++; continue;
    }

    // ── Skip YAML-like metadata lines ──────────────────────────
    if (line.startsWith('**CREDO Gruppe') || line.startsWith('Version 1.0')) {
      i++; continue;
    }

    // ── Teil A / B / C / D / E → Trennseite ────────────────────
    const teilMatch = line.match(/^# Teil ([A-E]):\s*(.+)/);
    if (teilMatch) {
      const letter = teilMatch[1];
      const title  = teilMatch[2];
      const labels = {
        A: 'Für Administratoren (Personalverwaltung)',
        B: 'Für Koordinatoren (Lehrer & Pädagogen)',
        C: 'Für Betreuer (Schülerinnen & Schüler)',
        D: 'Für N8N-Workflowbauer (IT & Support)',
        E: 'Prozessbeschreibungen nach ISO 9001',
      };
      result.push(...buildSectionPage(`TEIL ${letter}`, labels[letter] || title));
      i++; continue;
    }

    // ── Headings ────────────────────────────────────────────────
    if (line.startsWith('#### ')) {
      result.push(new Paragraph({
        heading: HeadingLevel.HEADING_4,
        children: parseInline(line.slice(5).trim())
      }));
      i++; continue;
    }
    if (line.startsWith('### ')) {
      result.push(new Paragraph({
        heading: HeadingLevel.HEADING_3,
        children: parseInline(line.slice(4).trim())
      }));
      i++; continue;
    }
    if (line.startsWith('## ')) {
      result.push(new Paragraph({
        heading: HeadingLevel.HEADING_2,
        children: parseInline(line.slice(3).trim())
      }));
      i++; continue;
    }
    if (line.startsWith('# ')) {
      result.push(new Paragraph({
        heading: HeadingLevel.HEADING_1,
        children: parseInline(line.slice(2).trim())
      }));
      i++; continue;
    }

    // ── Horizontal rule → Spacer ────────────────────────────────
    if (line.trim() === '---') {
      result.push(new Paragraph({
        spacing: { before: 160, after: 160 },
        children: [new TextRun({ text: '', font: 'Arial' })],
        border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary } }
      }));
      i++; continue;
    }

    // ── Warning ⚠️ ──────────────────────────────────────────────
    if (line.startsWith('⚠️') || line.startsWith('⚠')) {
      const text = line.replace(/^⚠️?\s*(ACHTUNG:?\s*)?/, '').trim();
      result.push(buildBox('⚠', text, COLORS.warnBg, 'E2001A'));
      i++; continue;
    }

    // ── Info ℹ️ ─────────────────────────────────────────────────
    if (line.startsWith('ℹ️') || line.startsWith('ℹ')) {
      const text = line.replace(/^ℹ️?\s*(HINWEIS:?\s*)?/, '').trim();
      result.push(buildBox('i', text, COLORS.infoBg, '009AC6'));
      i++; continue;
    }

    // ── Tip ✅ ──────────────────────────────────────────────────
    if (line.startsWith('✅')) {
      const text = line.replace(/^✅\s*(TIPP:?\s*|Tipp:?\s*)?/, '').trim();
      result.push(buildBox('✓', text, COLORS.tipBg, '6BAA24'));
      i++; continue;
    }

    // ── Screenshot placeholder [SCREENSHOT: ...] ─────────────────
    if (line.startsWith('[SCREENSHOT:')) {
      const text = line.replace(/^\[SCREENSHOT:\s*/, '').replace(/\]$/, '').trim();
      result.push(new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({
          text: `[ Abbildung: ${text} ]`,
          font: 'Arial', size: FONT.body, italics: true, color: '888888'
        })],
        shading: { fill: COLORS.screenshotBg, type: ShadingType.CLEAR },
        spacing: { before: 240, after: 240 },
        border: {
          top:    { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
          bottom: { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
          left:   { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
          right:  { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
        }
      }));
      i++; continue;
    }

    // ── Bullet list  - item ──────────────────────────────────────
    if (line.match(/^[-*]\s+/)) {
      const text = line.replace(/^[-*]\s+/, '').trim();
      result.push(new Paragraph({
        numbering: { reference: 'bullets', level: 0 },
        children: parseInline(text),
        spacing: { before: 60, after: 60 }
      }));
      i++; continue;
    }

    // ── Numbered list  1. item ───────────────────────────────────
    const numMatch = line.match(/^(\d+)\.\s+(.+)/);
    if (numMatch) {
      const text = numMatch[2].trim();
      result.push(new Paragraph({
        numbering: { reference: 'numbers', level: 0 },
        children: parseInline(text),
        spacing: { before: 60, after: 60 }
      }));
      i++; continue;
    }

    // ── Empty line ───────────────────────────────────────────────
    if (line.trim() === '') {
      // Add small spacing paragraph only if previous wasn't also empty
      if (result.length > 0) {
        result.push(new Paragraph({
          spacing: { before: 40, after: 40 },
          children: [new TextRun('')]
        }));
      }
      i++; continue;
    }

    // ── Normal paragraph ─────────────────────────────────────────
    result.push(new Paragraph({
      children: parseInline(line.trim()),
      spacing: { before: 80, after: 80 }
    }));

    i++;
  }

  // Flush any remaining table
  if (inTable) flushTable();

  return result;
}

// ============================================================
// Deckblatt
// ============================================================

const today   = new Date();
const dateStr = today.toLocaleDateString('de-DE', { year: 'numeric', month: 'long' });

function buildCoverPage() {
  return [
    // Grauer Balken oben
    new Paragraph({
      children: [new TextRun({ text: ' '.repeat(100), font: 'Arial', size: 96 })],
      shading:  { fill: COLORS.primary, type: ShadingType.CLEAR },
      spacing:  { before: 0, after: 0 }
    }),
    // Spacer
    new Paragraph({ spacing: { before: 2000, after: 0 }, children: [new TextRun('')] }),
    // Organisation
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 240 },
      children:  [new TextRun({ text: 'CREDO Gruppe', font: 'Arial', size: 36, bold: true, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 2400 },
      children:  [new TextRun({ text: 'Christlicher Schulverein Minden e.V.', font: 'Arial', size: 26, color: COLORS.dark })]
    }),
    // Haupttitel
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 480 },
      children:  [new TextRun({ text: 'BENUTZERHANDBUCH', font: 'Arial', size: 80, bold: true, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 3000 },
      children:  [new TextRun({ text: 'Betreuer-App', font: 'Arial', size: 56, color: COLORS.dark })]
    }),
    // Version & Datum
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 240 },
      children:  [new TextRun({ text: 'Version 1.0', font: 'Arial', size: 22, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 2000 },
      children:  [new TextRun({ text: dateStr, font: 'Arial', size: 22, color: COLORS.dark })]
    }),
    // CREDO-Linie (Farbbalken simuliert durch farbige Block-Zeichen)
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing:   { before: 0, after: 0 },
      children:  [
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.primary }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.yellow }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.green }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.red }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588',   font: 'Arial', size: 28, color: COLORS.blue }),
      ]
    }),
    // Seitenumbruch
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ============================================================
// Header und Footer
// ============================================================

function buildHeader() {
  return new Header({
    children: [
      new Paragraph({
        children: [
          new TextRun({
            text: 'CREDO Gruppe \u2013 Betreuer-App Benutzerhandbuch',
            font: 'Arial', size: FONT.small, color: COLORS.dark
          }),
          new TextRun({ children: [new Tab()], font: 'Arial' }),
          new TextRun({
            children: [PageNumber.CURRENT],
            font: 'Arial', size: FONT.small, color: COLORS.dark
          }),
        ],
        tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
        border:  { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLORS.primary } },
        spacing: { after: 200 }
      })
    ]
  });
}

function buildFooter() {
  return new Footer({
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing:   { before: 160 },
        border:    { top: { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary } },
        children:  [
          new TextRun({
            text: 'Christlicher Schulverein Minden e.V. \u2022 Kingsleyallee 6 \u2022 32425 Minden',
            font: 'Arial', size: FONT.footer, color: COLORS.dark
          })
        ]
      })
    ]
  });
}

// ============================================================
// Dokument aufbauen
// ============================================================

console.log('\u{1F4D6} Lese Handbuch-Entwurf...');
const contentParagraphs = parseMarkdown(handbuchContent);
console.log(`   -> ${contentParagraphs.length} Elemente geparst`);

const doc = new Document({
  styles,
  numbering,
  sections: [
    // ─── Deckblatt (eigene Sektion ohne Header/Footer) ─────────
    {
      properties: {
        page: {
          size:   { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children: buildCoverPage()
    },

    // ─── Hauptinhalt ────────────────────────────────────────────
    {
      properties: {
        page: {
          size:   { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1440, bottom: 1800, left: 1440 }
        }
      },
      headers: { default: buildHeader() },
      footers: { default: buildFooter() },
      children: contentParagraphs
    }
  ]
});

// ============================================================
// Speichern
// ============================================================

const outputPath = path.join(__dirname, 'Benutzerhandbuch_CREDO.docx');

console.log('\u{1F4BE} Erstelle Word-Dokument...');

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  const sizeKB = Math.round(buffer.length / 1024);
  console.log(`\u2705 Word-Dokument erstellt: ${outputPath}`);
  console.log(`   Dateigr\u00f6\u00dfe: ${sizeKB} KB`);
  console.log(`   Elemente: ${contentParagraphs.length}`);
  console.log(`   Datum: ${dateStr}`);
}).catch(err => {
  console.error('\u274C Fehler beim Erstellen:', err.message);
  if (err.stack) console.error(err.stack);
  process.exit(1);
});

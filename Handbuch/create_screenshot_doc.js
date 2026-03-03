/**
 * create_screenshot_doc.js
 * Erstellt eine Screenshot-Dokumentation der Betreuer-App als Word-Dokument
 * Alle drei Rollen: Admin, Koordinator, Betreuer
 *
 * Ausführen: node Handbuch/create_screenshot_doc.js
 */

'use strict';

const {
  Document, Packer, Paragraph, TextRun, ImageRun,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle,
  ShadingType, PageBreak, WidthType, Table, TableRow, TableCell,
  VerticalAlign, TabStopType, TabStopPosition, Tab, PageNumber,
  LevelFormat
} = require('docx');

const fs   = require('fs');
const path = require('path');

// ============================================================
// CREDO CI
// ============================================================
const COLORS = {
  primary: 'DADADA',
  dark:    '575756',
  yellow:  'FBC900',
  green:   '6BAA24',
  red:     'E2001A',
  blue:    '009AC6',
  black:   '000000',
  white:   'FFFFFF',
  admin:   '575756',   // Dunkelgrau für Admin-Abschnitt
  koord:   '009AC6',   // Blau für Koordinator-Abschnitt
  betr:    '6BAA24',   // Grün für Betreuer-Abschnitt
  all:     'FBC900',   // Gelb für Alle-Rollen
};

const FONT   = { h1: 64, h2: 48, h3: 36, h4: 26, body: 22, small: 18, footer: 16, code: 20 };
const SCRS   = path.join(__dirname, 'screenshots');
const MANIFEST = JSON.parse(fs.readFileSync(path.join(SCRS, 'manifest.json'), 'utf8'));

// ============================================================
// Hilfsfunktionen
// ============================================================

function loadImage(filename) {
  const p = path.join(SCRS, filename);
  if (!fs.existsSync(p)) return null;
  return fs.readFileSync(p);
}

function roleColor(role) {
  if (role.includes('Admin'))       return COLORS.admin;
  if (role.includes('Koordinator')) return COLORS.koord;
  if (role.includes('Betreuer'))    return COLORS.betr;
  return COLORS.all;
}

function roleBadge(role) {
  return new Paragraph({
    spacing: { before: 0, after: 120 },
    children: [
      new TextRun({
        text: `  Rolle: ${role}  `,
        font: 'Arial', size: FONT.small, bold: true,
        color: COLORS.white,
        highlight: undefined,
        shading: { fill: roleColor(role), type: ShadingType.CLEAR }
      })
    ]
  });
}

function buildHeader() {
  return new Header({
    children: [new Paragraph({
      children: [
        new TextRun({ text: 'CREDO Gruppe \u2013 Betreuer-App Bildschirmreferenz', font: 'Arial', size: FONT.small, color: COLORS.dark }),
        new TextRun({ children: [new Tab()], font: 'Arial' }),
        new TextRun({ children: [PageNumber.CURRENT], font: 'Arial', size: FONT.small, color: COLORS.dark }),
      ],
      tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
      border:  { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLORS.primary } },
      spacing: { after: 200 }
    })]
  });
}

function buildFooter() {
  return new Footer({
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      border: { top: { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary } },
      spacing: { before: 160 },
      children: [new TextRun({
        text: 'Christlicher Schulverein Minden e.V. \u2022 Kingsleyallee 6 \u2022 32425 Minden',
        font: 'Arial', size: FONT.footer, color: COLORS.dark
      })]
    })]
  });
}

// Trennseite für eine Rollengruppe
function buildRolePage(roleLabel, roleColor, roleDesc) {
  return [
    new Paragraph({ children: [new PageBreak()] }),
    new Paragraph({
      shading: { fill: roleColor, type: ShadingType.CLEAR },
      alignment: AlignmentType.CENTER,
      spacing: { before: 2880, after: 480 },
      children: [new TextRun({ text: roleLabel, font: 'Arial', size: 80, bold: true, color: COLORS.white })]
    }),
    new Paragraph({
      shading: { fill: roleColor, type: ShadingType.CLEAR },
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 2880 },
      children: [new TextRun({ text: roleDesc, font: 'Arial', size: 36, color: COLORS.white })]
    }),
    new Paragraph({
      shading: { fill: roleColor, type: ShadingType.CLEAR },
      alignment: AlignmentType.CENTER,
      spacing: { before: 0, after: 0 },
      children: [new TextRun({ text: ' '.repeat(200), font: 'Arial', size: 48 })]
    }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// Screenshot-Eintrag: Titel + Badge + Bild + Beschreibung
function buildScreenshotEntry(item) {
  const paragraphs = [];
  const imgData = loadImage(item.file.split('/').pop().split('\\').pop());

  // Abschnitts-Überschrift
  paragraphs.push(new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text: item.label, font: 'Arial', size: FONT.h3, bold: true, color: COLORS.dark })],
    spacing: { before: 360, after: 120 }
  }));

  // Rollen-Badge
  paragraphs.push(new Paragraph({
    spacing: { before: 0, after: 160 },
    children: [
      new TextRun({ text: 'Rolle: ', font: 'Arial', size: FONT.small, bold: true, color: COLORS.dark }),
      new TextRun({ text: item.role, font: 'Arial', size: FONT.small, bold: true, color: roleColor(item.role) }),
    ]
  }));

  // Screenshot-Bild
  if (imgData) {
    try {
      paragraphs.push(new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 160, after: 160 },
        children: [
          new ImageRun({
            data: imgData,
            transformation: {
              width:  640,
              height: 400,
            },
            type: 'png',
          })
        ],
        border: {
          top:    { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
          bottom: { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
          left:   { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
          right:  { style: BorderStyle.SINGLE, size: 4, color: COLORS.primary },
        }
      }));
    } catch (e) {
      paragraphs.push(new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: `[Bild: ${item.label}]`, font: 'Arial', size: FONT.body, italics: true, color: '888888' })],
        spacing: { before: 160, after: 160 }
      }));
    }
  }

  // Beschreibung
  paragraphs.push(new Paragraph({
    spacing: { before: 80, after: 320 },
    children: [new TextRun({ text: item.description, font: 'Arial', size: FONT.body, color: COLORS.dark })]
  }));

  // Trennlinie
  paragraphs.push(new Paragraph({
    spacing: { before: 0, after: 240 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 2, color: COLORS.primary } },
    children: [new TextRun('')]
  }));

  return paragraphs;
}

// ============================================================
// Deckblatt
// ============================================================
const today   = new Date();
const dateStr = today.toLocaleDateString('de-DE', { year: 'numeric', month: 'long' });

function buildCoverPage() {
  return [
    new Paragraph({
      children: [new TextRun({ text: ' '.repeat(100), font: 'Arial', size: 96 })],
      shading:  { fill: COLORS.primary, type: ShadingType.CLEAR },
      spacing:  { before: 0, after: 0 }
    }),
    new Paragraph({ spacing: { before: 1440, after: 0 }, children: [new TextRun('')] }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: 'CREDO Gruppe', font: 'Arial', size: 36, bold: true, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 0, after: 2000 },
      children: [new TextRun({ text: 'Christlicher Schulverein Minden e.V.', font: 'Arial', size: 26, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: 'BILDSCHIRMREFERENZ', font: 'Arial', size: 80, bold: true, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: 'Betreuer-App', font: 'Arial', size: 56, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: 'Screenshots aller Ansichten nach Rolle', font: 'Arial', size: 28, italics: true, color: COLORS.dark })]
    }),
    new Paragraph({ spacing: { before: 1440, after: 0 }, children: [new TextRun('')] }),
    // Rollen-Übersicht als farbige Tabelle
    new Table({
      width: { size: 70, type: WidthType.PERCENTAGE },
      rows: [
        new TableRow({ children: [
          new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'ADMIN', font: 'Arial', size: 24, bold: true, color: COLORS.white })] })], shading: { fill: COLORS.admin, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 } }),
          new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'KOORDINATOR', font: 'Arial', size: 24, bold: true, color: COLORS.white })] })], shading: { fill: COLORS.koord, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 } }),
          new TableCell({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'BETREUER', font: 'Arial', size: 24, bold: true, color: COLORS.white })] })], shading: { fill: COLORS.betr, type: ShadingType.CLEAR }, margins: { top: 120, bottom: 120, left: 200, right: 200 } }),
        ]})
      ]
    }),
    new Paragraph({ spacing: { before: 1440, after: 240 }, children: [new TextRun('')] }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 0, after: 240 },
      children: [new TextRun({ text: 'Version 1.0  \u2022  ' + dateStr, font: 'Arial', size: 22, color: COLORS.dark })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 0, after: 0 },
      children: [
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.primary }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.yellow }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.green }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588  ', font: 'Arial', size: 28, color: COLORS.red }),
        new TextRun({ text: '\u2588\u2588\u2588\u2588\u2588',  font: 'Arial', size: 28, color: COLORS.blue }),
      ]
    }),
    new Paragraph({ children: [new PageBreak()] }),
  ];
}

// ============================================================
// Inhaltsverzeichnis-Seite
// ============================================================
function buildTOC() {
  const items = [];
  items.push(new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text: 'Inhalt dieser Dokumentation', font: 'Arial', size: FONT.h1, bold: true, color: COLORS.dark })],
    spacing: { before: 0, after: 480 }
  }));

  const sections = [
    { label: 'ADMIN', color: COLORS.admin, items: MANIFEST.screenshots.filter(s => s.role.includes('Admin')) },
    { label: 'KOORDINATOR', color: COLORS.koord, items: MANIFEST.screenshots.filter(s => s.role.includes('Koordinator')) },
    { label: 'BETREUER', color: COLORS.betr, items: MANIFEST.screenshots.filter(s => s.role.includes('Betreuer') && !s.role.includes('Admin') && !s.role.includes('Koordinator')) },
    { label: 'ALLE ROLLEN', color: COLORS.all, items: MANIFEST.screenshots.filter(s => s.role === 'Alle') },
  ];

  for (const sec of sections) {
    if (sec.items.length === 0) continue;
    items.push(new Paragraph({
      spacing: { before: 240, after: 120 },
      children: [new TextRun({ text: sec.label, font: 'Arial', size: FONT.h4, bold: true, color: sec.color })]
    }));
    for (const item of sec.items) {
      items.push(new Paragraph({
        spacing: { before: 60, after: 60 },
        indent: { left: 360 },
        children: [
          new TextRun({ text: '\u2022  ', font: 'Arial', size: FONT.body, color: sec.color }),
          new TextRun({ text: item.label, font: 'Arial', size: FONT.body, color: COLORS.black }),
        ]
      }));
    }
  }

  items.push(new Paragraph({ children: [new PageBreak()] }));
  return items;
}

// ============================================================
// Haupt-Content aufbauen
// ============================================================
function buildContent() {
  const content = [];
  const shots   = MANIFEST.screenshots;

  // GEMEINSAME SEITEN (Login, Profil, Passwort)
  const commonItems = shots.filter(s => s.role === 'Alle');
  if (commonItems.length > 0) {
    content.push(...buildRolePage('ALLE ROLLEN', COLORS.all, 'Login \u2022 Profil \u2022 Passwort'));
    content.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: 'Gemeinsame Ansichten (alle Rollen)', font: 'Arial', size: FONT.h1, bold: true, color: COLORS.dark })],
      spacing: { before: 0, after: 240 }
    }));
    content.push(new Paragraph({
      spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: 'Diese Seiten sind für alle Benutzer zugänglich – unabhängig von der zugewiesenen Rolle.', font: 'Arial', size: FONT.body, italics: true, color: COLORS.dark })]
    }));
    for (const item of commonItems) content.push(...buildScreenshotEntry(item));
  }

  // ADMIN
  const adminItems = shots.filter(s => s.role.includes('Admin') && !s.role.includes('Koordinator'));
  if (adminItems.length > 0) {
    content.push(...buildRolePage('ADMIN', COLORS.admin, 'Vollzugriff auf alle Schulen und Betreuer'));
    content.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: 'Admin-Ansichten', font: 'Arial', size: FONT.h1, bold: true, color: COLORS.admin })],
      spacing: { before: 0, after: 240 }
    }));
    content.push(new Paragraph({
      spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: 'Der Administrator hat Zugriff auf alle Schulen, alle Betreuer und alle Funktionen der App.', font: 'Arial', size: FONT.body, italics: true, color: COLORS.dark })]
    }));
    for (const item of adminItems) content.push(...buildScreenshotEntry(item));
  }

  // ADMIN + KOORDINATOR (gemeinsame Ansichten)
  const sharedItems = shots.filter(s => s.role.includes('Admin') && s.role.includes('Koordinator'));
  if (sharedItems.length > 0) {
    content.push(new Paragraph({ children: [new PageBreak()] }));
    content.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: 'Gemeinsame Ansichten: Admin & Koordinator', font: 'Arial', size: FONT.h1, bold: true, color: COLORS.admin })],
      spacing: { before: 0, after: 240 }
    }));
    content.push(new Paragraph({
      spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: 'Diese Ansichten sind für beide Rollen verfügbar. Der Koordinator sieht dabei nur Daten seiner eigenen Schule(n).', font: 'Arial', size: FONT.body, italics: true, color: COLORS.dark })]
    }));
    for (const item of sharedItems) content.push(...buildScreenshotEntry(item));
  }

  // KOORDINATOR
  const koordItems = shots.filter(s => s.role === 'Koordinator');
  if (koordItems.length > 0) {
    content.push(...buildRolePage('KOORDINATOR', COLORS.koord, 'Schulbezogene Verwaltung und Genehmigungen'));
    content.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: 'Koordinator-Ansichten', font: 'Arial', size: FONT.h1, bold: true, color: COLORS.koord })],
      spacing: { before: 0, after: 240 }
    }));
    content.push(new Paragraph({
      spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: 'Der Koordinator verwaltet Betreuer seiner Schule, prüft Stundennachweise und erstellt Einladungslinks.', font: 'Arial', size: FONT.body, italics: true, color: COLORS.dark })]
    }));
    for (const item of koordItems) content.push(...buildScreenshotEntry(item));
  }

  // BETREUER
  const betItems = shots.filter(s => s.role === 'Betreuer');
  if (betItems.length > 0) {
    content.push(...buildRolePage('BETREUER', COLORS.betr, 'Zeiterfassung und eigene Daten'));
    content.push(new Paragraph({
      heading: HeadingLevel.HEADING_1,
      children: [new TextRun({ text: 'Betreuer-Ansichten', font: 'Arial', size: FONT.h1, bold: true, color: COLORS.betr })],
      spacing: { before: 0, after: 240 }
    }));
    content.push(new Paragraph({
      spacing: { before: 0, after: 480 },
      children: [new TextRun({ text: 'Der Betreuer erfasst seine Arbeitsstunden, reicht Monatsnachweise ein und verwaltet seine eigenen Profilinformationen.', font: 'Arial', size: FONT.body, italics: true, color: COLORS.dark })]
    }));
    for (const item of betItems) content.push(...buildScreenshotEntry(item));
  }

  return content;
}

// ============================================================
// Dokument erstellen
// ============================================================
console.log('📖 Lese Screenshot-Manifest...');
console.log(`   -> ${MANIFEST.screenshots.length} Screenshots gefunden`);

const coverChildren  = buildCoverPage();
const tocChildren    = buildTOC();
const mainChildren   = buildContent();

const doc = new Document({
  styles: {
    default: { document: { run: { font: 'Arial', size: FONT.body, color: COLORS.black } } }
  },
  sections: [
    // Deckblatt
    {
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      children: coverChildren
    },
    // Inhaltsverzeichnis
    {
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1800, left: 1440 } } },
      headers: { default: buildHeader() },
      footers: { default: buildFooter() },
      children: tocChildren
    },
    // Hauptinhalt
    {
      properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, right: 1440, bottom: 1800, left: 1440 } } },
      headers: { default: buildHeader() },
      footers: { default: buildFooter() },
      children: mainChildren
    }
  ]
});

const outputPath = path.join(__dirname, 'BildschirmReferenz_CREDO.docx');
console.log('💾 Erstelle Word-Dokument...');

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log(`\n✅ Dokument erstellt: ${outputPath}`);
  console.log(`   Größe: ${Math.round(buffer.length / 1024)} KB`);
  console.log(`   Screenshots eingebettet: ${MANIFEST.screenshots.length}`);
  console.log(`   Erstellt am: ${dateStr}`);
}).catch(err => {
  console.error('❌ Fehler:', err.message);
  console.error(err.stack);
  process.exit(1);
});

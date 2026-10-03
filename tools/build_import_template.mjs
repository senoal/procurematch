import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = "outputs/data-intake";
const previewDir = `${outputDir}/previews`;
const outputPath = `${outputDir}/purchase_order_import_template.xlsx`;
const workbook = Workbook.create();
const font = "Arial";
const colors = {
  ink: "#171716",
  paper: "#F2EFE6",
  white: "#FFFDF7",
  blue: "#2449FF",
  acid: "#C9F73A",
  gray: "#DEDACF",
  red: "#D53F35",
};

function applyBase(sheet, range) {
  sheet.showGridLines = false;
  range.format.font = { name: font, size: 10, color: colors.ink };
  range.format.verticalAlignment = "center";
}

function styleInputSheet(sheet, title, note, headers, rows, tableName, widths) {
  sheet.getRange(`A1:${String.fromCharCode(64 + headers.length)}1`).merge();
  sheet.getRange("A1").values = [[title]];
  sheet.getRange("A1").format = {
    font: { name: font, size: 15, bold: true, color: colors.ink },
    rowHeight: 28,
  };
  sheet.getRange(`A2:${String.fromCharCode(64 + headers.length)}2`).merge();
  sheet.getRange("A2").values = [[note]];
  sheet.getRange("A2").format = {
    font: { name: font, size: 9, italic: true, color: "#6B6861" },
    rowHeight: 22,
  };
  const headerEnd = String.fromCharCode(64 + headers.length);
  sheet.getRange(`A4:${headerEnd}4`).values = [headers];
  sheet.getRange(`A5:${headerEnd}${4 + rows.length}`).values = rows;
  applyBase(sheet, sheet.getRange(`A1:${headerEnd}${Math.max(10, 4 + rows.length)}`));
  sheet.getRange(`A4:${headerEnd}4`).format = {
    fill: colors.ink,
    font: { name: font, size: 9, bold: true, color: colors.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    rowHeight: 26,
    borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
  };
  sheet.getRange(`A5:${headerEnd}${4 + rows.length}`).format.fill = colors.white;
  sheet.getRange(`A5:${headerEnd}${4 + rows.length}`).format.borders = {
    insideHorizontal: { style: "thin", color: "#D5D1C7" },
  };
  sheet.tables.add(`A4:${headerEnd}${4 + rows.length}`, true, tableName).style = "TableStyleMedium2";
  widths.forEach((width, index) => {
    sheet.getRangeByIndexes(0, index, 10, 1).format.columnWidth = width;
  });
  sheet.freezePanes.freezeRows(4);
  sheet.tabColor = colors.blue;
}

const instructions = workbook.worksheets.add("Instructions");
instructions.getRange("A1:F1").merge();
instructions.getRange("A1").values = [["Purchase Order Import Template"]];
instructions.getRange("A3:F3").merge();
instructions.getRange("A3").values = [["Cara menggunakan template"]];
instructions.getRange("A5:B9").values = [
  ["1", "Isi satu baris untuk setiap produk dalam dokumen."],
  ["2", "Gunakan nomor dokumen yang sama untuk dokumen dengan beberapa produk."],
  ["3", "Gunakan tanggal berformat YYYY-MM-DD."],
  ["4", "Jangan mengubah nama sheet atau header kolom."],
  ["5", "Unggah workbook melalui menu Data Intake."],
];
instructions.getRange("A11:F11").merge();
instructions.getRange("A11").values = [["Urutan pemrosesan: PurchaseOrders, GoodsReceipts, lalu Invoices."]];
applyBase(instructions, instructions.getRange("A1:F14"));
instructions.getRange("A1:F1").format = { font: { name: font, size: 16, bold: true, color: colors.ink }, rowHeight: 32 };
instructions.getRange("A3:F3").format = { fill: colors.ink, font: { name: font, size: 10, bold: true, color: colors.white }, rowHeight: 24 };
instructions.getRange("A5:A9").format = { fill: colors.acid, font: { name: font, size: 10, bold: true, color: colors.ink }, horizontalAlignment: "center" };
instructions.getRange("B5:B9").format.wrapText = true;
instructions.getRange("A11:F11").format = { fill: "#E3E6FF", font: { name: font, size: 9, bold: true, color: colors.blue }, rowHeight: 24 };
instructions.getRange("A1:A14").format.columnWidth = 7;
instructions.getRange("B1:B14").format.columnWidth = 58;
instructions.tabColor = colors.ink;

const po = workbook.worksheets.add("PurchaseOrders");
styleInputSheet(
  po,
  "Purchase Orders",
  "Supplier dan produk akan dibuat atau diperbarui berdasarkan kode dan SKU.",
  ["po_number", "supplier_code", "supplier_name", "order_date", "expected_date", "product_sku", "product_name", "quantity", "unit_price"],
  [["PO-2026-100", "SUP-100", "PT Demo Supplier", new Date("2026-10-03"), new Date("2026-10-10"), "PRD-100", "Demo Product", 25, 150000]],
  "PurchaseOrdersTable",
  [17, 16, 28, 14, 15, 16, 27, 12, 16],
);
po.getRange("D5:E200").format.numberFormat = "yyyy-mm-dd";
po.getRange("H5:H200").format.numberFormat = "#,##0.00";
po.getRange("I5:I200").format.numberFormat = "#,##0";
po.getRange("H5:H200").dataValidation = { rule: { type: "decimal", operator: "greaterThan", formula1: 0 } };
po.getRange("I5:I200").dataValidation = { rule: { type: "decimal", operator: "greaterThanOrEqual", formula1: 0 } };

const receipts = workbook.worksheets.add("GoodsReceipts");
styleInputSheet(
  receipts,
  "Goods Receipts",
  "PO dan SKU harus sudah tersedia pada sheet PurchaseOrders atau di database.",
  ["receipt_number", "po_number", "receipt_date", "product_sku", "quantity"],
  [["GR-2026-100", "PO-2026-100", new Date("2026-10-09"), "PRD-100", 25]],
  "GoodsReceiptsTable",
  [19, 18, 15, 18, 13],
);
receipts.getRange("C5:C200").format.numberFormat = "yyyy-mm-dd";
receipts.getRange("E5:E200").format.numberFormat = "#,##0.00";
receipts.getRange("E5:E200").dataValidation = { rule: { type: "decimal", operator: "greaterThan", formula1: 0 } };

const invoices = workbook.worksheets.add("Invoices");
styleInputSheet(
  invoices,
  "Invoices",
  "Supplier, PO, dan SKU harus sudah tersedia. Matching berjalan setelah impor berhasil.",
  ["invoice_number", "po_number", "supplier_code", "invoice_date", "product_sku", "quantity", "unit_price"],
  [["INV-2026-100", "PO-2026-100", "SUP-100", new Date("2026-10-10"), "PRD-100", 25, 150000]],
  "InvoicesTable",
  [19, 18, 17, 15, 18, 13, 17],
);
invoices.getRange("D5:D200").format.numberFormat = "yyyy-mm-dd";
invoices.getRange("F5:F200").format.numberFormat = "#,##0.00";
invoices.getRange("G5:G200").format.numberFormat = "#,##0";
invoices.getRange("F5:F200").dataValidation = { rule: { type: "decimal", operator: "greaterThan", formula1: 0 } };
invoices.getRange("G5:G200").dataValidation = { rule: { type: "decimal", operator: "greaterThanOrEqual", formula1: 0 } };

workbook.recalculate();
await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["Instructions", "PurchaseOrders", "GoodsReceipts", "Invoices"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${previewDir}/${sheetName}.png`, new Uint8Array(await preview.arrayBuffer()));
}
const check = await workbook.inspect({
  kind: "table",
  range: "PurchaseOrders!A1:I5",
  include: "values,formulas",
  tableMaxRows: 8,
  tableMaxCols: 10,
});
console.log(check.ndjson);
const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 50 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);
await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);

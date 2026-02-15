# Google Sheets

**Important:** Use `gog sheets get`, not `gog sheets read`. The command name is `get`.

## Reading a Spreadsheet

To read a spreadsheet, first discover the sheet names, then read with a proper A1 range:

```bash
# Step 1: Get sheet names and structure
gog sheets metadata <spreadsheetId>

# Step 2: Read values using A1 notation (sheet name + cell range)
gog sheets get <spreadsheetId> 'SheetName!A1:Z100'
```

The range argument is **required** and must use A1 notation: `SheetName!A1:B10`. A bare sheet name like `Sheet1` will fail — always include the cell range (e.g. `Sheet1!A1:Z100`).

```bash
gog sheets get <spreadsheetId> 'Sheet1!A1:B10'
gog sheets get <spreadsheetId> 'Sheet1!A1:B10' --json
gog sheets get <spreadsheetId> 'Sheet1!A:Z'              # All rows in columns A-Z
gog sheets get <spreadsheetId> 'Sheet1!A1:B10' --render FORMULA
```

## Update Values

Values use pipe `|` to separate cells and comma `,` to separate rows.

```bash
gog sheets update <spreadsheetId> 'A1' 'val1|val2,val3|val4'
gog sheets update <spreadsheetId> 'Sheet1!A1:C1' 'new|row|data'
gog sheets update <spreadsheetId> 'A1' --values-json '[["a","b"],["c","d"]]'
gog sheets update <spreadsheetId> 'A1' 'raw data' --input RAW
gog sheets update <spreadsheetId> 'Sheet1!A1:C1' 'data' --copy-validation-from 'Sheet1!A2:C2'
```

Flags: `--input` (RAW/USER_ENTERED, default USER_ENTERED), `--values-json`, `--copy-validation-from`

## Append Values

```bash
gog sheets append <spreadsheetId> 'Sheet1!A:C' 'new|row|data'
gog sheets append <spreadsheetId> 'Sheet1!A:C' --values-json '[["a","b","c"]]'
gog sheets append <spreadsheetId> 'Sheet1!A:C' 'data' --insert INSERT_ROWS
gog sheets append <spreadsheetId> 'Sheet1!A:C' 'data' --copy-validation-from 'Sheet1!A2:C2'
```

Flags: `--input` (RAW/USER_ENTERED, default USER_ENTERED), `--insert` (OVERWRITE/INSERT_ROWS), `--values-json`, `--copy-validation-from`

## Clear Values

```bash
gog sheets clear <spreadsheetId> 'Sheet1!A1:B10'
```

## Format Cells

```bash
gog sheets format <spreadsheetId> 'Sheet1!A1:B2' \
  --format-json '{"textFormat":{"bold":true}}' \
  --format-fields 'userEnteredFormat.textFormat.bold'
```

Flags: `--format-json` (Sheets API CellFormat JSON), `--format-fields` (field mask)

## Cell Notes

```bash
gog sheets notes <spreadsheetId> 'Sheet1!A1:B10'
```

## Metadata

```bash
gog sheets metadata <spreadsheetId>
```

## Create

```bash
gog sheets create "My New Spreadsheet"
gog sheets create "My Spreadsheet" --sheets "Sheet1,Sheet2"
```

Flags: `--sheets` (comma-separated sheet names)

## Copy

```bash
gog sheets copy <spreadsheetId> "My Sheet Copy"
gog sheets copy <spreadsheetId> "My Sheet Copy" --parent <folderId>
```

Flags: `--parent`

## Export

```bash
gog sheets export <spreadsheetId> --format xlsx --out ./sheet.xlsx
gog sheets export <spreadsheetId> --format pdf --out ./sheet.pdf
gog sheets export <spreadsheetId> --format csv --out ./sheet.csv
```

Flags: `--out`, `--format` (pdf/xlsx/csv, default xlsx)

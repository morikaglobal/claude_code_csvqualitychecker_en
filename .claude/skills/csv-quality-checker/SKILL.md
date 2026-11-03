---
name: csv-quality-checker
description: Checks a CSV file for data quality issues. Use when the user asks to validate, check, or profile a CSV file.
---

# CSV Quality Check

When checking a CSV file, follow these steps in order:

1. Read the file. Report the row count and column names.
2. Check for these issues:
   - Missing values (empty cells)
   - Duplicate rows
   - Invalid dates
   - Negative numbers in quantity or price columns
3. For each issue, report:
   - The row number
   - The column
   - Severity: high, medium, or low
   - A suggested fix
4. End with a one-line summary: total issues found.
5. DO NOT modify the original file.
6. **Generate HTML Dashboard**: After reporting issues, run the Python script below to generate an HTML dashboard and publish it as an Artifact.

## HTML Dashboard Generation

After completing steps 1-4, run the CSV Quality Checker Python script:

```bash
python .claude/skills/csv-quality-checker/csv_quality_checker.py <csv_file>
```

This script will:
- Analyze the CSV file using the same quality checks
- Generate a styled HTML dashboard with:
  - Summary stats (row count, column count, issue count by severity)
  - Issues summary table with row, column, issue description, and severity
- Output the HTML between markers:
  - Start: `<!-- DASHBOARD_START -->`
  - End: `<!-- DASHBOARD_END -->`

Then:
1. Capture the HTML output from between the markers
2. Publish it to an Artifact with:
   - Title: "CSV Quality Dashboard"
   - Icon: "table"
   - Description: "Data quality issues for [filename]"
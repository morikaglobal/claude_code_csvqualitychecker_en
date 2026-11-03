#!/usr/bin/env python3
"""CSV Quality Checker with HTML Dashboard Generator"""

import csv
import sys
from datetime import datetime
from collections import defaultdict

def read_csv(filepath):
    """Read CSV file and return rows and column names."""
    rows = []
    columns = []

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames if reader.fieldnames else []
        for i, row in enumerate(reader, start=2):  # Start at 2 (after header)
            rows.append((i, row))

    return columns, rows

def is_valid_date(date_str):
    """Check if date string is in YYYY-MM-DD format and valid."""
    if not date_str or not isinstance(date_str, str):
        return False

    try:
        # Check format
        parts = date_str.split('-')
        if len(parts) != 3:
            return False

        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

        # Check ranges
        if not (1900 <= year <= 2100):
            return False
        if not (1 <= month <= 12):
            return False
        if not (1 <= day <= 31):
            return False

        # Try to parse as actual date
        datetime(year, month, day)
        return True
    except (ValueError, TypeError):
        return False

def check_csv_quality(filepath):
    """Analyze CSV for quality issues."""
    columns, rows = read_csv(filepath)
    issues = []

    # Track seen rows for duplicate detection
    seen_rows = {}

    for row_num, row_data in rows:
        row_values = tuple(row_data.values())

        # Check for duplicates
        if row_values in seen_rows:
            issues.append({
                'row': row_num,
                'column': 'All',
                'issue': f'Duplicate of row {seen_rows[row_values]}',
                'severity': 'medium'
            })
        else:
            seen_rows[row_values] = row_num

        # Check each column
        for col in columns:
            value = row_data.get(col, '').strip()

            # Missing values
            if not value:
                issues.append({
                    'row': row_num,
                    'column': col,
                    'issue': 'Missing value',
                    'severity': 'high'
                })
                continue

            # Invalid dates
            if col.lower() in ['date', 'order_date', 'created_at', 'updated_at']:
                if not is_valid_date(value):
                    issues.append({
                        'row': row_num,
                        'column': col,
                        'issue': f'Invalid date format: {value}',
                        'severity': 'high'
                    })

            # Negative quantities/prices
            if col.lower() in ['quantity', 'qty', 'amount', 'price', 'unit_price', 'cost']:
                try:
                    num_value = float(value)
                    if num_value < 0:
                        issues.append({
                            'row': row_num,
                            'column': col,
                            'issue': f'Negative value: {value}',
                            'severity': 'high'
                        })
                except ValueError:
                    # Non-numeric value
                    issues.append({
                        'row': row_num,
                        'column': col,
                        'issue': f'Invalid value (expected number): {value}',
                        'severity': 'high'
                    })

    return {
        'filepath': filepath,
        'columns': columns,
        'row_count': len(rows),
        'rows': rows,
        'issues': issues
    }

def generate_html_dashboard(data):
    """Generate HTML dashboard from CSV analysis."""
    issues = data['issues']
    row_count = data['row_count']
    columns = data['columns']
    rows = data['rows']

    # Count severity levels
    severity_counts = defaultdict(int)
    for issue in issues:
        severity_counts[issue['severity']] += 1

    total_issues = len(issues)
    high_count = severity_counts['high']
    medium_count = severity_counts['medium']

    # Build issues table rows
    issues_html = ''
    for issue in sorted(issues, key=lambda x: x['row']):
        severity_class = f"severity-{issue['severity']}"
        issues_html += f"""
                <tr>
                    <td>{issue['row']}</td>
                    <td>{issue['column']}</td>
                    <td>{issue['issue']}</td>
                    <td><span class="{severity_class}">{issue['severity'].upper()}</span></td>
                </tr>
        """

    # Build data table with highlights
    # Map issues by (row, column)
    issue_map = defaultdict(list)
    duplicate_map = {}  # row_num -> list of duplicate row numbers

    for issue in issues:
        if issue['column'] == 'All' and 'Duplicate' in issue['issue']:
            # Parse "Duplicate of row X"
            parts = issue['issue'].split('row ')
            if len(parts) > 1:
                try:
                    dup_row = int(parts[1])
                    if issue['row'] not in duplicate_map:
                        duplicate_map[issue['row']] = []
                    duplicate_map[issue['row']].append(dup_row)
                    if dup_row not in duplicate_map:
                        duplicate_map[dup_row] = []
                    duplicate_map[dup_row].append(issue['row'])
                except ValueError:
                    pass
        else:
            issue_map[(issue['row'], issue['column'])].append(issue)

    # Assign duplicate group IDs
    duplicate_groups = {}
    group_id = 0
    processed = set()

    for row in duplicate_map.keys():
        if row not in processed:
            group = {row}
            stack = [row]
            while stack:
                current = stack.pop()
                if current in duplicate_map:
                    for dup in duplicate_map[current]:
                        if dup not in group:
                            group.add(dup)
                            stack.append(dup)

            for r in group:
                duplicate_groups[r] = group_id
                processed.add(r)
            group_id += 1

    # Build data table
    data_table_html = '<thead><tr><th>Row</th>'
    for col in columns:
        data_table_html += f'<th>{col}</th>'
    data_table_html += '</tr></thead><tbody>'

    for row_num, row_data in rows:
        data_table_html += '<tr>'
        data_table_html += f'<td class="row-num">{row_num}</td>'

        for col in columns:
            value = row_data.get(col, '').strip()
            cell_class = ''

            # Check for issues in this cell
            cell_issues = issue_map.get((row_num, col), [])

            if cell_issues:
                for issue in cell_issues:
                    if 'Missing value' in issue['issue']:
                        cell_class = 'highlight-missing'
                    else:
                        cell_class = 'highlight-error'
                    break

            # Add duplicate group styling
            if row_num in duplicate_groups:
                if cell_class:
                    cell_class += f' dup-group-{duplicate_groups[row_num]}'
                else:
                    cell_class = f'dup-group-{duplicate_groups[row_num]}'

            display_value = value if value else '<em>empty</em>'
            if cell_class:
                data_table_html += f'<td class="{cell_class}">{display_value}</td>'
            else:
                data_table_html += f'<td>{display_value}</td>'

        data_table_html += '</tr>'

    data_table_html += '</tbody>'

    # Generate duplicate group CSS
    duplicate_colors = ['#e879f9', '#f97316', '#06b6d4', '#a16207', '#7c3aed', '#dc2626', '#2563eb']
    duplicate_css = ''
    for group_id in range(len(duplicate_groups)):
        color = duplicate_colors[group_id % len(duplicate_colors)]
        duplicate_css += f"""
        .dup-group-{group_id} {{
            background-color: {color} !important;
            color: white;
            font-weight: bold;
        }}
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSV Quality Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            margin: 0;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-top: 0;
            font-size: 24px;
        }}
        h2 {{
            color: #333;
            font-size: 16px;
            margin-top: 30px;
            margin-bottom: 15px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 10px;
        }}
        .stats {{
            display: flex;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .stat-card {{
            padding: 12px 16px;
            background: #f9f9f9;
            border-left: 4px solid #3b82f6;
            border-radius: 4px;
        }}
        .stat-card.error {{
            border-left-color: #ef4444;
        }}
        .stat-card.warning {{
            border-left-color: #f59e0b;
        }}
        .stat-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-top: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            font-size: 14px;
        }}
        th {{
            background: #f3f4f6;
            color: #374151;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        tr:hover {{
            background: #fafafa;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .row-num {{
            color: #999;
            font-weight: 500;
            background: #f3f4f6;
        }}
        .issues-table th {{
            background: #fee2e2;
            color: #7f1d1d;
        }}
        .data-table th {{
            background: #f0fdf4;
            color: #166534;
        }}
        .severity-high {{
            color: #dc2626;
            font-weight: bold;
        }}
        .severity-medium {{
            color: #ea580c;
            font-weight: bold;
        }}
        .severity-low {{
            color: #059669;
            font-weight: bold;
        }}
        em {{
            color: #999;
            font-style: italic;
        }}
        .highlight-missing {{
            background-color: #fef3c7 !important;
            color: #92400e;
            font-weight: bold;
        }}
        .highlight-error {{
            background-color: #fee2e2 !important;
            color: #991b1b;
            font-weight: bold;
        }}
        {duplicate_css}
        .legend {{
            margin-top: 20px;
            padding: 15px;
            background: #f9fafb;
            border-radius: 6px;
            border-left: 4px solid #3b82f6;
        }}
        .legend-item {{
            display: inline-block;
            margin-right: 20px;
            margin-bottom: 8px;
        }}
        .legend-color {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 3px;
            margin-right: 8px;
            vertical-align: middle;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 CSV Quality Dashboard</h1>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total Rows</div>
                <div class="stat-value">{row_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Columns</div>
                <div class="stat-value">{len(columns)}</div>
            </div>
            <div class="stat-card {'error' if total_issues > 0 else ''}">
                <div class="stat-label">Issues Found</div>
                <div class="stat-value">{total_issues}</div>
            </div>
            <div class="stat-card error">
                <div class="stat-label">High Severity</div>
                <div class="stat-value">{high_count}</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-label">Medium Severity</div>
                <div class="stat-value">{medium_count}</div>
            </div>
        </div>

        <h2>⚠️ Issues Summary</h2>
        <table class="issues-table">
            <thead>
                <tr>
                    <th>Row</th>
                    <th>Column</th>
                    <th>Issue</th>
                    <th>Severity</th>
                </tr>
            </thead>
            <tbody>
                {issues_html if issues_html else '<tr><td colspan="4" style="text-align: center; color: #059669;">✓ No issues found</td></tr>'}
            </tbody>
        </table>

        <h2>📋 Data Preview with Issues</h2>
        <div class="legend">
            <strong>Legend:</strong><br>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #fef3c7;"></span>
                <strong>Yellow</strong> = Missing value
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #fee2e2;"></span>
                <strong>Red</strong> = Invalid or problematic value
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #e879f9;"></span>
                <strong>Colored</strong> = Duplicate rows (same color = same duplicate group)
            </div>
        </div>
        <table class="data-table">
            {data_table_html}
        </table>
    </div>
</body>
</html>
"""
    return html

def main():
    if len(sys.argv) < 2:
        print("Usage: python csv_quality_checker.py <csv_file>")
        sys.exit(1)

    filepath = sys.argv[1]

    try:
        data = check_csv_quality(filepath)
        html = generate_html_dashboard(data)

        print("<!-- DASHBOARD_START -->")
        print(html)
        print("<!-- DASHBOARD_END -->")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

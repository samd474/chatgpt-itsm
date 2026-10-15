import csv
import io

from django.http import HttpResponse

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def escape_cell(value):
    """Neutralise spreadsheet formula injection in exported cells."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def csv_response(filename, header, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for row in rows:
        writer.writerow([escape_cell(value) for value in row])
    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response

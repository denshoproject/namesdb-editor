import codecs
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List, Match, Optional, Set, Tuple, Union


# Some files' XMP data is wayyyyyy too big
csv.field_size_limit(sys.maxsize)
CSV_DELIMITER = ','
CSV_QUOTECHAR = '"'
CSV_QUOTING = csv.QUOTE_ALL

def csv_reader(csvfile):
    """Get a csv.reader object for the file.
    
    @param csvfile: A file object.
    """
    reader = csv.reader(
        csvfile,
        delimiter=CSV_DELIMITER,
        quoting=CSV_QUOTING,
        quotechar=CSV_QUOTECHAR,
    )
    return reader

def csv_writer(csvfile):
    """Get a csv.writer object for the file.
    
    @param csvfile: A file object.
    """
    writer = csv.writer(
        csvfile,
        delimiter=CSV_DELIMITER,
        quoting=CSV_QUOTING,
        quotechar=CSV_QUOTECHAR,
    )
    return writer

def csv_str_writer():
    output = io.StringIO()
    writer = csv.writer(
        output,
        delimiter=CSV_DELIMITER,
        quoting=CSV_QUOTING,
        quotechar=CSV_QUOTECHAR,
    )
    return output,writer

def read_csv(
        path: str,
        offset: Optional[int]=0,
        limit: Optional[int]=1_000_000,
) -> List[Dict[str,str]]:
    """Read specified file, returns list of rows.
    
    >>> path = '/tmp/batch-test_write_csv.csv'
    >>> csv_file = '"id","title","description"\r\n"ddr-test-123","thing 1","nothing here"\r\n"ddr-test-124","thing 2","still nothing"\r\n'
    >>> with open(path, 'w') as f:
    ...    f.write(csv_file)
    >>> batch.read_csv(path)
    [
        ['id', 'title', 'description'],
        ['ddr-test-123', 'thing 1', 'nothing here'],
        ['ddr-test-124', 'thing 2', 'still nothing']
    ]
    
    Throws Exception if file contains text that can't be decoded to UTF-8.
    
    @param path: Absolute path to CSV file
    @returns list of rows
    """
    offset += 1  # Account for row 0 (headers)
    limit  += 1  #
    rows = []
    with open(path, 'r') as f:
        reader = csv_reader(f)
        n = 0
        for index,row in enumerate(reader):
            # Skip rows before offset, but always get rowd 0 with headers
            if (index != 0) and (index < offset):
                continue
            n += 1
            if limit and n > limit:
                break
            rows.append(row)
    return rows

def write_csv_str(row: Dict[str,str]) -> str:
    """Write row to CSV formatted str
    
    TODO refactor. This makes a new CSV writer, writes a line, closes the output,
    and discards the writer for each row, so it's probably really inefficient
    """
    output,writer = csv_str_writer()
    writer.writerow(row)
    contents = output.getvalue()
    output.close()
    return contents.strip()

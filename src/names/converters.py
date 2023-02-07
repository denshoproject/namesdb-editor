# Various ways to represent structured data in strings,
# for use in web forms or in CSV files.
#
# Some of these methods are extremely similar to each other, but they
# originated in different places in the app or different points in the
# process.  They are collected here to document the various formats
# used, and hopefully to make it easier to merge or prune them in the
# future.

import copy
from datetime import datetime
import json
import logging
logger = logging.getLogger(__name__)
import re
from typing import Any, Dict, List, Match, Optional, Set, Tuple, Union

from jinja2 import Template


def normalize_string(text: str) -> str:
    if text == None:
        return u''
    elif not isinstance(text, str):
        return text
    elif not text:
        return u''
    return str(text).replace('\r\n', '\n').replace('\r', '\n').strip()

def load_dirty_json(text: str):
    # http://grimhacker.com/2016/04/24/loading-dirty-json-with-python/
    regex_replace = [
        (r"([ \{,:\[])(u)?'([^']+)'", r'\1"\3"'),
        (r" False([, \}\]])", r' false\1'),
        (r" True([, \}\]])", r' true\1')
    ]
    for r, s in regex_replace:
        text = re.sub(r, s, text)
    return json.loads(text)

def strip_list(data: List[Any]) -> List[Any]:
    """Remove empty list items (ex: ['not empty, '']
   
    @param data: list
    @returns: list
    """
    return [
        item for item in data
        if item and (not item == 0)
    ]

def render(template: str, data: Dict[str, str]) -> str:
    """Render a Jinja2 template.
    
    @param template: str Jinja2-formatted template
    @param data: dict
    """
    return Template(template).render(data=data)

def coerce_text(data: Union[int,datetime,str]) -> Optional[str]:
    """Ensure types (ints,datetimes) are converted to text
    """
    if isinstance(data, int):
        return str(data)
    elif isinstance(data, datetime):
        return datetime_to_text(data)
    return data


# boolean --------------------------------------------------------------
# datetime -------------------------------------------------------------
# list ----------------------------------------------------------------
## dict -----------------------------------------------------------------

TEXT_BRACKETID_TEMPLATE = '{term} [{id}]'
TEXT_BRACKETID_REGEX = re.compile(r'(?P<term>[\w\d -:()_,`\'"]+)\s\[(?P<id>\d+)\]')
 
def _is_text_bracketid(text: str) -> Union[Match[str], bool]:
    if text:
        m = re.search(TEXT_BRACKETID_REGEX, text)
        if m and (len(m.groups()) == 2) and m.groups()[1].isdigit():
            return m
    return False


# listofdicts ----------------------------------------------------------

def _is_listofdicts(data: Union[Any, List[Dict[str,str]]]) -> bool:
    if isinstance(data, list):
        num_dicts = 0
        for x in data:
            if isinstance(x, dict):
                num_dicts += 1
        if num_dicts == len(data):
            return True
    return False


# rolepeople -----------------------------------------------------------
#
# List listofdicts but adds default key:val pairs if missing
# 
# text = ''
# data = []
# 
# text = "Watanabe, Joe"
# data = [
#     {'namepart': 'Watanabe, Joe', 'role': 'author'}
# ]
# 
# text = "Masuda, Kikuye [42]:narrator"
# data = [
#     {'namepart': 'Masuda, Kikuye', 'role': 'narrator', 'id': 42}
# ]
# 
# text = "Watanabe, Joe:author; Masuda, Kikuye:narrator"
# text = [
#     'Watanabe, Joe: author',
#     'Masuda, Kikuye [42]: narrator'
# ]
# text = [
#     {'namepart': 'Watanabe, Joe', 'role': 'author'}
#     {'namepart': 'Masuda, Kikuye', 'role': 'narrator', 'id': 42}
# ]
# data = [
#     {'namepart': 'Watanabe, Joe', 'role': 'author'}
#     {'namepart': 'Masuda, Kikuye', 'role': 'narrator', 'id': 42}
# ]
#

def _filter_rolepeople(data: List[Dict[str,str]]) -> List[Dict[str,str]]:
    """filters out items with empty nameparts
    prevents this: [{'namepart': '', 'role': 'author'}]
    """
    return [
        item for item in data
        if item.get('namepart')  # and item.get('role')
    ]

# TODO add type hints
def _parse_rolepeople_text(texts, default):
    data = []
    for text in _unroll_gloppy_list(texts):
        txt = text.strip()
        if txt:
            item = copy.deepcopy(default)
            
            if ('|' in txt) and (':' in txt):
                # ex: "namepart:Sadako Kashiwagi|role:narrator|id:856"
                for chunk in txt.split('|'):
                    key,val = chunk.split(':')
                    item[key.strip()] = val.strip()
                if item.get('name') and not item.get('namepart'):
                    item['namepart'] = item.pop('name')
            
            elif ':' in txt:
                # ex: "Sadako Kashiwagi:narrator"
                # ex: 'namepart: Yasuda, Mitsu;\n'
                key,value = txt.split(':')
                if key.strip() in default.keys():
                    # ex: 'namepart: Yasuda, Mitsu;\n'
                    item[key.strip()] = value.strip()
                else:
                    # ex: "Sadako Kashiwagi:narrator"
                    item['namepart'] = key.strip()
                    item['role'] = value.strip()
            
            else:
                # ex: "Sadako Kashiwagi"
                item['namepart'] = txt
            
            # extract person ID if present
            match = _is_text_bracketid(item.get('namepart',''))
            if match:
                item['namepart'] = match.groupdict()['term'].strip()
                item['id'] = match.groupdict()['id'].strip()
            if item.get('id') and item['id'].isdigit():
                item['id'] = int(item['id'])
            
            data.append(item)
    return data

def _unroll_gloppy_list(text: list) -> List[str]:
    """Lists of rolepeople from e.g. forms might have multiple items in a line
    
    e.g. ['Lastname1,Firstname1; Lastname2,Firstname2', 'Lastname3,Firstname3']
    """
    new_list = []
    while(text):
        # split if there are more than one items in a listitem
        # append the first item to the new list
        items = text.pop(0).split(';', 1) # split on the first semicolon
        if len(items) == 1:
            new_list.append(items[0].strip())  # the last one
        elif len(items) > 1:
            first,others = items
            new_list.append(first.strip())
            # stick remainders onto front of list to preserve order
            new_list.insert(0, others.strip())
    return new_list

def text_to_rolepeople(text: str, default: dict) -> List[Dict[str,str]]:
    if not text:
        return []
    
    # might already be listofdicts or listofstrs
    if isinstance(text, list):
        if _is_listofdicts(text):
            return _filter_rolepeople(text)
        elif _is_listofstrs(text):
            data = _parse_rolepeople_text(text, default)
            return _filter_rolepeople(data)
    
    text = normalize_string(text)
    
    # or it might be JSON
    if ('{' in text) or ('[' in text):
        try:
            data = json.loads(text)
        except ValueError:
            try:
                data = load_dirty_json(text)
            except ValueError:
                data = []
        if data:
            return _filter_rolepeople(data)
    
    # looks like it's raw text
    data = _parse_rolepeople_text(text.split(';'), default)
    return _filter_rolepeople(data)

def rolepeople_to_text(data: List[Dict[str,str]]) -> str:
    """Convert list of dicts to string "KEY:VAL|KEY:VAL|...; KEY:VAL|KEY:VAL|..."
    """
    if isinstance(data, str):
        text = data
    else:
        items = []
        for d in data:
            # strings probably formatted or close enough
            if isinstance(d, str):
                items.append(d)
            elif isinstance(d, dict):
                items.append(
                    ' | '.join(
                        [f'{key}: {val}' for key,val in d.items()]
                    )
                )
        text = '; '.join(items).strip()
    return text

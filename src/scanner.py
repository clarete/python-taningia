# -*- coding: utf-8; -*-
#
# Copyright (C) 2009, 2010  Lincoln de Sousa <lincoln@comum.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

"""Header scanner

This program is intended to scan .h files and extract docstrings and C
code definitions, like functions, typedefs, enums and others. To make
our life easier and avoid the needing of write a scanner as robust as
GCC's one, we need to enforce a strict coding style and some others
standards in our library. If one of these standers is broken, this
scanner will, at least, complain.

These are our standards (restrictions =P):

 * Docstrings are different from normal documentation. They start with
   the '/**' chars instead of just '/*'.
 * Types have the `ta_' prefix and the `_t' sufix, to structs, enums,
   delegates and etc.
 * All exposed API is declared in lower case.
 * The scanner doesn't handle symbols that doesn't have a docstring.
 * (Currently) Macros are not found by this scanner.
 * Delegates should name its parameters.

This scanner has two basic targets, docstrings and C
definitions. Docstrings are easy to parse and understand, as they
start with /** and end with */ but C symbols are not so simple, so we
have a special piece of code to handle each supported C definition.
The currently supported types are:

 * typedef enum
 * typedef struct
 * functions
 * delegates (typedefs to function pointers)

Nothing else is currently supported. This program was designed to be
easily changed but there are no special mechanism to extend its
capabilities.

Some considerations about the implementation

 * This code will not be run everytime, so we should prefer
   readability and manutenability than optimization.

 * We will only use regular expressions where it makes our job
   easier. In other words, where it is hard to do with simple string
   manipulation. Just to keep things easier to understand.

"""

import os
import re
import warnings
import simplejson
import tags

#
# ---- Some useful regular expressions used along the program ----
#

TYPE_PAT = re.compile('typedef struct _.+ ([^;]+_t)')

TYPE_PAT2 = re.compile('typedef struct[^{]*{[^}]*}\s*([^;]+_t)')

ENUM_PAT = re.compile('(?:typedef\s)?enum {([^}]*)} ([^;]+)')

FUNC_PAT = \
    re.compile('((?:const\s+)?\w+\s*\**)\s*([a-z0-9\_]+)\s*\(([^\)]+)\)')

PARAM_PAT = re.compile('((?:const\s+)?\w+\s*\**)(\w+)')

DELEGATE_PAT = re.compile('typedef (\w+)\s*\*?\s*\(([^\)]+)\)\s*\(([^\)]+)\)')

#
# ---- Docstring parsing functions ----
#

def find_docstrings(buf):
    """Docstring finding function.

    This simple method finds strings starting with /** and ending
    with */. It excludes edges of the found strings, like this::

        >>> find_docstrings('we have a docstring here /** blah blah blah */')
        [' blah blah blah ']

        >>> find_docstrings('''/** Another docstring
        ...  * now with multiple lines
        ...  * as you see */
        ... code code code''')
        [' Another docstring\\n * now with multiple lines\\n * as you see ']

        >>> find_docstrings('/** first ds */ blah /** second ds */ blah blah')
        [' first ds ', ' second ds ']

        >>> find_docstrings('/* blah blah */ test test test')
        []
    """
    result = []
    lastidx = 0
    while True:
        start = buf.find('/**', lastidx)
        stop = buf.find('*/', start)
        if start >= 0:
            result.append(buf[start+3:stop])
            lastidx = stop
        else:
            break
    return result

def parse_docstring(dstring):
    """Docstring parsing function.

    This function receives a single docstring to be parsed. This work
    consists in simply separate description from the rest of the
    docstring and find tags that starts with the `@' char and ends
    with the start of another `@' or with the end of the string.

    As said above, before starting to find tags, the description
    piece, that is separated from the rest of the docstring is
    splitted. The chars that marks the description start are '\n\n'.

    For example::

      >>> ds = '''
      ...  * @name: ta_iri
      ...  * @type: class
      ...  *
      ...  * Implementation of the Internationalized Resource Identifiers
      ...  * standard defined by the RFC 3987. This implementation is not
      ...  * complete yet, there are some really important things ...
      ... '''

    The above docstring has two tags and the description field. To
    split them up a simple `ds.split("\n\n")' is done. After that,
    tags are parsed by their handlers.

    This function returns a dictionary and its keys are the
    description and all other found tags. The value of the
    `description' field is a normal string, the value of each tag
    depends on its type. To know more about the tag formats, see the
    `tags.py' module.

    All docstrings should have at least two tags: `name' and
    `type'. All other tags are not required.

    Each tag is another dict containing the result of parsing of the
    single tag. The parsing functions can be found in the `tags.py'
    module.

    For our above example, this should be the result::

      >>> parsed = parse_docstring(ds)
      >>> isinstance(parsed, dict)
      True
      >>> parsed.keys()
      ['type', 'description', 'name']

    Getting the description::

      >>> print parsed['description']
      Implementation of the Internationalized Resource Identifiers
      standard defined by the RFC 3987. This implementation is not
      complete yet, there are some really important things ...

    Handling tags. Each tag iter is another object containing the info
    of a single parsed tag, each tag parser can return a different
    object, like this::

      >>> parsed['name']
      {'name': 'ta_iri'}

      >>> parsed['type']
      {'name': 'class'}

    """
    ret = {}

    # Clearing `*' chars from the docstring
    newbuf = []
    for i in dstring.split('\n'):
        line = re.sub('^\s*\*\s*', '', i).strip()
        newbuf.append(line)

    # Splitting tags from description
    broken = '\n'.join(newbuf).split('\n\n')
    description = ''
    if len(broken) > 1:
        description = broken[1].strip()
    ret['description'] = description

    # Looking for tags and parsing them
    dvars = re.findall('@([^:]+):\s*([^@]+)', broken[0])
    for key, val in dvars:
        rkey = key.split(' ')[0]
        # If we don't know a tag, we just make user aware, there is no
        # need to stop anything.
        try:
            parsed = getattr(tags, 'tag_%s' % rkey)(val)
            if key == 'param':
                # Creating the list that will hold found
                # parameters. This will only be present when finding
                # at least one @param tag and it should only happen in
                # methods (functions in general).
                if ret.get('params') is None:
                    ret['params'] = []
                ret['params'].append(parsed)
            else:
                # Handling all other tags that are just a new entry in
                # the return dict.
                ret[key] = parsed
        except AttributeError:
            warnings.warn('Unknown tag %s' % key)
    return ret

def get_parsed_docstrings(buf):
    """Since `parse_docstring' function parses a single docstring, we
    wrote this helper function that finds all docstrings and parses
    them.

    The return of this function is a dictionary containing all parsed
    docstrings found in a file. The keys of this dict are the `name'
    tag values.

      >>> buf = '''
      ... /**
      ...  * @name: test
      ...  * @type: class
      ...  *
      ...  * This is a simple test docstring class.
      ...  */
      ... '''
      >>> from pprint import pprint
      >>> pprint(get_parsed_docstrings(buf))
      {'test': {'description': 'This is a simple test docstring class.',
                'name': 'test',
                'type': {'name': 'class'}}}
    """
    ret = {}
    for i in find_docstrings(buf):
        parsed = parse_docstring(i)
        try:
            key = '%(class)s_%(name)s' % parsed['name']
        except KeyError:
            key = parsed['name']['name']
        ret[key] = parsed
    return ret

#
# ---- File scanning functions ----
#

def strip_spaces(buf):
    """Replace all whitespaces to a single whitespace, like::

       >>> strip_spaces('ta_atom_content_t          *')
       'ta_atom_content_t *'
    """
    while buf.find('  ') != -1:
        buf = buf.replace('  ', ' ')
    return buf.strip()

def strip_comments(buf):
    """Strip C multiline comments from `buf'.

      >>> strip_comments('''
      ... /* blah blah */
      ... this is a test buffer
      ... /* blah
      ...    multi line comment
      ...  */
      ... 1, 2, 3, ...
      ... ''')
      '\\n\\nthis is a test buffer\\n\\n1, 2, 3, ...\\n'
    """
    newbuf = []
    lastidx = 0
    while 1:
        idx = buf.find('/*', lastidx)
        if idx >= 0:
            newbuf.append(buf[lastidx:idx])
            idx = buf.find('*/', idx)
            if idx >= 0:
                lastidx = idx + 2
            else:
                break
        else:
            newbuf.append(buf[lastidx:])
            break
    return ''.join(newbuf)

def find_types(buf):
    """Find C types in a buffer.
    """
    return TYPE_PAT.findall(buf) + TYPE_PAT2.findall(buf)

def find_enums(buf):
    """Find enum definitions in a buffer.
    """
    enums = []
    for i in ENUM_PAT.findall(buf):
        econt, name = i
        econt = strip_spaces(econt.replace('\n', ''))
        vals = [x.strip() for x in econt.split(',') if x]
        isflags = '<<' in econt
        if isflags:
            entries = []
            for i in vals:
                entry = i.split('=')[0].strip()
                entries.append(entry)
        else:
            entries = vals
        enums.append({
                'name': name,
                'isflags': isflags,
                'entries': entries
        })
    return enums

def find_delegates(buf):
    """Finds delegates (typedefs to functions) in a buffer.

    This is a very important kind of data to provide to a binding
    generator script. This will allow it to write wrappers
    dynamically, instead of needing to write a glue code for each
    function that receives a function pointer.

    This is a simple example of how it works::

      >>> code = '''/** delegate blah ... */
      ... typedef int *(*ta_list_cmp_func_t) (void *a, void *b);
      ... /* more pieces of code... */
      ... '''
      >>> from pprint import pprint
      >>> pprint(find_delegates(code))
      [{'cname': 'ta_list_cmp_func_t',
        'params': [{'name': 'a', 'type': 'void *'},
                   {'name': 'b', 'type': 'void *'}],
        'rtype': 'int'}]
    """
    found = []
    for ret, name, params in DELEGATE_PAT.findall(buf):
        found.append({'cname': name.replace('*', '').strip(),
                      'rtype': ret.strip(),
                      'params': clear_params(params),
                      })
    return found

def clear_params(params):
    """Scan the `params' string and return a dict with parsed
    information.

      >>> from pprint import pprint
      >>> pprint(clear_params('const char *p1, int p2, ta_iri_t *iri'))
      [{'name': 'p1', 'type': 'const char *'},
       {'name': 'p2', 'type': 'int'},
       {'name': 'iri', 'type': 'ta_iri_t *'}]

    We do handle void parameters! In this case, we have no parameters
    actually::

      >>> clear_params('void')
      []

    There is no problem if catched parameters has tralling or leading
    whitespaces, both are stripped::

      >>> clear_params(' void ')
      []
    """
    new_params = []

    # Cleaning params string and splitting params with comma
    params = params.replace('\n', '')
    eparams = params.split(',')

    # Params dict has the following fields: name and type.
    for i in eparams:
        param = i.strip()
        if param == 'void':
            # This means that the function has no parameters.
            continue
        elif param == '...':
            # This is not being handled actually. We are just passing
            # the responsability to the user of this information.
            ptype = 'varargs'
            name = ''
        else:
            found = PARAM_PAT.findall(i)
            ptype, name = found[0]
        new_params.append({
                'type': ptype.strip(),
                'name': name,
        })
    return new_params

def find_functions(buf):
    """Find constructors, destructors, getters, setters and normal
    methods in a buffer.

    It actually looks for C functions, like this::

      >>> content = '''
      ... int my_func (const char *param1, int param2, void *param3);
      ... '''
      >>> from pprint import pprint
      >>> pprint(find_functions(content))
      [{'name': 'my_func',
        'params': [{'name': 'param1', 'type': 'const char *'},
                   {'name': 'param2', 'type': 'int'},
                   {'name': 'param3', 'type': 'void *'}],
        'rtype': 'int'}]
    """
    methods = []
    for i in FUNC_PAT.findall(buf):
        rtype, name, params = i
        if rtype.strip() == 'typedef':
            # Our regular expression is not smart enough to avoid
            # finding all kinds of delegates when looking for
            # functions and two lines here are better then changing
            # the RE and make it more complex.
            continue
        pparams = clear_params(params)
        methods.append({
                'name': name,
                'rtype': rtype.strip(),
                'params': pparams,
        })
    return methods

def get_parsed_code(buf):
    """Clear spaces and comments from the buffer and then looks for
    types, enums and functions in it and return them.

    This function is just a facility that calls all code parsing
    functions.

      >>> code = '''
      ... typedef struct
      ... {
      ...   char *blah;
      ...   int blah;
      ... } myclass_t;
      ...
      ... typedef struct _otherclass otherclass_t;
      ...
      ... typedef enum {
      ...   CLASS_BLAH
      ... } blah_enum_t;
      ...
      ... enum {
      ...   E_VAL1,
      ...   E_VAL2
      ... } e_vals;
      ...
      ... enum {
      ...   F1 = 1 << 1,
      ...   F2 = 1 << 2,
      ...   F3 = 1 << 3
      ... } myflags;
      ...
      ... typedef int *(*my_cmp_func) (void *a, void *b);
      ...
      ... '''
      >>> from pprint import pprint
      >>> pprint(get_parsed_code(code))
      {'delegates': [{'cname': 'my_cmp_func',
                      'params': [{'name': 'a', 'type': 'void *'},
                                 {'name': 'b', 'type': 'void *'}],
                      'rtype': 'int'}],
       'enums': [{'entries': ['CLASS_BLAH'],
                  'isflags': False,
                  'name': 'blah_enum_t'},
                 {'entries': ['E_VAL1', 'E_VAL2'],
                  'isflags': False,
                  'name': 'e_vals'},
                 {'entries': ['F1', 'F2', 'F3'],
                  'isflags': True,
                  'name': 'myflags'}],
       'functions': [],
       'types': ['otherclass_t', 'myclass_t', 'blah_enum_t']}
    """
    content = strip_spaces(strip_comments(buf))
    types = find_types(content)
    enums = find_enums(content)
    functions = find_functions(content)
    delegates = find_delegates(content)
    return dict(types=types, enums=enums, functions=functions,
                delegates=delegates)

def purge_lib_prefix(name):
    """Purges the ta_ prefix from a string, like this::

      >>> purge_lib_prefix('ta_iri')
      'iri'

      >>> purge_lib_prefix('ta_tag')
      'tag'
    """
    return re.sub('^ta_', '', name)

def purge_type_sufix(name):
    """Purges the _t sufix from a string, like this::

      >>> purge_type_sufix('ta_iri_t')
      'ta_iri'

    This is safe enough to only get rid of the *last* _t, see the
    example::

      >>> purge_type_sufix('test_test_t')
      'test_test'
    """
    return re.sub('_t$', '', name)

def scan_file(fname):
    """Open a header file and collect both docstrings and code stuff.

    This function returns a module description. The module name is
    built from the basename of file.
    """
    # Extracting information from code and docstrings with our helper
    # functions.
    content = open(fname).read()
    code = get_parsed_code(content)
    doc = get_parsed_docstrings(content)

    # Building module header
    module = dict()
    module['name'] = os.path.basename(os.path.splitext(fname)[0])
    module['types'] = {}
    module['functions'] = {}
    module['enums'] = code['enums']
    module['delegates'] = {}

    # Adding classes to our module
    for cname in code['types']:
        tname = purge_type_sufix(cname)
        docstring = doc.get(tname, {})
        module['types'][tname] = docstring
        module['types'][tname]['cname'] = cname

    # Removing enums from types list
    for enum in module['enums']:
        try:
            del module['types'][purge_type_sufix(enum['name'])]
        except KeyError:
            pass

    # Adding functions to our module
    for function in code['functions']:
        fname = function['name']
        try:
            # Getting docstring information for the handled function.
            fds = doc[fname]
        except KeyError:
            warnings.warn('Cowardly refusing to add function %s without '
                          'a docstring =(' % fname)
            continue

        # Before updatting function dict with docstring stuff we need
        # to save docstrings parameters.
        oldparams = fds.get('params')
        if oldparams:
            # This entry is being deleted to avoid overriding data got
            # from code when updating. Manual merging will be done
            # bellow.
            del fds['params']

            # Updating parameters of handled function with data from
            # docstring.
            for i in function['params']:
                for j in oldparams:
                    if i['name'] == j['name']:
                        i.update(j)

        # Updating data collected from code with docstring info.
        function.update(fds)
        class_name = function['name'].get('class')
        if class_name:
            # associating the method to a class.
            try:
                cls = module['types'][class_name]
            except KeyError:
                # Just customizing the exception output.
                raise KeyError('No such class %s in %s' % (
                        class_name, module['types'].keys()))
            cls_methods = cls.get('methods')
            if not cls_methods:
                cls['methods'] = []
                cls_methods = cls['methods']
            cls_methods.append(function)
        else:
            # If this code is reached, it means that the function is
            # not associated to any class.
            mfuncs = module.get('functions')
            if not mfuncs:
                module['functions'] = []
            module['functions'].append(function)

    # Adding delegates to our brand new module
    for delegate in code['delegates']:
        rname = purge_type_sufix(delegate['cname'])
        try:
            delegate.update(doc[rname])
        except KeyError:
            warnings.warn('Cowardly refusing to add delegate %s.%s without '
                          'a docstring =(' % (module['name'], rname))
            continue
        module['delegates'][rname] = delegate
    return module

def scan_files(files):
    """Executes the `scan_file' function for all files passed in the
    command line and returns the scan result.
    """
    modules = {}
    for i in files:
        module = scan_file(i)
        modules[module['name']] = module
    return modules

def main():
    """Parses the command line arguments and execute the `scan_files'
    function in all arguments received.
    """
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('-o', '--output', dest='output',
                      action='store', default='/dev/stdout',
                      help='Output file name, defaults to /dev/stdout.')
    parser.add_option('-i', '--indent', dest='indent',
                      action='store', default='-1', type='int',
                      help='If is a non negative integer, defines the '
                      'pretty indentation of the json content generated')
    parser.add_option('-t', '--run-tests', dest='tests',
                      action='store_true', default=False,
                      help='Run doctests.')

    options, files = parser.parse_args()

    if options.tests:
        import doctest
        doctest.testmod()[0]
        exit()

    target = open(options.output, 'w')
    simplejson.dump(scan_files(files), target, indent=int(options.indent))
    return 0

if __name__ == '__main__':
    exit(main())

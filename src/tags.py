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

"""This module contains parsers of documentation tag values.
"""

__all__ = (
    'tag_name', 'tag_type', 'tag_param', 'tag_raise', 'tag_super',
    'tag_since', 'tag_see', 'tag_return',
)

def tag_name(value):
    """Parser for the @name tag.

    This is the simplest parser that we have. It just strips tralling
    whitespaces from the value and returns it.

    like this::

      >>> tag_name(' ta_iri')
      {'name': 'ta_iri'}

      >>> tag_name(' ta_log::info')
      {'name': 'info', 'class': 'ta_log'}
    """
    broken = value.strip().split('::')
    if len(broken) == 1:
        return {'name': broken[0]}
    else:
        return {'name': broken[1], 'class': broken[0]}

def tag_type(value):
    """Parser for the @type tag.

    This is the most complex parser of our current
    implementation. This function has to handle many different types
    of objects each one with a different syntax.

    The currently implemented types are the following::

      * class = "class"

      * enum = "enum"

      * delegate = "delegate"

      * constructor = "constructor"

      * destructor = "destructor"

      * getter = "getter"

      * setter = "setter"

      * method = "method"

    For `enum', `class' and `delegate' types this should be the
    behaviour::

      >>> tag_type('class')
      {'name': 'class'}

      >>> tag_type('enum')
      {'name': 'enum'}

      >>> tag_type('delegate')
      {'name': 'delegate'}

    For `constructor', `destructor' and `method' types, we have this
    one::

      >>> tag_type(' constructor')
      {'name': 'constructor'}

      >>> tag_type(' destructor')
      {'name': 'destructor'}

      >>> tag_type(' method')
      {'name': 'method'}

    For 'getter' and 'setter' we have::

      >>> tag_type(' getter')
      {'name': 'getter'}

      >>> tag_type(' setter')
      {'name': 'setter'}

    """
    return {'name': value.strip()}

def tag_param(value):
    """Parser for the @param tag.

    This parser finds the parameter name and its modifiers, like
    this::

      >>> from pprint import pprint
      >>> pprint(tag_param(' type (optional): Content mime type'))
      {'doc': 'Content mime type', 'modifiers': ['optional'], 'name': 'type'}

      >>> pprint(tag_param(' size (optional, len): Test param'))
      {'doc': 'Test param', 'modifiers': ['optional', 'len'], 'name': 'size'}
    """
    broken = value.split(':')

    # Looking for modifiers in the parameter definition. They are
    # declared between parenthesis and are separated by the ',' char.
    name = broken[0].strip()
    modifiers = []
    if '(' in name:
        name, params = name.split('(')
        modifiers_str = params.replace(')', '')
        modifiers = [x.strip() for x in modifiers_str.split(',')]

    # Looking for documentation
    doc = ''
    if len(broken) > 1:
        doc = broken[1].strip()

    # Building return dict
    return dict(name=name.strip(), modifiers=modifiers, doc=doc)

def tag_raise(value):
    """Parser for the @raises tag.

    This simple parser splits the value by the ',' char and returns a
    stripped list containing the splitted values. Like this:

     >>> tag_raise(' TA_ATOM_PARSING_ERROR')
     ['TA_ATOM_PARSING_ERROR']

     >>> tag_raise(' TA_ATOM_LOAD_ERROR, TA_ATOM_PARSING_ERROR')
     ['TA_ATOM_LOAD_ERROR', 'TA_ATOM_PARSING_ERROR']
    """
    return [x.strip() for x in value.split(',')]

def tag_super(value):
    """Parser for the @super tag.

    Like `tag_name' and other simple parsers, it just strips white
    spaces from the string.

      >> tag_super(' ta_iri')
      'ta_iri'
    """
    return value.strip()

def tag_since(value):
    """Parser for the @since tag.

    This tag marks in which version a symbol was added to the API and
    works like this::

      >>> tag_since(' 2.1.2')
      '2.1.2'
    """
    return value.strip()

def tag_see(value):
    """Parser for the @see tag.

    This tag can contain link references for other symbols in the
    library.

    You should use only known symbols in the library. External
    references should be added in the `description' field.

       >>> tag_see('ta_iri')
       ['ta_iri']

       >>> tag_see('ta_iri, ta_tag')
       ['ta_iri', 'ta_tag']
    """
    return [x.strip() for x in value.split(',')]

def tag_return(value):
    """Parser for the @return tag.

    Return tag is provided when an unreachable information should be
    provided. In common cases, the header code parser extract the
    return type of the method prototypes. But there are somethings
    that are hard (or impossible) to guess just looking in to the
    prototype.

    One use case for this tag is to inform the type of objects added
    in a list or in other kind of container. Like this::

      >>> tag_return(' ta_list (ta_atom_link)')
      {'containing': 'ta_atom_link', 'type': 'ta_list'}

    But other kind of information can be provided with @returns tag
    too, like in this example::

      >>> tag_return(' bool')
      {'type': 'bool'}
    """
    ret = {}
    stype = value.strip()
    if '(' in value:
        stype, containing_type = stype.split('(')
        containing_type = containing_type.replace(')', '').strip()
        ret['containing'] = containing_type
    stype = stype.strip()
    ret['type'] = stype
    return ret

if __name__ == '__main__':
    import doctest
    doctest.testmod()

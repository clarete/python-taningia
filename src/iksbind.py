#!/usr/bin/python
# -*- coding: utf-8; -*-
#
# Copyright (C) 2010  Lincoln de Sousa <lincoln@comum.org>
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

from pybindgen import FileCodeSink, Module, retval, param, cppclass
from pybindgen.module import SubModule
from pybindgen.typehandlers.base import ReturnValue, Parameter

IKSTYPE = [
    'IKS_NONE',
    'IKS_TAG',
    'IKS_ATTRIBUTE',
    'IKS_CDATA',
]

IKSUBTYPE = [
    'IKS_TYPE_NONE',
    'IKS_TYPE_ERROR',
    'IKS_TYPE_CHAT',
    'IKS_TYPE_GROUPCHAT',
    'IKS_TYPE_HEADLINE',
    'IKS_TYPE_GET',
    'IKS_TYPE_SET',
    'IKS_TYPE_RESULT',
    'IKS_TYPE_SUBSCRIBE',
    'IKS_TYPE_SUBSCRIBED',
    'IKS_TYPE_UNSUBSCRIBE',
    'IKS_TYPE_UNSUBSCRIBED',
    'IKS_TYPE_PROBE',
    'IKS_TYPE_AVAILABLE',
    'IKS_TYPE_UNAVAILABLE',
]

IKSHOWTYPE = [
    'IKS_SHOW_UNAVAILABLE',
    'IKS_SHOW_AVAILABLE',
    'IKS_SHOW_CHAT',
    'IKS_SHOW_AWAY',
    'IKS_SHOW_XA',
    'IKS_SHOW_DND',
]

IKS_STRING_METHOD = '''static PyObject *
_wrap_iks_string(PyIks *self, PyObject *args, PyObject *kwargs,
                 PyObject **return_exception)

{
    PyObject *py_retval;
    char *retval;
    const char *keywords[] = {NULL};
    
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "", (char **)keywords)) {
        PyObject *exc_type, *traceback;
        PyErr_Fetch(&exc_type, return_exception, &traceback);
        Py_XDECREF(exc_type);
        Py_XDECREF(traceback);
        return NULL;
    }
    retval = iks_string(NULL, self->obj);
    py_retval = Py_BuildValue((char *) "s", retval);
    return py_retval;
}
'''

def add_classes(mod):
    klass = mod.add_class(
        'iks',
        memory_policy=cppclass.FreeFunctionPolicy('(void *)'),
        custom_name='Iks')

    klass.add_function_as_constructor(
        'iks_new',
        retval('iks*', caller_owns_return=True),
        [param('const char*', 'name')],
        )

    klass.add_function_as_method(
        'iks_insert',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=False),
         param('const char*', 'name')],
        custom_name='insert',
        )

    klass.add_function_as_method(
        'iks_insert_attrib',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=True),
         param('const char*', 'name'),
         param('const char*', 'value')],
        custom_name='insert_attrib',
        )

    klass.add_function_as_method(
        'iks_name',
        retval('char*', caller_owns_return=False),
        [param('iks*', 'x', transfer_ownership=False)],
        custom_name='name',
        )

    klass.add_custom_method_wrapper(
        'string',
        '_wrap_iks_string',
        IKS_STRING_METHOD,
        )

    klass.add_function_as_method(
        'iks_child',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=False)],
        custom_name='child',
        )

    klass.add_function_as_method(
        'iks_next',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=False)],
        custom_name='next',
        )

    klass.add_function_as_method(
        'iks_next_tag',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=False)],
        custom_name='next_tag',
        )

    klass.add_function_as_method(
        'iks_prev',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=False)],
        custom_name='prev',
        )

    klass.add_function_as_method(
        'iks_prev_tag',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=False)],
        custom_name='prev_tag',
        )

    klass.add_function_as_method(
        'iks_find',
        retval('iks*', caller_owns_return=True),
        [param('iks*', 'x', transfer_ownership=False),
         param('const char*', 'name')],
        custom_name='find',
        )

    klass.add_function_as_method(
        'iks_find_attrib',
        retval('char*', caller_owns_return=False),
        [param('iks*', 'x', transfer_ownership=False),
         param('const char*', 'name')],
        custom_name='find_attrib',
        )

def add_functions(mod):
    mod.add_function('iks_make_session',
                     retval('iks*', caller_owns_return=True),
                     [], custom_name='make_session')

    mod.add_function('iks_make_pres',
                     retval('iks*', caller_owns_return=True),
                     [param('int', 'show'),
                      param('const char *', 'status')],
                     custom_name='make_pres')

def gen_mod(mod):
    submod = SubModule('iksemel', mod)
    submod.add_enum('ikstype', IKSTYPE)
    submod.add_enum('iksubtype', IKSUBTYPE)
    submod.add_enum('ikshowtype', IKSHOWTYPE)
    add_classes(submod)
    add_functions(submod)

def main():
    mainmod = Module('iksemel2')
    output = open('iksemel2module.c', 'w')
    mainmod.generate(FileCodeSink(output))
    output.close()

if __name__ == '__main__':
    main()

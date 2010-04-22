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

import sys
import os
import warnings
from scanner import scan_file, purge_lib_prefix, purge_type_sufix
from pybindgen import FileCodeSink, Module, retval, param, cppclass
from pybindgen.module import SubModule

def underscore_to_camel(name):
    nname = ''
    nsize = len(name)
    i = 0
    while i < nsize:
        if name[i] == '_':
            i += 1
            nname += name[i].upper()
        else:
            if i == 0:
                nname += name[i].upper()
            else:
                nname += name[i]
        i += 1
    return nname

def handle_params(method, parent):
    cparams = []
    for index, item in enumerate(method['params']):
        extra = {}

        # Handling ownership in parameters of known types
        if item['type'] in [('%s *' % x) for x in parent]:
            extra.update({'transfer_ownership': False})

        # Dealing with optional arguments
        if 'optional' in item.get('modifiers', ()):
            if '*' in item['type']:
                extra.update({'default_value': 'NULL'})
            elif item['type'] == 'int':
                extra.update({'default_value': '0'})

        cparams.append(param(item['type'], item['name'], **extra))
    return cparams

def load_module(module, parent):
    print "Processing module `%s'" % module['name']
    mod = SubModule(module['name'], parent)

    for enum in module['enums']:
        print " - enum `%s'" % enum['name']
        mod.add_enum(enum['name'], enum['entries'])

    for ctype in module['types']:
        ktype = module['types'][ctype]

        # Preparing the custom name of our class. All pedantic C
        # namespace and type conventions are being purged and
        # underscore style is replaced by camelcase style.
        custom_name = purge_lib_prefix(ktype['cname'])
        custom_name = purge_type_sufix(custom_name)
        custom_name = underscore_to_camel(custom_name)

        print " - class `%s'" % custom_name

        # Preparing vars to receive constructor, destructor and
        # other ordinary methods of our class.
        constructor = None
        destructor = None
        methods = []

        # `Almost' all of our library types has refcounted memory
        # policy, so the default is to do not have a destructor. We
        # use the generic one, ta_object_unref.
        destructor = None

        # Separating constructor, destructor and other ordinary
        # methods.
        for method in ktype['methods']:
            print "  * method `%s'" % method['name']['name']
            cname = '%(class)s_%(name)s' % method['name']
            method['cname'] = cname

            # C API specific stuff. We don't have to expose it.
            if method['type']['name'] == 'initializer':
                continue
            if method['type']['name'] == 'constructor':
                constructor = method
            elif method['type']['name'] == 'destructor':
                # Overrides default destructor
                destructor = cname
            else:
                if method['name']['name'] == 'set_handler':
                    continue
                methods.append(method)

        if destructor is not None:
            memory_policy = cppclass.FreeFunctionPolicy(destructor)
        else:
            memory_policy = cppclass.ReferenceCountingFunctionsPolicy(
                  incref_function='ta_object_ref',
                  decref_function='ta_object_unref',
                  )

        # Time to create our class!
        klass = mod.add_class(
            ktype['cname'],
            memory_policy=memory_policy,
            custom_name=custom_name)

        # And set its constructor.
        klass.add_function_as_constructor(
            constructor['cname'],
            retval(constructor['rtype']),
            handle_params(constructor, parent))

        # Adding other ordinary methods
        for i in methods:
            # Pretty function name. Nice to debug too.
            fname = i['name']['name']

            # Preparing some extra parameters to control the memory
            # management of the returned value of our method.
            extra_params = {}

            if i['rtype'] == 'char *':
                # I can do it here because all stuff that should not
                # be free is marked as `constant' in the library.
                extra_params.update({'caller_owns_return': True})
            elif i['rtype'] in [('%s *' % x) for x in parent]:
                # We really would implement reference counting in our
                # objects.
                extra_params.update({'reference_existing_object': True})

            try:
                klass.add_function_as_method(
                    i['cname'],
                    retval(i['rtype'], **extra_params),
                    handle_params(i, parent),
                    custom_name=fname)
            except:
                warnings.warn('Skipping method %s, something wrong happened' %
                              fname)
    return mod

def main():
    # Building main module
    mainmod = Module('taningia')
    mainmod.add_include('<taningia/taningia.h>')

    # Time to find submodules to add. Order is important here.
    base = os.path.expanduser("~/Work/taningia/include/taningia/")
    headers = ['error.h', 'log.h', 'iri.h', 'xmpp.h']
    for i in headers:
        module = scan_file(os.path.join(base, i))
        load_module(module, mainmod)

    # Writing down all processed stuff and we're done!
    output = open('taningiamodule.c', 'w')
    mainmod.generate(FileCodeSink(output))
    output.close()

if __name__ == '__main__':
    main()

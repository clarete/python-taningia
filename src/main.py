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

        # Separating constructor, destructor and other ordinary
        # methods.
        for method in ktype['methods']:
            print "  * method `%s'" % method['name']['name']
            cname = '%(class)s_%(name)s' % method['name']
            method['cname'] = cname

            if method['type']['name'] == 'constructor':
                constructor = method
            elif method['type']['name'] == 'destructor':
                destructor = cppclass.FreeFunctionPolicy(cname)
            else:
                if method['name']['name'] == 'set_handler':
                    continue
                methods.append(method)

        # Time to create our class!
        klass = mod.add_class(
            ktype['cname'],
            memory_policy=destructor,
            custom_name=custom_name)

        # And set its constructor.
        klass.add_function_as_constructor(
            constructor['cname'],
            retval(constructor['rtype']),
            [param(x['type'], x['name']) for x in constructor['params']])

        # Adding other ordinary methods
        for i in methods:
            params = []
            for index, item in enumerate(i['params']):
                if item['type'] == 'varargs':
                    # Do not handling this will not hurt anything, we
                    # have only string formatting being done with it.
                    continue
                if index != 0:
                    # Ordinary parameters
                    params.append(param(item['type'], item['name']))
                else:
                    # This is the first parameter of a method, the
                    # `self' one. Because of it we pass
                    # transfer_ownership set to False.
                    params.append(param(item['type'], item['name'],
                                        transfer_ownership=False))

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

            klass.add_function_as_method(
                i['cname'],
                retval(i['rtype'], **extra_params),
                params,
                custom_name=fname)
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

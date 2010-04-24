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
from pybindgen.typehandlers.base import ReturnValue, Parameter

DATE_CONVERTERS = '''
static time_t
convert_from_date (PyObject *val)
{
  time_t retval = 0;

  if (val == Py_None)
    retval = 0;
  else
    {
      struct tm mtm;
      mtm.tm_sec = PyDateTime_DATE_GET_SECOND (val);
      mtm.tm_min = PyDateTime_DATE_GET_MINUTE (val);
      mtm.tm_hour = PyDateTime_DATE_GET_HOUR (val);
      mtm.tm_mday = PyDateTime_GET_DAY (val);
      mtm.tm_mon = PyDateTime_GET_MONTH (val) - 1;    /* Month starts from 0 */
      mtm.tm_year = PyDateTime_GET_YEAR (val) - 1900; /* see `man mktime'    */
      mtm.tm_isdst = -1;
      mtm.tm_gmtoff = 1;
      if ((retval = mktime (&mtm)) == -1)
        {
          /* Invalid date, should be handled by the caller */
          retval = -1;
        }
    }
  return retval;
}

static PyObject *
convert_to_date (time_t val)
{
  if (val == 0)
    {
      Py_INCREF (Py_None);
      return Py_None;
    }
  else
    {
      struct tm *ctm = localtime (&val);
      PyObject *date = PyDateTime_FromDateAndTime (1900 + ctm->tm_year,
                                                   ctm->tm_mon + 1,
                                                   ctm->tm_mday,
                                                   ctm->tm_hour,
                                                   ctm->tm_min,
                                                   ctm->tm_sec,
                                                   0);
      Py_INCREF (date);
      return date;
    }
}
'''

class TimeTParameter(Parameter):

    DIRECTIONS = [Parameter.DIRECTION_IN]
    CTYPES = ['time_t']

    def convert_python_to_c(self, wrapper):
        pyobj = wrapper.declarations.declare_variable('PyObject*', 'pydtime');
        dobj = wrapper.declarations.declare_variable('time_t', 'dtime', '0');
        wrapper.before_call.write_code('dtime = convert_from_date (pydtime);')
        wrapper.parse_params.add_parameter('O', ['&'+pyobj], self.value)
        wrapper.call_params.append(dobj)

class TimeTReturnValue(ReturnValue):

    CTYPES = ['time_t']

    def get_c_error_return(self):
        return 'return NULL;'

    def convert_c_to_python(self, wrapper):
        name = wrapper.declarations.declare_variable('PyObject*', 'py_date')
        wrapper.after_call.write_code('py_date = convert_to_date (retval);')
        wrapper.build_params.add_parameter('O', ['py_date'], prepend=True)

class ListTReturnValue(ReturnValue):

    CTYPES = ['ta_list_t*']


    def __init__(self, ctype, is_const=False, contained_type=None):
        super(ListTReturnValue, self).__init__(ctype, is_const)
        self.contained_type = contained_type

    def get_c_error_return(self):
        return 'return NULL;'

    def convert_c_to_python(self, wrapper):
        template = '''py_list = PyList_New (0);
if (!py_list)
  return NULL;
for (tmp = retval; tmp; tmp = tmp->next) {
    %(pystruct)s *pyobj;
    pyobj = PyObject_New (%(pystruct)s, &%(pytypestruct)s);
    pyobj->obj = tmp->data;
    PyList_Append (py_list, (PyObject*) pyobj);
}
'''
        wrapper.declarations.declare_variable('PyObject*', 'py_list', 'NULL')
        wrapper.declarations.declare_variable('ta_list_t*', 'tmp', 'NULL')
        wrapper.after_call.write_code(template % {
                'pystruct':self.contained_type.pystruct,
                'pytypestruct': self.contained_type.pytypestruct})
        wrapper.build_params.add_parameter('O', ['py_list'], prepend=True)
        
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

        # Do not handling this will not hurt anything, we have only
        # string formatting being done with it.
        if item['type'] == 'varargs':
            continue

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

    for func in module['functions']:
        name = func['name']['name']
        custom_name = name.replace('ta_%s_' % mod.name, '')

        try:
            mod.add_function(name,
                             retval(func['rtype']),
                             handle_params(func, parent),
                             custom_name=custom_name)
        except Exception, e:
            warnings.warn('Skipping func %s, something wrong happened. %s' %
                          (name, str(e)))

    for ctype in module['types']:
        ktype = module['types'][ctype]

        # Preparing the custom name of our class. All pedantic C
        # namespace and type conventions are being purged and
        # underscore style is replaced by camelcase style.

        custom_name = ktype['cname'].replace(module['name'] + '_', '')
        custom_name = purge_lib_prefix(custom_name)
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
            elif i['rtype'] == 'ta_list_t *':
                containing = i['return']['containing']
                containing_type = mod.parent[containing+'_t']
                extra_params.update({'contained_type': containing_type})

            try:
                klass.add_function_as_method(
                    i['cname'],
                    retval(i['rtype'], **extra_params),
                    handle_params(i, parent),
                    custom_name=fname)
            except Exception, e:
                warnings.warn('Skipping method %s, something wrong happened. %s' %
                              (fname, str(e)))
    return mod

def main():
    # Building main module
    mainmod = Module('taningia')
    mainmod.add_include('<datetime.h>')
    mainmod.add_include('<taningia/taningia.h>')
    mainmod.after_forward_declarations.writeln(DATE_CONVERTERS)
    mainmod.before_init.write_code('PyEval_InitThreads ();')
    mainmod.before_init.write_code('PyDateTime_IMPORT;')

    # Time to find submodules to add. Order is important here.
    base = os.path.expanduser("~/Work/taningia/include/taningia/")
    headers = ['error.h', 'log.h', 'iri.h', 'xmpp.h', 'atom.h', 'pubsub.h']
    for i in headers:
        module = scan_file(os.path.join(base, i))
        load_module(module, mainmod)

    # Writing down all processed stuff and we're done!
    output = open('taningiamodule.c', 'w')
    mainmod.generate(FileCodeSink(output))
    output.close()

if __name__ == '__main__':
    main()

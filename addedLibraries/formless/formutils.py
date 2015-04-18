# Copyright (c) 2004 Divmod.
# See LICENSE for details.

from __future__ import generators

from zope.interface import implements

from twisted.python import components

from nevow import inevow
from nevow import tags

from formless import iformless


try:
    enumerate = enumerate
except:
    def enumerate(collection):
        i = 0
        it = iter(collection)
        while 1:
            yield (i, it.next())
            i += 1


class PrefixerDict(dict):
    def __init__(self, prefix, errors):
        if prefix is None: prefix = ''
        self.prefix = prefix
        self.errors = errors
        dict.__init__(self)

    def __setitem__(self, key, value):
        if key is None:
            key = ''
        if key == '':
            pfxkey = self.prefix
        else:
            pfxkey = '.'.join((self.prefix, key))
        self.errors[pfxkey] = value

    def __getitem__(self, key):
        if key == '':
            pfxkey = self.prefix
        else:
            pfxkey = '.'.join((self.prefix, key))
        return self.errors[pfxkey]

    def update(self, other):
        for key, value in other.items():
            self[key] = value


class FormDefaults(components.Adapter):
    def __init__(self):
        self.defaults = {}

    def setDefault(self, key, value, context=None):
        self.defaults[key] = value

    def getDefault(self, key, context=None):
        #print "getting default for key", key, self.defaults
        # 1) Check on the request
        current = self.defaults.get(key, None)
        if current is None:
            # 2) Check on the session
            if context is not None:
                sessionDefaults = context.locate(iformless.IFormDefaults)
                if sessionDefaults is not self:
                    current = sessionDefaults.getDefault(key)
                    if current is not None:
                        return current
                # 3) Ask the Binding instance for the default values
                try:
                    configurable = context.locate(iformless.IConfigurable)
                except KeyError:
                    return ''
                return configurable.getDefault(context.locate(inevow.IData))
        return current

    def getAllDefaults(self, key):
        return PrefixerDict(key, self.defaults)

    def clearAll(self):
        self.defaults = {}


class FormErrors(components.Adapter):
    """An object which keeps track of which forms have which errors
    """
    implements(iformless.IFormErrors)
    def __init__(self):
        self.errors = {}

    def setError(self, errorKey, error):
        self.errors[errorKey] = error

    def getError(self, errorKey):
        #print "get error", errorKey, self.__dict__
        return self.errors.get(errorKey)

    def getAllErrors(self, formName):
        return PrefixerDict(formName, self.errors)

    def updateErrors(self, formName, errors):
        PrefixerDict(formName, self.errors).update(errors)

    def clearErrors(self, formName):
        for key in self.errors.keys():
            if key.startswith(formName):
                del self.errors[key]

    def clearAll(self):
        self.errors = {}

def calculatePostURL(context, data):
    postLocation = inevow.ICurrentSegments(context)[-1]
    if postLocation == '':
        postLocation = '.'
    try:
        configurableKey = context.locate(iformless.IConfigurableKey)
    except KeyError:
        #print "IConfigurableKey was not remembered when calculating full binding name for %s in node %s" % (configurable, context.key)
        configurableKey = ''
    bindingName = context.key
    return "%s/freeform_post!%s!%s" % (postLocation, configurableKey, bindingName)


def keyToXMLID(key):
    """Convert a key into an XML-styleinevow.ID """
    if not key:
        #print 'keyToXMLID: no key, but why?'
        return '***Error: Unset***'
    return '-'.join(key.split('.'))


def getError(context):
    errors = context.locate(iformless.IFormErrors)
    err = errors.getError(context.key)
    if err is not None:
        return err
    return tags.comment["\nNo error for error key: %s\n" % context.key]

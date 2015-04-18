##############################################################################
#
# Copyright (c) 2009 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Fixer for class interface declarations to class decorators

$Id$
"""

# Local imports
from lib2to3.fixer_base import BaseFix
from lib2to3.patcomp import PatternCompiler
from lib2to3.fixer_util import syms, Name
from lib2to3.fixer_util import Node, Leaf

class Function2DecoratorBase(BaseFix):

    IMPORT_PATTERN = """
    import_from< 'from' dotted_name< 'zope' '.' 'interface' > 'import' import_as_names< any* (name='%(function_name)s') any* > >
    |
    import_from< 'from' dotted_name< 'zope' '.' 'interface' > 'import' name='%(function_name)s' any* >
    |
    import_from< 'from' dotted_name< 'zope' > 'import' name='interface' any* >
    |
    import_from< 'from' dotted_name< 'zope' '.' 'interface' > 'import' import_as_name< name='%(function_name)s' 'as' rename=(any) any*> >
    |
    import_from< 'from' dotted_name< 'zope' > 'import' import_as_name< name='interface' 'as' rename=(any) any*> >
    |
    import_from< 'from' 'zope' 'import' import_as_name< 'interface' 'as' interface_rename=(any) > >
    """
    
    CLASS_PATTERN = """
    decorated< decorator <any* > classdef< 'class' any* ':' suite< any* simple_stmt< power< statement=(%(match)s) trailer < '(' interface=any ')' > any* > any* > any* > > >
    |
    classdef< 'class' any* ':' suite< any* simple_stmt< power< statement=(%(match)s) trailer < '(' interface=any ')' > any* > any* > any* > >
    """

    FUNCTION_PATTERN = """
    simple_stmt< power< old_statement=(%s) trailer < '(' any* ')' > > any* >
    """
    
    def should_skip(self, node):
        module = str(node)
        return not ('zope' in module and 'interface' in module)

    def compile_pattern(self):
        # Compile the import pattern.
        self.named_import_pattern = PatternCompiler().compile_pattern(
            self.IMPORT_PATTERN % {'function_name': self.FUNCTION_NAME})
        
    def start_tree(self, tree, filename):
        # Compile the basic class/function matches. This is done per tree,
        # as further matches (based on what imports there are) also are done
        # per tree.
        self.class_patterns = []
        self.function_patterns = []
        self.fixups = []

        self._add_pattern("'%s'" % self.FUNCTION_NAME)
        self._add_pattern("'interface' trailer< '.' '%s' >" % self.FUNCTION_NAME)
        self._add_pattern("'zope' trailer< '.' 'interface' > trailer< '.' '%s' >" % self.FUNCTION_NAME)
    
    def _add_pattern(self, match):
            self.class_patterns.append(PatternCompiler().compile_pattern(
                self.CLASS_PATTERN % {'match': match}))
            self.function_patterns.append(PatternCompiler().compile_pattern(
                self.FUNCTION_PATTERN % match))
        
    def match(self, node):
        # Matches up the imports
        results = {"node": node}
        if self.named_import_pattern.match(node, results):
            return results

        # Now match classes on all import variants found:
        for pattern in self.class_patterns:
            if pattern.match(node, results):
                return results
                
    def transform(self, node, results):
        if 'name' in results:
            # This matched an import statement. Fix that up:
            name = results["name"]
            name.replace(Name(self.DECORATOR_NAME, prefix=name.prefix))
        if 'rename' in results:
            # The import statement use import as
            self._add_pattern("'%s'" % results['rename'].value)
        if 'interface_rename' in results:
            self._add_pattern("'%s' trailer< '.' '%s' > " % (
                results['interface_rename'].value, self.FUNCTION_NAME))
        if 'statement' in results:
            # This matched a class that has an <FUNCTION_NAME>(IFoo) statement.
            # We must convert that statement to a class decorator
            # and put it before the class definition.
            
            statement = results['statement']
            if not isinstance(statement, list):
                statement = [statement]
            # Make a copy for insertion before the class:
            statement = [x.clone() for x in statement]
            # Get rid of leading whitespace:
            statement[0].prefix = ''
            # Rename function to decorator:
            if statement[-1].children:
                func = statement[-1].children[-1]
            else:
                func = statement[-1]
            if func.value == self.FUNCTION_NAME:
                func.value = self.DECORATOR_NAME
            
            interface = results['interface']
            if not isinstance(interface, list):
                interface = [interface]
            interface = [x.clone() for x in interface]

            # Create the decorator:
            decorator = Node(syms.decorator, [Leaf(50, '@'),] + statement +
                             [Leaf(7, '(')] + interface + [Leaf(8, ')')])
                
            # Take the current class constructor prefix, and stick it into
            # the decorator, to set the decorators indentation.
            nodeprefix = node.prefix
            decorator.prefix = nodeprefix
            # Preserve only the indent:
            if '\n' in nodeprefix:
                nodeprefix = nodeprefix[nodeprefix.rfind('\n')+1:]
            
            # Then find the last line of the previous node and use that as
            # indentation, and add that to the class constructors prefix.
                
            previous = node.prev_sibling
            if previous is None:
                prefix = ''
            else:
                prefix = str(previous)
            if '\n' in prefix:
                prefix = prefix[prefix.rfind('\n')+1:]
            prefix = prefix + nodeprefix
                
            if not prefix or prefix[0] != '\n':
                prefix = '\n' + prefix
            node.prefix = prefix
            new_node = Node(syms.decorated, [decorator, node.clone()])
            # Look for the actual function calls in the new node and remove it.
            for node in new_node.post_order():
                for pattern in self.function_patterns:
                    if pattern.match(node, results):
                        parent = node.parent
                        previous = node.prev_sibling
                        # Remove the node
                        node.remove()
                        if not str(parent).strip():
                            # This is an empty class. Stick in a pass
                            if (len(parent.children) < 3 or 
                                ' ' in parent.children[2].value):
                                # This class had no body whitespace.
                                parent.insert_child(2, Leaf(0, '    pass'))
                            else:
                                # This class had body whitespace already.
                                parent.insert_child(2, Leaf(0, 'pass'))
                            parent.insert_child(3, Leaf(0, '\n'))
                        elif (prefix and isinstance(previous, Leaf) and
                            '\n' not in previous.value and
                            previous.value.strip() == ''):
                            # This is just whitespace, remove it:
                            previous.remove()

            return new_node
                    

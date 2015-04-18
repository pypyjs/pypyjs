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
"""Fixer for implements(IX) -> @implementer(IX).

$Id$
"""

from .base import Function2DecoratorBase

class FixClassProvides(Function2DecoratorBase):
    FUNCTION_NAME = 'classProvides'
    DECORATOR_NAME = 'provider'

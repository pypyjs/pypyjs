# Just use ElementTree.

from xml.etree import ElementTree

globals().update(ElementTree.__dict__)
del __all__

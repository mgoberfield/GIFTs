try:
    import gzip
except ValueError:
    pass

import os
import sys
import time
import uuid
import xml.etree.ElementTree as ET


class XMLError(SyntaxError):
    pass


class Bulletin(object):
    """Convenient wrapper around Python's <list> container class for processing <MeteorologicalBulletin>"""

    def __init__(self):

        self._children = []
        if sys.version_info[0] == 3:
            self.encoding = 'unicode'
        else:
            self.encoding = 'UTF-8'

    def __len__(self):

        return len(self._children)

    def __getitem__(self, pos):

        return self._children[pos]

    def __str__(self):
        """Print out the bulletin in prettified XML"""
        #
        # Create the bulletin
        self._export()
        #
        # Pad it with spaces and newlines
        self._addwhitespace()
        xmlstring = ET.tostring(self.bulletin, encoding=self.encoding, method='xml')
        self.bulletin = None
        return xmlstring.replace(' />', '/>')

    def _addwhitespace(self):
        tab = "  "

        def indent(elem, level=0):
            i = "\n" + level * tab
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + tab
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for elem in elem:
                    indent(elem, level + 1)
                    if not elem.tail or not elem.tail.strip():
                        elem.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i

        indent(self.bulletin)

    def __add__(self, other):
        """Combining bulletins"""
        #
        # Check to make sure they are of same product type -- very simple: doesn't take into account
        # namespace complexity.
        #
        try:
            if self._kind != other._kind:
                raise XMLError("All meteorologicalInformation children in the bulletins must be of the same kind.")

        except AttributeError:
            try:
                self._kind
            except AttributeError:
                try:
                    self._kind = other._kind
                except AttributeError:
                    raise XMLError("Attempted to combine empty bulletins")

        newBulletin = Bulletin()
        newBulletin._children.extend(self._children)
        newBulletin._children.extend(other._children)

        return newBulletin

    def _export(self):
        """Construct a <MeteorologicalBulletin> ElementTree"""

        if len(self) == 0:
            raise XMLError("At least one meteorologicalInformation child must be present in a bulletin.")

        try:
            self._bulletinID
        except AttributeError:
            raise XMLError("bulletinIdentifier needs to be set")

        self.bulletin = ET.Element('MeteorologicalBulletin')
        self.bulletin.set('xmlns', 'http://def.wmo.int/collect/2014')
        self.bulletin.set('xmlns:gml', 'http://www.opengis.net/gml/3.2')
        self.bulletin.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        self.bulletin.set('xsi:schemaLocation',
                          'http://def.wmo.int/collect/2014 http://schemas.wmo.int/collect/1.2/collect.xsd')
        self.bulletin.set('gml:id', 'uuid.%s' % uuid.uuid4())

        for child in self._children:
            metInfo = ET.SubElement(self.bulletin, 'meteorologicalInformation')
            metInfo.append(child)

        bulletinId = ET.SubElement(self.bulletin, 'bulletinIdentifier')
        bulletinId.text = self._bulletinID

    def what_kind(self):
        """Returns what type or 'kind' of <meteorologicalInformation> children are kept in this bulletin"""
        try:
            return self._kind
        except AttributeError:
            return None

    def append(self, document):
        """Append a ElementTree child to the list"""
        try:
            if document.tag == self._kind:
                self._children.append(document)
                try:
                    if self.bulletin is not None:
                        self.bulletin = None

                except AttributeError:
                    pass
            else:
                raise XMLError("All meteorologicalInformation children in a bulletin must be of the same kind.")

        except AttributeError:
            self._kind = document.tag
            self._children.append(document)

    def pop(self, pos=0):
        """Remove a child from the list"""
        return self._children.pop(pos)

    def set_bulletinIdentifier(self, **kwargs):

        keys = ['A_', 'tt', 'aaii', 'cccc', 'yygg', 'bbb', '_C_', 'cccc', time.strftime('_%Y%m%d%H%M%S.'), 'xml']
        self._bulletinID = ''.join([kwargs.get(key, key) for key in keys])

    def get_bulletinIdentifier(self):

        return self._bulletinID

    def export(self):
        """Construct and return a <MeteorologicalBulletin> ElementTree"""

        self._export()
        return self.bulletin

    def _write(self, obj):

        result = ET.tostring(self.bulletin, encoding=self.encoding, method='xml')

        if self._canBeCompressed:
            obj(result.encode('utf-8'))
        else:
            obj(result)

    def write(self, obj=None):
        """ElementTree to a file or stream.

        obj - if none provided, XML is written to current working directory, or
              write() method, or
              file object, or
              character string as directory, or
              character string as a filename.

        File extension indicated on <bulletinIdentifer> element's value determines
        whether compression is done. (Only gzip is permitted at this time)"""

        if self._bulletinID[-2:] == 'gz':
            if 'gzip' in globals().keys():
                self._canBeCompressed = True
            else:
                raise SystemError('No capability to compress files using gzip()')
        else:
            self._canBeCompressed = False
        #
        # Generate the bulletin for export to file or stream
        self._export()
        #
        # If the object name is 'write'; Assume it's configured properly for writing
        try:
            if obj.__name__ == 'write':
                return self._write(obj)
        except AttributeError:
            pass

        if type(obj) == str or obj is None:

            if obj is None:
                obj = self._bulletinID
            elif os.path.isdir(obj):
                obj = os.path.join(obj, self._bulletinID)
            else:
                if os.path.basename(obj) != self._bulletinID:
                    raise XMLError('Internal ID and external file names do not agree.')

            if self._canBeCompressed:
                _fh = gzip.open(obj, 'wb')
            else:
                _fh = open(obj, 'w')

            self._write(_fh.write)
            _fh.close()

        else:
            if os.path.basename(obj.name) != self._bulletinID:
                raise XMLError('Internal and external file names do not agree.')

            self._write(obj.write)

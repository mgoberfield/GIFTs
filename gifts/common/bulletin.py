try:
    import gzip
except ValueError:
    pass

import datetime
import os
import re
import sys
import uuid
import xml.etree.ElementTree as ET


class XMLError(SyntaxError):
    pass


class Bulletin(object):
    """Convenient wrapper around Python's <list> container class for processing <MeteorologicalBulletin>"""

    def __init__(self):

        self._children = []
        self.xmlFileNamePartA = re.compile(r'A_L[A-Z]{3}\d\d[A-Z]{4}\d{6}([ACR]{2}[A-Z])?_C_[A-Z]{4}')

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
        if sys.version_info[0] == 3:
            xmlstring = ET.tostring(self.bulletin, encoding='unicode', method='xml')
        else:
            xmlstring = ET.tostring(self.bulletin, encoding='UTF-8', method='xml')

        self.bulletin = None
        return xmlstring

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

    def _export(self, compress=False):
        """Construct a <MeteorologicalBulletin> ElementTree"""

        if len(self) == 0:
            raise XMLError("At least one meteorologicalInformation child must be present in a bulletin.")

        try:
            if self.xmlFileNamePartA.match(self._bulletinId) is None:
                raise XMLError('bulletinIdentifier does not conform to WMO. 386')

        except AttributeError:
            raise XMLError("bulletinIdentifier needs to be set")

        self.bulletin = ET.Element('MeteorologicalBulletin')
        self.bulletin.set('xmlns', 'http://def.wmo.int/collect/2014')
        self.bulletin.set('xmlns:gml', 'http://www.opengis.net/gml/3.2')
        self.bulletin.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        self.bulletin.set('xsi:schemaLocation',
                          'http://def.wmo.int/collect/2014 https://schemas.wmo.int/collect/1.2/collect.xsd')
        self.bulletin.set('gml:id', 'uuid.%s' % uuid.uuid4())

        for child in self._children:
            metInfo = ET.SubElement(self.bulletin, 'meteorologicalInformation')
            metInfo.append(child)

        fn = '{}_{}.xml'.format(self._bulletinId, datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'))
        if compress:
            fn = '{}.gz'.format(fn)

        bulletinId = ET.SubElement(self.bulletin, 'bulletinIdentifier')
        bulletinId.text = self._internalBulletinId = fn

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

        keys = ['A_', 'tt', 'aaii', 'cccc', 'yygg', 'bbb', '_C_', 'cccc']
        self._bulletinId = ''.join([kwargs.get(key, key) for key in keys])
        self._wmoAHL = '{}{} {} {} {}'.format(kwargs['tt'], kwargs['aaii'], kwargs['cccc'], kwargs['yygg'],
                                              kwargs['bbb']).rstrip()

    def export(self):
        """Construct and return a <MeteorologicalBulletin> ElementTree"""

        self._export()
        return self.bulletin

    def _write(self, obj, header, compress):

        tree = ET.ElementTree(element=self.bulletin)
        if header:
            ahl_line = '{}\n'.format(self._wmoAHL)
            obj.write(ahl_line.encode('UTF-8'))
        try:
            tree.write(obj, encoding='UTF-8', xml_declaration=True, method='xml', short_empty_elements=True)
        except TypeError:
            tree.write(obj, encoding='UTF-8', xml_declaration=True, method='xml')

    def _iswriteable(self, obj):
        try:
            return obj.writable() and obj.mode == 'wb'
        except AttributeError:
            try:
                return isinstance(obj, file) and obj.mode == 'wb'
            except NameError:
                return False

    def write(self, obj=None, header=False, compress=False):
        """Writes ElementTree to a file or stream.

        obj - if none provided, XML is written to current working directory, or
              character string as directory, or
              os.PathLike object such as a file object in 'wb' mode

        header - boolean as to whether the WMO AHL line should be included as first line in file. If true,
                 the file is no longer valid XML.

        If applicable, returns fullpath to the XML bulletin"""

        canBeCompressed = False
        if compress:
            if 'gzip' in globals().keys():
                canBeCompressed = True
            else:
                raise SystemError('No capability to compress files using gzip()')
        #
        # Do not include WMO AHL line in compressed files
        if canBeCompressed:
            header = False
        #
        # Generate the Meteorological Bulletin for writing
        try:
            self._internalBulletinId
        except AttributeError:
            self._export(canBeCompressed)
        #
        # If the object name is writable and mode is correct
        if self._iswriteable(obj):
            self._write(obj, header, canBeCompressed)
            return None
        #
        # Write to current directory if None, or to the directory path provided.
        if obj is None or (isinstance(obj, str) and os.path.isdir(obj)):
            if obj is None:
                obj = os.getcwd()

            if header:
                fullpath = os.path.join(obj, self._internalBulletinId.replace('xml', 'txt'))
            else:
                fullpath = os.path.join(obj, self._internalBulletinId)
            #
            # Write it out.
            if canBeCompressed:
                _fh = gzip.open(fullpath, 'wb')
            else:
                _fh = open(fullpath, 'wb')

            self._write(_fh, header, canBeCompressed)
            _fh.close()

            return fullpath

        else:
            raise IOError('First argument is an unsupported type: %s' % (str(type(obj))))

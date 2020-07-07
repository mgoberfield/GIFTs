import logging

from . import bulletin
from . import xmlConfig as des


class Encoder(object):

    def __init__(self):
        """Superclass for invoking MDL decoders and encoders for a code form."""

        self.geoLocationsDB = None
        self._Logger = logging.getLogger(__name__)

    def encode(self, text, receiptTime=None, **attrs):
        """Parses text to extract the WMO AHL line and one or more TAC forms.

           text = character string containing entire TAC message (required)
           receiptTime = date/time stamp the TAC message was received (optional, see xmlConfig.py)

           returns Bulletin object."""
        #
        collection = bulletin.Bulletin()
        #
        # Get the WMO AHL line and the TAC form(s)
        try:
            AHL = self.re_AHL.search(text)
            attrs.update(AHL.groupdict(''))
            attrs['tt'] = self.T1T2
            collection.set_bulletinIdentifier(**attrs)

            translatedBulletinID = AHL.group(0).replace(' ', '')

            for tac in self.re_TAC.findall(text):

                decodedTAC = self.decoder(tac)
                if decodedTAC['bbb'] == '':
                    decodedTAC['bbb'] = attrs['bbb']

                if des.TRANSLATOR:
                    decodedTAC['translatedBulletinID'] = translatedBulletinID
                    if receiptTime is not None:
                        decodedTAC['translatedBulletinReceptionTime'] = receiptTime
                    else:
                        decodedTAC['translatedBulletinReceptionTime'] = decodedTAC['translationTime']

                elif 'err_msg' in decodedTAC:
                    if self.T1T2 == 'L' or self.T1T2 == 'LT':
                        try:
                            self._Logger.warning('Will not create IWXXM document for %s' % decodedTAC['ident']['str'])
                        except KeyError:
                            self._Logger.warning('Bad observation, could not determine ICAO ID: %s' % tac)
                    else:
                        self._Logger.warning('Will not create IWXXM advisory because of a decoding error.')

                    continue

                if self.geoLocationsDB is not None:

                    try:
                        metaData = self.geoLocationsDB.get(decodedTAC['ident']['str'], '|||0.0 0.0 0')
                    except KeyError:
                        self._Logger.warning('Bad observation, could not determine icaoID: %s' % tac)
                        continue

                    fullname, iataID, alternateID, position = metaData.split('|')

                    if len(fullname) > 0:
                        decodedTAC['ident']['name'] = fullname
                    if len(alternateID) > 0:
                        decodedTAC['ident']['alternate'] = alternateID
                    if len(iataID) > 0:
                        decodedTAC['ident']['iataID'] = iataID

                    decodedTAC['ident']['position'] = position
                    if position == '0.0 0.0 0':
                        self._Logger.warning('"%s" not found in geoLocationsDB. Location missing.' %
                                             decodedTAC['ident']['str'])
                try:
                    collection.append(self.encoder(decodedTAC, tac))
                except SyntaxError as msg:
                    self._Logger.warning(msg)

        except AttributeError:
            pass

        return collection

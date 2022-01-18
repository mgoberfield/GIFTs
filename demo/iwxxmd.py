#!/bin/env python
#
# Description: Daemon that monitors a directory for TAC messages to be re-issued as an XML bulletin
#              consisting of IWXXM documents.
#
import logging
import logging.config
import os
import pickle
import signal
import sys
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import gifts


class Daemon(object):

    def daemonize(self):
        """Create a daemon using UNIX double fork mechanism."""

        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                raise SystemExit(0)

        except OSError as err:
            raise SystemExit(f'os.fork() call #1 failed: {str(err)}\n')

        # decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            # exit from second parent
            pid = os.fork()
            if pid > 0:
                raise SystemExit(0)

        except OSError as err:
            raise SystemExit(f'os.fork() call #2 failed: {str(err)}\n')

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def start(self):
        """Detach from terminal and then invoke the run() method"""

        self.daemonize()
        self.run()


class DOWFileHandler(logging.FileHandler):
    """Create and rotate log files based on the day-of-the-week"""

    def __init__(self, directory=None, basename=None):

        self.basename = os.path.join(directory, basename)
        self.__checkFileTime()
        super(DOWFileHandler, self).__init__(self.baseFilename, mode='a', delay=True)

    def __checkFileTime(self):

        self.baseFilename = '%s_%s' % (self.basename, time.strftime('%a'))
        try:
            if time.time() - os.path.getmtime(self.baseFilename) > 86400:  # more than 1 day
                os.unlink(self.baseFilename)
        except OSError:
            pass

    def doRollover(self):

        self.stream.write('Switching to new log file.\n')
        self.stream.close()
        self.__checkFileTime()
        self.stream = open(self.baseFilename, 'a')
        self.stream.write(time.strftime('Log rollover at %Y-%m-%d %H:%M:%S\n'))

    def emit(self, record):
        #
        # If the day of the week has changed since last emit...
        if time.strftime('%a') != self.baseFilename[-3:]:
            self.doRollover()

        logging.FileHandler.emit(self, record)


class Dispatcher(FileSystemEventHandler):
    """Create and write out the IWXXM documents based on the TAC form of the product"""

    def __init__(self, encoder, delete_flag, header, outputDirectory):

        super(Dispatcher, self).__init__()

        self.logger = logging.getLogger(__name__)

        self.encoder = encoder
        self.delete_flag = delete_flag
        self.header = header
        self.outputDirectory = outputDirectory
        self.bulletin = gifts.bulletin.Bulletin()

        if self.header:
            self.ext = 'txt'
        else:
            self.ext = 'xml'

    def on_modified(self, event):
        """If a new file saved in monitored directory, read it."""

        if not event.is_directory:
            try:
                #
                # Read the file contents
                fh = open(event.src_path, 'r')
                tac = fh.read()
                fh.close()
                self.logger.debug(f'Read the file: {event.src_path}')

            except IOError:
                self.logger.error(f'Unable to read the file: {event.src_path}')
                tac = ''
            #
            # Delete the file if requested
            if self.delete_flag:
                try:
                    os.unlink(event.src_path)
                    self.logger.debug(f'Deleted the file: {event.src_path}')

                except IOError:
                    self.logger.error(f'Unable to delete the file: {event.src_path}')
            #
            # Create the IWXXM form
            try:
                bulletin = self.encoder.encode(tac)
                iwxxm_msg_cnt = len(bulletin)
                if iwxxm_msg_cnt:
                    self.logger.debug(f'{iwxxm_msg_cnt} IWXXM products generated from {event.src_path} contents')
                    bulletin.write(self.outputDirectory, header=self.header)

                del bulletin

            except Exception:
                self.logger.exception('Unable to convert TAC to XML. Reason:\n')


class Monitor(Daemon):
    """Set up a watchdog for monitoring a file system directory"""

    def __init__(self, encoder, delete_flag, header, inputDirectory, outputDirectory):

        super(Monitor, self).__init__()

        self.logger = logging.getLogger(__name__)
        #
        # Check to make sure the monitor can read these directories and modify their contents
        if not os.path.exists(inputDirectory) or not os.path.isdir(inputDirectory) or \
           not os.access(inputDirectory, (os.R_OK | os.W_OK | os.X_OK)):
            raise SystemExit(f'{inputDirectory} does not exist or unable to modify its contents')

        if not os.path.exists(outputDirectory) or not os.path.isdir(outputDirectory) or \
           not os.access(outputDirectory, (os.W_OK | os.X_OK)):
            raise SystemExit(f'{outputDirectory} does not exist or unable to write to it')
        #
        # Set up the dispatcher to generate and write the IWXXM product
        self.dispatcher = Dispatcher(encoder, delete_flag, header, outputDirectory)
        #
        # Start the observer with the the directory to watch and what to do when
        # there's activity in the directory
        self.observer = Observer()
        self.observer.schedule(self.dispatcher, inputDirectory, False)
        self.inputDirectory = inputDirectory
        #
        # Clean up when termination signal is received
        signal.signal(signal.SIGTERM, self.shutdown)

    def run(self):

        self.logger.info(f'Begin monitoring {self.inputDirectory}. . .')
        self.observer.start()
        t = 0

        while True:
            time.sleep(0.1)
            t += 1
            if t >= 36000:
                self.logger.info('Aliveness check . . .')
                t = 0

    def shutdown(self, signum, frame):

        self.logger.info(f'Shutdown in progress. Monitoring {self.inputDirectory} will be stopped')
        self.observer.stop()
        self.observer.join()
        self.logger.info('Shutdown complete.')

        raise SystemExit(0)


if __name__ == '__main__':

    import configparser as cp

    try:
        settings = cp.ConfigParser()
        if len(settings.read(sys.argv[1])) == 0:
            SystemExit('Unrecognized format in configuration file')

    except IndexError:
        raise SystemExit('Error: configuration file is needed as first argument')

    except FileNotFoundError:
        raise SystemExit(f'File not found: {sys.argv[1]}')

    except cp.ParsingError as err:
        raise SystemExit(f'Error parsing {sys.argv[1]}: {str(err)}')
    #
    # Select the requested TAC-to-XML encoder
    product = settings.get('internals', 'product')
    try:
        classPtr = {'metar': gifts.METAR.Encoder,
                    'taf': gifts.TAF.Encoder,
                    'tca': gifts.TCA.Encoder,
                    'vaa': gifts.VAA.Encoder,
                    'swa': gifts.SWA.Encoder}.get(product)

    except KeyError:
        raise SystemExit(f'{product} is not one of: metar, taf, tca, vaa, swa')
    #
    # For METAR/SPECI and TAF products, read in the external database. This code assumes
    # pickled dictionary here; change it if different.
    if product in ['metar', 'taf']:
        try:
            database = settings.get('internals', 'geo_locations_file')
            with open(database, 'rb') as fh:
                WMO_ID_mappings = pickle.load(fh)

        except Exception as err:
            raise SystemExit(str(err))
    #
    # Create the TAC-to-XML encoding service
    if product in ['metar', 'taf']:
        encoder = classPtr(WMO_ID_mappings)
    else:
        encoder = classPtr()
    #
    # Configure logging
    logfileDirectory = settings.get('directories', 'logs')
    #
    # Check the directory for use
    if not os.path.exists(logfileDirectory) or not os.path.isdir(logfileDirectory) or \
       not os.access(logfileDirectory, (os.W_OK | os.X_OK)):
        raise SystemExit(f'{logfileDirectory} does not exist or unable to write to it')

    logger = {
        'version': 1,
        'disable_existing_loggers': False,

        'formatters': {
            'default': {
                'class': 'logging.Formatter',
                'format': '%(asctime)s %(levelname)-5s %(process)5d %(module)s: %(message)s'
            },
        },

        'handlers': {
            'file': {
                'level': 'INFO',
                'formatter': 'default',
                '()': 'iwxxmd.DOWFileHandler',
                'directory': f'{logfileDirectory}',
                'basename': f'{product}_iwxxmd'
            },
        },
        'loggers': {
            'gifts': {
                'propogate': True,
                'handlers': ['file'],
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['file']
        }
    }
    logging.config.dictConfig(logger)
    #
    # Initialize the watchdog
    try:
        delete_flag = settings.get('internals', 'delete_after_read') == 'true'
        header = settings.get('internals', 'wmo_ahl_line') == 'true'

        watchdog = Monitor(encoder, delete_flag, header, settings.get('directories', 'input'),
                           settings.get('directories', 'output'))

    except Exception as err:
        raise SystemExit(str(err))
    #
    # Start monitoring the directory in the background
    watchdog.start()

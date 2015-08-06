__author__ = 'micucci'
# Copyright 2015 Midokura SARL
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from Exceptions import *
from common.FileLocation import *
from common.CLI import LinuxCLI
import logging
import logging.handlers
import datetime
import os
import glob

class LogManager(object):

    def __init__(self, root_dir='.'):
        self.loggers = {}
        """ :type: dict [str, Logger]"""
        self.default_log_level = logging.WARNING
        """ :type: int"""
        self.formats = {}
        """ :type: dict [str, logging.Formatter]"""
        self.root_dir = root_dir
        """ :type: str"""
        self.open_log_files = {}
        """ :type: dict [FileLocation, list[(logging.Logger, logging.Handler)]]"""
        self.external_log_files = set()
        """ :type: set [FileLocation]"""

        # Set up a default, standard format
        self.add_format('standard',
                        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        if not LinuxCLI().exists(self.root_dir):
            LinuxCLI(priv=False).mkdir(self.root_dir)

    def set_default_log_level(self, level):
        """
        Set default log level all loggers will use unless otherwise specified
        :param level: int Log level as defined by Python's logging module
        :return:
        """
        self.default_log_level = level

    def get_format(self, format):
        """
        Return a stored format
        :param format: str Name of format to return
        :return: logging.Formatter
        """
        if format not in self.formats:
            raise ObjectNotFoundException('Log format not defined: ' + format)
        return self.formats[format]

    def add_format(self, format_name, format_obj):
        """
        Add a format to the stored formats
        :param format_name: str Name to use for format (must be unique)
        :param format_obj: logging.Formatter Formatter object from Python's logging module
        :return:
        """
        if format_name in self.formats:
            raise ObjectAlreadyAddedException('Log format already defined: ' + format_name)
        self.formats[format_name] = format_obj

    def get_logger(self, name='root'):
        """
        Returns a Python logging.Logger that was created with the given name
        :param name: str Name of the logger to retrieve
        :return: logging.Logger
        """
        if name not in self.loggers:
            raise ObjectNotFoundException('No logger found: ' + name)
        return self.loggers[name]

    def _log_check_and_create(self, name, level, handler_obj, format_name):
        """
        Internal function to create and set up logger
        :param name: str Name of logger to create
        :param level: int Log level to set for log and handler
        :param handler_obj: logging.Handler Handler object to use for this logger
        :param format_name: Name of the stored format to use for this logger
        :return: logging.Logger The created logger object
        """

        if name is None:
            name = 'root' + str(len(self.loggers))

        if name in self.loggers:
            new_log = self.get_logger(name)
        else:
            new_log = logging.getLogger(name)

        handler_obj.setLevel(level if level is not None else self.default_log_level)
        handler_obj.setFormatter(self.get_format(format_name))

        new_log.setLevel(level if level is not None else self.default_log_level)
        new_log.addHandler(handler_obj)

        self.loggers[name] = new_log

        return new_log

    def add_stdout_logger(self, name=None, log_level=None, format_name='standard'):
        """
        Add a Python logger which uses a StreamHandler sending logs to stdout then stores and returns it
        :param name: str Identifier for this logger, None to autogenerate
        :param log_level: int Logging level (use LogManager default if None) for the log output
        :param format_name: str Preset format name to use (add via "add_format" function)
        :return: logging.Logger Created logger
        """
        new_log = self._log_check_and_create(name, log_level, logging.StreamHandler(), format_name)
        return new_log

    def add_file_logger(self, file_name, name=None, file_overwrite=False,
                        log_level=None, format_name='standard'):
        """
        Add a Python logger which uses a FileHandler to log to a file then stores and returns it
        :param file_name: str Name of the file to log to
        :param name: str Identifier for this logger, None to autogenerate
        :param file_overwrite: bool True to overwrite file, false to append (default)
        :param log_level: int Logging level (use LogManager default if None) for the log output
        :param format_name: str Preset format name to use (add via "add_format" function)
        :return: logging.Logger Created logger
        """
        mode = 'a' if file_overwrite is False else 'w'
        handler = logging.FileHandler(self.root_dir + "/" + file_name, mode)
        new_log = self._log_check_and_create(name,
                                             log_level,
                                             handler,
                                             format_name)
        self.add_log_file(FileLocation(self.root_dir + "/" + file_name), new_log, handler)

        return new_log

    def add_split_logger(self, file1_name, file2_name, name=None,
                         file1_overwrite=False, file2_overwrite=False,
                         file1_log_level=None, file2_log_level=None,
                         file1_format_name='standard', file2_format_name='standard'):
        """
        Add a Python logger which creates a logger which will send to to two separate files
        then stores and returns it
        :param name: str Identifier for this logger, None to autogenerate
        :param file1_name: str Name of the first file to log to
        :param file2_name: str Name of the second file to log to
        :param file1_overwrite: bool True to overwrite first file, false to append (default)
        :param file2_overwrite: bool True to overwrite second file, false to append (default)
        :param file1_log_level: int Logging level for first file logging (use LogManager default if None)
        :param file2_log_level: int Logging level for second file logging (use LogManager default if None)
        :param file1_format_name: str Preset format name to use for first file logger
        :param file2_format_name: str Preset format name to use for second file logger
        :return: logging.Logger Created logger
        """
        file1_mode = 'a' if file1_overwrite is False else 'w'
        file2_mode = 'a' if file2_overwrite is False else 'w'
        file1_handler = logging.FileHandler(self.root_dir + "/" + file1_name, file1_mode)
        new_log = self._log_check_and_create(name, file1_log_level,
                                             file1_handler,
                                             file1_format_name)

        file2_handler = logging.FileHandler(self.root_dir + "/" + file2_name, file2_mode)
        file2_handler.setLevel(file2_log_level if file2_log_level is not None else self.default_log_level)
        file2_handler.setFormatter(self.get_format(file2_format_name))

        new_log.addHandler(file2_handler)

        self.add_log_file(FileLocation(self.root_dir + "/" + file1_name), new_log, file1_handler)
        self.add_log_file(FileLocation(self.root_dir + "/" + file2_name), new_log, file2_handler)

        return new_log

    def add_tee_logger(self, file_name, name=None, file_overwrite=False,
                        file_log_level=None, stdout_log_level=None,
                        file_format_name='standard', stdout_format_name='standard'):
        """
        Add a Python logger which creates a logger which will send to std and log to a
        file, then stores and returns it
        :param name: str Identifier for this logger, None to autogenerate
        :param file_name: str Name of the file to log to
        :param file_overwrite: bool True to overwrite file, false to append (default)
        :param file_log_level: int Logging level for file logging (use LogManager default if None)
        :param stdout_log_level: int Logging level for stdout logging (use LogManager default if None)
        :param file_format_name: str Preset format name to use for file logger
        :param stdout_format_name: str Preset format name to use for stdout logger
        :return: logging.Logger Created logger
        """
        mode = 'a' if file_overwrite is False else 'w'
        handler = logging.FileHandler(self.root_dir + "/" + file_name, mode)
        new_log = self._log_check_and_create(name, file_log_level,
                                             handler,
                                             file_format_name)

        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(stdout_log_level if stdout_log_level is not None else self.default_log_level)
        stdout_handler.setFormatter(self.get_format(stdout_format_name))

        new_log.addHandler(stdout_handler)
        self.add_log_file(FileLocation(self.root_dir + "/" + file_name), new_log, handler)

        return new_log

    def add_external_log_file(self, location):
        self.external_log_files.add(location)

    def add_log_file(self, location, logger, file_handler):
        if location not in self.open_log_files:
            self.open_log_files[location] = []
        self.open_log_files[location].append((logger, file_handler))

    def collate_logs(self):
        """
        Gather all the log files into one place and tarball them up
        :return:
        """
        for l in self.loggers.itervalues():
            pass

    def _rollover_file(self, file_path, backup_dir=None,
                       date_pattern='%Y%m%d%H%M%S', zip_file=True):
        cli = LinuxCLI(priv=False)
        suff_str = '.' + datetime.datetime.now().strftime(date_pattern)
        dest_dir = backup_dir if backup_dir is not None else (self.root_dir + '/log_bak')

        if not cli.exists(dest_dir):
            cli.mkdir(dest_dir)
        dest_filename = dest_dir + '/' + os.path.basename(file_path) + suff_str

        # Move the file, zip if requested
        cli.move(file_path, dest_filename)
        if zip_file:
            cli.cmd('gzip -9 ' + dest_filename)

    # TODO: Make sure logging can have subdirs under root dir to help organize logs!
    def rollover_logs_fresh(self, backup_dir=None,
                      date_pattern='%Y%m%d%H%M%S', zip_file=True, file_filter='*.log'):
        """
        Rollover all files in root directory matching glob filter.  This assumes a fresh start,
        where there are no handlers or loggers currently active for those files (at the
        start of a server process for example)
        :type backup_dir: str
        :type date_pattern: str
        :type zip_file: bool
        :type filter: str
        :return:
        """
        print "checking dir: " + self.root_dir + '/' + file_filter
        file_list = [f
                     for f in glob.glob(self.root_dir + '/' + file_filter)
                     if os.path.isfile(f)]

        for f in file_list:
            print "checking: " + f
            if os.path.getsize(f) > 0:
                self._rollover_file(file_path=f, backup_dir=backup_dir,
                                    date_pattern=date_pattern, zip_file=zip_file)

    def rollover_logs_by_date(self, backup_dir=None,
                              date_pattern='%Y%m%d%H%M%S', zip_file=True):
        """
        If the filename exists, roll it over to a new file based on the parameters.  Return
        the name of the new file.
        :type backup_dir: str
        :type date_pattern: str
        :type zip_file: bool
        :return: str
        """
        for file_loc, logger_list in self.open_log_files.iteritems():
            cli = LinuxCLI(priv=False)
            print "checking: " + file_loc.full_path()
            if cli.exists(file_loc.full_path()) and os.path.getsize(file_loc.full_path()) > 0:

                # Close previous, now-stale file handlers
                for l, h in logger_list:
                    h.close()
                    l.removeHandler(h)

                self._rollover_file(file_loc.full_path(), backup_dir, date_pattern, zip_file)

                # Pop off old logger/handler pairs and re-populate with new handler objects
                # which point to the original file location
                for i in range(0, len(logger_list)):
                    l, h = logger_list.pop()
                    new_handler = logging.FileHandler(filename=file_loc.full_path(), mode='w')
                    l.addHandler(new_handler)
                    logger_list.append((l, new_handler))




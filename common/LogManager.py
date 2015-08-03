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
import logging


class LogManager(object):

    def __init__(self):
        self.loggers = {}
        """ :type: dict [str, Logger]"""
        self.default_log_level = logging.WARNING
        """ :type: int"""
        self.formats = {}
        """ :type: dict [str, logging.Formatter]"""

        # Set up a default, standard format
        self.add_format('standard',
                        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

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
        Add a Python logger which uses a StreamHanlder sending logs to stdout then stores and returns it
        :param name: str Identifier for this logger, None to autogenerate
        :param log_level: int Logging level (use LogManager default if None) for the log output
        :param format_name: str Preset format name to use (add via "add_format" function)
        :return: logging.Logger Created logger
        """
        return self._log_check_and_create(name, log_level, logging.StreamHandler(), format_name)

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
        mode = 'a' if file_overwrite is False else 'r'
        return self._log_check_and_create(name, log_level,
                                          logging.FileHandler(file_name, mode), format_name)

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
        file1_mode = 'a' if file1_overwrite is False else 'r'
        file2_mode = 'a' if file2_overwrite is False else 'r'
        new_log = self._log_check_and_create(name, file1_log_level,
                                             logging.FileHandler(file1_name, file1_mode), file1_format_name)

        file2_handler = logging.FileHandler(file2_name, file2_mode)
        file2_handler.setLevel(file2_log_level if file2_log_level is not None else self.default_log_level)
        file2_handler.setFormatter(self.get_format(file2_format_name))

        new_log.addHandler(file2_handler)

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
        new_log = self._log_check_and_create(name, file_log_level,
                                             logging.FileHandler(file_name, mode), file_format_name)

        stdout_handler = logging.StreamHandler()
        stdout_handler.setLevel(stdout_log_level if stdout_log_level is not None else self.default_log_level)
        stdout_handler.setFormatter(self.get_format(stdout_format_name))

        new_log.addHandler(stdout_handler)

        return new_log

    def collate_logs(self):
        """
        Gather all the log files into one place and tarball them up
        :return:
        """
        for l in self.loggers.itervalues():
            pass


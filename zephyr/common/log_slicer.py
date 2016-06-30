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

import datetime
from zephyr.common import cli

COMMON_FORMATS = [
    ('%Y.%m.%d %H:%M:%S.%f', 0),
    ('%Y-%m-%d %H:%M:%S,%f', 0),
    ('%Y-%m-%d %H:%M:%S,%f', 2),
    ('%b %d, %Y %I:%M:%S %p', 0),
    ('%Y/%m/%d %H:%M:%S', 0)
]


def slice_log_files_by_time(log_files, out_dir, slice_start_time=None,
                            slice_stop_time=None, leeway=0,
                            ext='.slice'):
    """
    Slice given log files using timestamps and copy the slice to a new
    file. The default is to start at the beginning and slice all the way
    to the end.  The leeway parameter will move the slice to n seconds
    before start and n seconds after the end time.

    Use 'ext' to set the extension on the slice files (defaults to .slice)
    :type log_files: list[FileLocation]
    :type out_dir: str
    :type slice_start_time: datetime.datetime
    :type slice_stop_time: datetime.datetime
    :type leeway: int
    :type ext: str
    :return:
    """

    concrete_start_time = slice_start_time - datetime.timedelta(seconds=leeway)
    concrete_stop_time = slice_stop_time + datetime.timedelta(seconds=leeway)

    log_file_set = log_files

    for filepath in log_file_set:
        lines_to_write = []
        if cli.LinuxCLI(priv=False).exists(filepath.full_path()):
            with open(filepath.full_path(), 'r') as cf:
                firstline = cf.readline()
                current_format = None
                current_pos = None
                for fmt, pos in COMMON_FORMATS:
                    try:
                        current_format = fmt
                        current_pos = pos
                        dateline = ' '.join(
                            firstline.split(' ')[current_pos:current_pos + 2])
                        datetime.datetime.strptime(dateline, current_format)
                        break
                    except ValueError:
                        continue
                if not current_format:
                    # No appropriate formats, so skip file
                    continue

                for line in cf.readlines():
                    dateline = ' '.join(
                        line.split(' ')[current_pos:current_pos + 2])
                    try:
                        current_time = datetime.datetime.strptime(
                            dateline, current_format)
                        if current_time < concrete_start_time:
                            continue
                        elif current_time > concrete_stop_time:
                            break
                        else:
                            lines_to_write.append(line)
                    except ValueError:
                        continue

            if len(lines_to_write) != 0:
                filename = out_dir + '/' + filepath.filename + ext
                cli.LinuxCLI(priv=False).write_to_file(
                    filename,
                    'SLICE OF LOG [' + filepath.full_path() + '] FROM [' +
                    str(concrete_start_time) + '] TO [' +
                    str(concrete_stop_time) + ']\n')
                cli.LinuxCLI(priv=False).write_to_file(
                    filename, ''.join(lines_to_write), append=True)

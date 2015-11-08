# %%writefile "sync_to_file_magic_command.py"
# %%load "sync_to_file_magic_command.py"

import re
import codecs
import os.path
import textwrap
from IPython.core.magic import (Magics,
                                magics_class,
                                cell_magic)

from IPython.core.magic_arguments import (argument,
                                          magic_arguments,
                                          parse_argstring)

from IPython.utils.path import unquote_filename


# def modify_fun_add_pattern_by_adding_prefix(_message_str):
#     def add_pattern(_str):
#         return _message_str + '\n ' + repr(_str)
#     return add_pattern


def format_log(_str_l):
    # first_level_indent = 0
    second_level_indent = 2
    third_level_indent = 4
    formatted_str_l = []
    match_wrap_re = re.compile(r"^-wrap(\d*) ")
    for _str in _str_l:
        assert isinstance(_str, basestring)
        if _str.startswith(('#', )):
            formatted_str = _str
        elif _str.startswith(('##', '--', '++', '!!')):
            formatted_str = ' '*second_level_indent + _str
        else:
            match_result = match_wrap_re.match(_str)
            if not (match_result is None):
                extra_indent = match_result.group(1)
                extra_indent = 0 if extra_indent == '' else int(extra_indent)
                str_start = match_result.end()
                total_indent = third_level_indent + extra_indent
                _str = _str[str_start:].replace('\n', '\\n')
                formatted_str = textwrap.fill(_str,
                                              initial_indent=' '*total_indent,
                                              subsequent_indent=' '*total_indent)
            else:
                formatted_str = ' '*third_level_indent + _str
        formatted_str_l.append(formatted_str)
    return '\n'.join(formatted_str_l)


def construct_indent_line_re(_cell_str, escape=True, arbitrary_end=False):
    _re_str_l = []
    for _cell_line in _cell_str.split('\n'):
        _cell_line = _cell_line.rstrip(' \t')
        if escape:
            _cell_line = re.escape(_cell_line)
        _cell_line = '^[ \t]*' + _cell_line
        if arbitrary_end:
            _cell_line += '.*$'
        else:
            _cell_line += '[ \t]*$'
        _re_str_l.append(_cell_line)
    _re_str = '\n'.join(_re_str_l)
    return _re_str


def convert_to_unix_line_feed(_str):
    match_rn_re = re.compile('\r\n', re.M)
    match_r_re = re.compile('\r', re.M)
    _str = match_rn_re.sub('\n', _str)
    _str = match_r_re.sub('\n', _str)
    return _str


def search_target_str(_re_str, _target_str, _re_flag, _start_pos=None, _end_pos=None):
    """
    iterfind the _target_str,
    return the number of matches and the first match object
    :param _re_str: the string of regular expression pattern
    :param _target_str: the string to search pattern in
    :param _re_flag: an int, the flag of regular expression
    :param _start_pos: the start pos to search in
    :param _end_pos: the end pos to to search in
    :return: an int, a match object(could be None)
    """
    _re = re.compile(_re_str, _re_flag)
    _n_match = 0
    _first_match_obj = None
    if _start_pos is None:
        _start_pos = 0
    if _end_pos is None:
        _end_pos = len(_target_str)
    for one_match_obj in _re.finditer(_target_str, _start_pos, _end_pos):
        if _n_match == 0:
            _first_match_obj = one_match_obj
        _n_match += 1
    return _n_match, _first_match_obj


@magics_class
class SyncToFile(Magics):

    # m:multiple match, u:unique match, n:no match
    match_result_prefix_d = {'m': 'Multiple match of pattern',
                             'u': 'Unique match of pattern',
                             'n': 'No match of pattern'}
    # add_prefix_fun_d =\
    #   {'m': modify_fun_add_pattern_by_adding_prefix('Multiple match of pattern'),
    #    'u': modify_fun_add_pattern_by_adding_prefix('Unique match of pattern'),
    #    'n': modify_fun_add_pattern_by_adding_prefix('No match of pattern')}

    @magic_arguments()
    @argument('-a', '--after', type=str,
              help='search after this pattern.')
    @argument('-b', '--before', type=str,
              help='search before this pattern')
    @argument('-m', '--mode', type=str, choices=['o', 'i', 'a', 'di', 'da'], default='da',
              help='''the mode of how to synchronize
                      o: overwrite,
                         use the cell to overwrite the search region
                      i: insert,
                         write the cell at the top of the search region
                      a: append,
                         write the cell at the bottom the search region
                      di: first match the cell as whole,
                          if no match, insert the cell
                      da: first match the cell as whole,
                          if no match, insert the cell''')
    @argument('-p', '--pass', action='store_true',
              help='do not execute the code')
    @argument('-r', '--reg', type=str,
              help='''treat -a -b as regular expression
                      reg flag is required,
                      the programme use re.M|re.S as default
                      use the flag 'd' if you don't want to
                      change the default setting''')
    @argument('-i', '--indent', type=int, default='0',
              help='force indentation')
    @argument('-l', '--log', action='store_true',
              help='report the running log of this programme')
    @argument('-t', '--test', action='store_true',
              help='do not write into the file, only report the "as if" result')
    @argument('file', type=str, nargs='+',
              help='a list of path to files')
    @cell_magic
    def sync_to_file(self, line, cell):
        """
        assume the target file(s) is encoded in 'utf-8' and only use '\n' as line end
        run the code in cell and sync it with target file(s), encoding using 'utf-8'

        the programme will first determine the search region based on the -a and -b option
        once the region is figured out, what to do next depends on option -m
        if the mode of synchronization is update, then the programme will try to detect the
        write region use the content of the code cell
        :type line: unicode
        :type cell: unicode
        :param line: the arguments passed to the magic command
        :param cell: the lines of the cell below the magic command
        """
        # set the framework of necessary parameters
        log_message_l = []
        par_d = {'args_d': None,
                 'file_path_l': None,
                 'target_str_l': None,
                 'n_target_str': None,
                 'search_start_index_l': None,
                 'search_end_index_l': None,
                 'cell': cell,
                 'cell_line_l': None,
                 'n_cell_line_l': None,
                 'modified_target_str_l': None}
        # get args
        args_d = vars(parse_argstring(self.sync_to_file, line))
        par_d['args_d'] = args_d
        log_message_l.append('# Parsing arguments...')
        log_message_l.append('-wrap2 ' + str(args_d))
        # run the code
        log_message_l.append('# Running the cell...')
        if not args_d['pass']:
            self.shell.run_cell(cell)
        # read content of files as str
        # if file does not exists, set the str as empty string
        file_path_l = [unquote_filename(_file_path) for _file_path in args_d['file']]
        target_str_l = []
        log_message_l.append('# Reading files...')
        for file_path in file_path_l:
            if os.path.exists(file_path):
                with codecs.open(file_path, 'r', encoding='utf-8') as f:
                    # convert \r\n to \n
                    _raw_str = f.read()
                    target_str_l.append(convert_to_unix_line_feed(_raw_str))
            else:
                target_str_l.append('')
        n_target_str = len(target_str_l)
        par_d['file_path_l'], par_d['target_str_l'], par_d['n_target_str'] = \
            file_path_l, target_str_l, n_target_str
        # set core variables
        self.set_search_region(log_message_l, par_d)
        # modify target str
        self.modify_target_str(log_message_l, par_d)
        # write the modified target str to target file
        if not args_d['test']:
            log_message_l.append('# Write target file(s)..')
            for target_index, write_str in enumerate(par_d['modified_target_str_l']):
                file_path = file_path_l[target_index]
                # log_message_l.append('++ Deal with file ' + file_path)
                with codecs.open(file_path, 'w', encoding='utf-8') as f:
                    f.write(write_str)
                # log_message_l.append('-- Finished. File: ' + file_path)
        else:
            log_message_l.append('#Test mode. No file is changed.')
        # output programme log if required
        if args_d['log']:
            print format_log(log_message_l)

    def set_search_region(self, _log_message_l, _par_d):
        # determine the scope to search
        file_path_l = _par_d['file_path_l']
        n_target_str = _par_d['n_target_str']
        target_str_l = _par_d['target_str_l']
        args_d = _par_d['args_d']
        search_start_index_l = [0 for _ in range(n_target_str)]
        search_end_index_l = [len(_str) for _str in target_str_l]
        _log_message_l.append('# Set the scope to search')
        has_after_arg = False if (args_d['after'] is None) or (args_d['after'] == '') else True
        has_before_arg = False if (args_d['before'] is None) or (args_d['before'] == '') else True
        has_both_arg = has_after_arg and has_before_arg
        is_re_mode = False if args_d['reg'] is None else True
        scope_re_flag = 're.S'
        if not (args_d['reg'] is None) and (args_d['reg'] != 'd'):
            scope_re_flag = scope_re_flag + '|' + args_d['reg']
        scope_re_flag = eval(scope_re_flag)
        if not is_re_mode:
            # escape meta char's of reg in the str
            if has_after_arg:
                args_d['after'] = re.escape(args_d['after'])
            if has_before_arg:
                args_d['before'] = re.escape(args_d['before'])
        # determine search_scope_re_str
        if has_both_arg:
            search_scope_re_str = '(' + args_d['after'] + ')(.*)(' + args_d['before'] + ')'
        elif has_after_arg:
            search_scope_re_str = args_d['after']
        elif has_before_arg:
            search_scope_re_str = args_d['before']
        else:
            search_scope_re_str = None
        if not (search_scope_re_str is None):
            # search and set search_start_index and search_end_index for every target
            for target_index, target_str in enumerate(target_str_l):
                _log_message_l.append('++ Deal with file ' +
                                      file_path_l[target_index])
                if target_str == '':
                    _log_message_l.append('-- Skipped. No content or not exist: ' +
                                          file_path_l[target_index])
                    continue
                n_match, first_match_obj = search_target_str(search_scope_re_str, target_str,
                                                             scope_re_flag)
                try_before_arg_flag = False
                try_after_arg_flag = False
                if n_match == 0:
                    self.log_match_result(_log_message_l, search_scope_re_str, 'n')
                    if has_both_arg:
                        try_before_arg_flag = True
                else:
                    if n_match > 1:
                        self.log_match_result(_log_message_l, search_scope_re_str, 'm')
                    else:
                        self.log_match_result(_log_message_l, search_scope_re_str, 'u')
                    if has_both_arg:
                        search_start_index_l[target_index] = first_match_obj.end(1)
                        search_end_index_l[target_index] = first_match_obj.start(3)
                    elif has_after_arg:
                        search_start_index_l[target_index] = first_match_obj.end()
                    else:  # has_before_arg
                        search_end_index_l[target_index] = first_match_obj.start()
                if try_before_arg_flag:
                    # no -a and -b pattern, try the -b pattern
                    _log_message_l.append('Restricted to the before pattern')
                    n_match, first_match_obj = search_target_str(args_d['before'], target_str,
                                                                 scope_re_flag)
                    if n_match == 0:
                        self.log_match_result(args_d['before'], 'n')
                        try_after_arg_flag = True
                    else:
                        if n_match > 1:
                            self.log_match_result(args_d['before'], 'm')
                        else:
                            self.log_match_result(args_d['before'], 'u')
                        search_end_index_l[target_index] = first_match_obj.start()
                if try_after_arg_flag:
                    # no -a and -b pattern, no -b pattern, last try -a pattern
                    _log_message_l.append('Last try the after pattern')
                    n_match, first_match_obj = search_target_str(args_d['after'], target_str,
                                                                 scope_re_flag)
                    if n_match == 0:
                        self.log_match_result(_log_message_l, args_d['after'], 'n')
                        _log_message_l.append('All tries failed! The search scope remains as default')
                    else:
                        if n_match > 1:
                            self.log_match_result(_log_message_l, args_d['after'], 'm')
                        else:
                            self.log_match_result(_log_message_l, args_d['after'], 'u')
                        search_start_index_l[target_index] = first_match_obj.end()
                _log_message_l.append('-- Finished. File: ' + file_path_l[target_index])
        else:
            _log_message_l.append('No argument is provided. The search scope remains as default')
        _par_d['search_start_index_l'], _par_d['search_end_index_l'] = \
            search_start_index_l, search_end_index_l

    @staticmethod
    def modify_target_str(_log_message_l, _par_d):
        _log_message_l.append('# Begin to modify the target str')
        file_path_l = _par_d['file_path_l']
        n_target_str = _par_d['n_target_str']
        target_str_l = _par_d['target_str_l']
        cell = _par_d['cell']
        args_d = _par_d['args_d']
        search_start_index_l = _par_d['search_start_index_l']
        search_end_index_l = _par_d['search_end_index_l']
        indent = args_d['indent']
        indented_cell_l = []
        # pre process the cell: skip lines that are blank
        # before the first non blank line or after the last non blank line
        cell = cell.strip()
        cell_line_l = [] if cell == '' else cell.split('\n')
        n_cell_line = len(cell_line_l)
        modified_target_str_l = [target_str_l[i] for i in range(n_target_str)]
        update_d = {'cell': cell, 'cell_line_l': cell_line_l,
                    'n_cell_line': n_cell_line,
                    'modified_target_str_l': modified_target_str_l}
        _par_d.update(update_d)
        if n_cell_line == 0:
            # nothing to write
            _log_message_l.append('!! Empty cell. Nothing to write.')
            return
        # indent cell for writing
        for cell_line in cell_line_l:
            indented_cell_l.append(' '*indent + cell_line)
        indented_cell = '\n'.join(indented_cell_l)
        # log writing mode
        append_message_d = {'o': '!! Writing mode is overwrite.',
                            'i': '!! Writing mode is insert.',
                            'a': '!! Writing mode is append.',
                            'di': '!! Writing mode is different and insert.',
                            'da': '!! Writing mode is different and append.'}
        _log_message_l.append(append_message_d[args_d['mode']])
        # begin to build modified str
        for target_index, target_str in enumerate(target_str_l):
            file_path = file_path_l[target_index]
            _log_message_l.append('++ Deal with file ' + file_path)
            start_index = search_start_index_l[target_index]
            end_index = search_end_index_l[target_index]
            if target_str == '':
                _log_message_l.append('Target file is empty.')
                modified_target_str_l[target_index] = indented_cell
            else:
                left_segment_end = None
                right_segment_start = None
                if args_d['mode'] == 'o':
                    left_segment_end = start_index
                    right_segment_start = end_index
                elif args_d['mode'] in ['i', 'di']:
                    left_segment_end = start_index
                    right_segment_start = start_index
                else:
                    # args_d['mode'] in ['a', 'da']:
                    left_segment_end = end_index
                    right_segment_start = end_index
                if args_d['mode'] in ['da', 'di']:
                # try to match the cell as whole
                    _log_message_l.append('Try to match the cell as whole.')
                    cell_re = construct_indent_line_re(cell)
                    n_match, _ = search_target_str(cell_re, target_str, re.M,
                                                   start_index, end_index)
                    if n_match > 0:
                        _log_message_l.append('Whole cell matched. No need to update.')
                        left_segment_end = None
                        right_segment_start = None
                if not (left_segment_end is None):
                    modified_str = target_str[:left_segment_end]
                    if modified_str != '':
                        if modified_str[-1] != '\n':
                            modified_str += '\n'
                    modified_str += indented_cell
                    if modified_str[-1] != '\n':
                        modified_str += '\n'
                    modified_str += target_str[right_segment_start:]
                    modified_target_str_l[target_index] = modified_str
                    _log_message_l.append('Target str is modified')
            _log_message_l.append('-- Finished. File: ' + file_path)

    @staticmethod
    def log_match_result(_log_l, pattern_str, key_word='u'):
        _log_l.append(SyncToFile.match_result_prefix_d[key_word])
        formatted_pattern_str = '-wrap2 ' + pattern_str
        _log_l.append(formatted_pattern_str)
        

# In order to actually use these magics, you must register them with a
# running IPython.  This code must be placed in a file that is loaded once
# IPython is up and running:
ip = get_ipython()
# You can register the class itself without instantiating it.  IPython will
# call the default constructor on it.
ip.register_magics(SyncToFile)
from platform import system
from os import environ

IS_MAC_OS = system() == 'Darwin'

LEAKS_CHECKER_NAME = 'leaks' if IS_MAC_OS else 'Valgrind'
LEAKS_CHECKER_COMMAND = 'export MallocStackLogging=1 && leaks --atExit --' \
    if IS_MAC_OS else 'valgrind --leak-check=full'

NO_LEAKS_FOUND_TEXT = '0 leaks for 0 total leaked bytes.' if IS_MAC_OS else 'no leaks are possible'


# Define constants
STDOUT = 0
STDERR = 1

TESTS_JSON_FILE_INDEX = 1
EXECUTABLE_INDEX = 2
EXPECTED_ARGS_AMOUNT = 3

HTML_COLORED_NEWLINE = '<span style="background-color: orange;">\\n</span><br/>'
HTML_COLORED_WHITESPACE = '<span style="background-color: #BE5103;">&nbsp;</span>'  # burnt orange
NORMAL_HTML_NEWLINE = '<br/>'

TEST_NAME = 'name'
TEMPLATE_NAME = 'template'
PARAMS = 'params'
OUTPUT_FILE = 'output_file'
EXPECTED_OUTPUT_FILE = 'expected_output_file'
EXPECTED_OUTPUT_IS_SUBSTR = 'expected_output_is_substring'
TEMP_REPORT = 'test_results_current.html'
FINAL_REPORT = 'test_results.html'

TIMEOUT = int(environ.get('MATAM_TESTER_TEST_TIMEOUT', '1'))  # 1 second
VALGRIND_TIMEOUT = int(environ.get('MATAM_TESTER_VALGRIND_TIMEOUT', '2'))  # 2 seconds

COMPARISON_TRIM_END_SPACES = int(environ.get('MATAM_TESTER_TRIMR_SPACES', '0'))
COMPARISON_IGNORE_BLANK_LINES = int(environ.get('MATAM_TESTER_IGNORE_EMPTY_LINES', '0'))

RUN_MULTI_THREAD = int(environ.get('MATAM_TESTER_RUN_MULTI_THREADED', '0')) == 1
EXPORT_TEMP_REPORT = int(environ.get('MATAM_TESTER_EXPORT_TEMP_REPORT', '0')) == 1

USE_OLD_DIFF_STYLE = int(environ.get('MATAM_TESTER_USE_OLD_DIFF_STYLE', '0')) == 1
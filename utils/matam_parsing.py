import sys

from utils.config import IS_MAC_OS, EXPECTED_OUTPUT_FILE, EXPECTED_OUTPUT_IS_SUBSTR, NORMAL_HTML_NEWLINE, \
    LEAKS_CHECKER_NAME
from utils.matam_types import Summary, TestCase, TestParamRange, TestParams

if sys.version_info < (3, 10):
    sys.exit("Python %s.%s or later is required.\n" % (3, 10))
else:
    from typing import List, Any, Iterable

def normalize_newlines(txt: str) -> str:
    return txt.replace('\r\n', '\n').replace('\r', '\n')


def test_exception_to_error_text(exception: Exception) -> str:
    if exception.stderr:
        return str(exception.stderr)
    if exception.stdout:
        return str(exception.stdout)
    return str(exception)


def remove_error_pipes_from_command(command: str) -> str:
    """
    Avoid pipe of stderr to output file to allow leaks test to work as normal
    :param command:
    :return:
    """
    command_without_err_pipe: str = command
    # macOs uses leaks which uses stdout, thus we need to undo the piping of it
    if IS_MAC_OS:
        index_of_out_pipe = command_without_err_pipe.rfind('>')
        if index_of_out_pipe != -1:
            command_without_err_pipe = command_without_err_pipe[:index_of_out_pipe]
        index_of_err_out_pipe = command_without_err_pipe.rfind('&>')
        if index_of_err_out_pipe != -1:
            command_without_err_pipe = command_without_err_pipe[:index_of_err_out_pipe]
        index_of_err_pipe = command_without_err_pipe.rfind('2>')
        if index_of_err_pipe != -1:
            command_without_err_pipe = command_without_err_pipe[:index_of_err_pipe]
        # If stderr is piped to stdout, remove said piping
        return command_without_err_pipe.replace('&>1', '>').replace('2>&1', '')
    else:
        index_of_err_pipe = command_without_err_pipe.rfind('2>')
        index_of_out_pipe = command_without_err_pipe.rfind('>')

        if index_of_err_pipe != -1:
            if index_of_out_pipe > index_of_err_pipe:
                command_without_err_pipe = command_without_err_pipe[
                                           :index_of_err_pipe] + command_without_err_pipe[
                                                                 index_of_out_pipe:]
            else:
                command_without_err_pipe = command_without_err_pipe[:index_of_err_pipe]

        # If stderr is piped to stdout, remove said piping
        return command_without_err_pipe.replace('&>1', '>').replace('2>&1', '')


def summarize_failed_test(test_name: str, expected_output: str, actual_output: str, diff_html: str) -> Summary:
    return Summary(
        title=f"{test_name} - Failed!",
        expected=expected_output,
        actual=actual_output,
        error=None,
        diff_html=diff_html
    )


def summarize_failed_test_due_to_exception(test_name: str, expected_output: str,
                                           exception: str) -> Summary:
    return Summary(
        title=f"{test_name} - Failed due to an error in the tester!",
        expected=expected_output,
        error=exception
    )


def summarize_failed_to_check_for_leaks(test_name: str, exception: str) -> Summary:
    return Summary(
        title=f'{test_name} has leaks!{NORMAL_HTML_NEWLINE}Failed due to an error raised by {LEAKS_CHECKER_NAME}!',
        error=exception
    )


def parse_test_placeholders(field: str, ranged_value: Any) -> str:
    return field.replace(':::placeholder:::', str(ranged_value))


def parse_ranged_tests(tests: List[TestCase]) -> List[TestCase]:
    for index, test in enumerate(tests):
        test_range: TestParamRange | List[str] | None = test.get('params_range', None)
        if test_range:
            ranged_values: Iterable[Any]
            if type(test_range) == dict:
                ranged_values = range(test_range['first'], test_range['last'] + 1)
            # In this case it will be a list of strs
            else:
                ranged_values = test_range
            for range_item in ranged_values:
                parsed_params: TestParams = dict()
                for name, value in test['params'].items():
                    parsed_value = parse_test_placeholders(value, range_item)
                    parsed_params[name] = parsed_value

                parsed_test = {
                    'name': parse_test_placeholders(test['name'], range_item),
                    'template': test['template'],
                    'params': parsed_params,
                    'output_file': parse_test_placeholders(test['output_file'], range_item),
                    EXPECTED_OUTPUT_FILE: parse_test_placeholders(test[EXPECTED_OUTPUT_FILE], range_item),
                    'run_leaks': test.get('run_leaks', None),
                    EXPECTED_OUTPUT_IS_SUBSTR: test.get(EXPECTED_OUTPUT_IS_SUBSTR, False)
                }

                tests.append(parsed_test)

    # Remove unparsed tests
    return [test for test in tests if 'params_range' not in test]
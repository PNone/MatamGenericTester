import sys
from os import getcwd, chdir, linesep
from os.path import dirname, join, normpath, isfile, isdir
import subprocess
import json

from multiprocessing.dummy import Pool as ThreadPool

from utils.config import RUN_MULTI_THREAD, FINAL_REPORT, EXECUTABLE_INDEX, TESTS_JSON_FILE_INDEX, \
    EXPECTED_ARGS_AMOUNT, \
    TIMEOUT, COMPARISON_IGNORE_BLANK_LINES, COMPARISON_TRIM_END_SPACES, VALGRIND_TIMEOUT, STDERR, \
    STDOUT, \
    LEAKS_CHECKER_NAME, NO_LEAKS_FOUND_TEXT, TEMPLATE_NAME, PARAMS, TEST_NAME, EXPECTED_OUTPUT_FILE, \
    EXPECTED_OUTPUT_IS_SUBSTR, OUTPUT_FILE, EXPORT_TEMP_REPORT, LEAKS_CHECKER_COMMAND, TEMP_REPORT
from utils.loading_bar import print_progress_bar
from utils.matam_html import create_html_report_from_results
from utils.matam_parsing import summarize_failed_test_due_to_exception, \
    test_exception_to_error_text, \
    normalize_newlines, summarize_failed_test, summarize_failed_to_check_for_leaks, \
    remove_error_pipes_from_command, \
    parse_ranged_tests
from utils.matam_types import TestResult, TestFile, Summary, TestCase, TestTemplates

if sys.version_info < (3, 10):
    sys.exit("Python %s.%s or later is required.\n" % (3, 10))
else:
    from typing import get_type_hints


def execute_test(command: str, relative_workdir: str, name: str, expected_output: str,
                 output_path: str,
                 results: list[TestResult], expected_is_substr: bool = False) -> None:
    try:
        with subprocess.Popen(command, shell=True, cwd=getcwd()) as proc:
            try:
                proc.communicate(timeout=TIMEOUT)
            except subprocess.TimeoutExpired as e:
                proc.kill()
                results.append({
                    'name': name,
                    'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                                      test_exception_to_error_text(
                                                                          e)),
                    'passed': False,
                    'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
                })
                return
    except subprocess.CalledProcessError as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              test_exception_to_error_text(e)),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return
    except subprocess.TimeoutExpired as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              test_exception_to_error_text(e)),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return
    except Exception as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output, str(e)),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return

    try:
        # norm path makes sure the path is formatted correctly
        with open(normpath(output_path), "r", encoding='utf-8') as file:
            actual_output = normalize_newlines(file.read())
    except UnicodeDecodeError as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              f'Test printed invalid output. Exception: {str(e)}'),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return
    except FileNotFoundError as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              f'Test failed to provide output. Exception: {str(e)}'),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return

    # Remove blank lines
    if COMPARISON_IGNORE_BLANK_LINES != 0:
        actual_output = linesep.join([s for s in actual_output.splitlines() if s])
        expected_output = linesep.join([s for s in expected_output.splitlines() if s])

    # Trim spaces from end of lines
    if COMPARISON_TRIM_END_SPACES != 0:
        actual_output = linesep.join([s.rstrip() for s in actual_output.splitlines()])
        expected_output = linesep.join([s.rstrip() for s in expected_output.splitlines()])

    compare_result: bool = actual_output == expected_output
    if expected_is_substr:
        compare_result = expected_output in actual_output

    if compare_result:
        results.append({
            'name': name,
            'summary': Summary(title=f"\n{name} - Passed!\n"),
            'passed': True
        })
    else:
        results.append({
            'name': name,
            'summary': summarize_failed_test(name, expected_output, actual_output),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })


def execute_memory_leaks_test(command: str, relative_workdir: str, name: str,
                              results: list[TestResult]) -> None:
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                cwd=getcwd())
        try:
            proc_result = proc.communicate(timeout=VALGRIND_TIMEOUT)
            result = proc_result[STDERR] if proc_result[STDERR] else proc_result[STDOUT]
        except subprocess.TimeoutExpired:
            proc.kill()
            result = proc.communicate()
            # Try using stderr or fallback to stdout
            result = result[STDERR] if result[STDERR] else result[STDOUT]
        try:
            actual_output = normalize_newlines(result.decode('utf-8'))
        except UnicodeDecodeError:
            actual_output = normalize_newlines(result.decode('windows-1252'))

    except subprocess.CalledProcessError as e:
        results.append({
            'name': f'{name} - {LEAKS_CHECKER_NAME}',
            'summary': summarize_failed_to_check_for_leaks(name, test_exception_to_error_text(e)),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return
    except subprocess.TimeoutExpired as e:
        results.append({
            'name': f'{name} - {LEAKS_CHECKER_NAME}',
            'summary': summarize_failed_to_check_for_leaks(name, test_exception_to_error_text(e)),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return
    except Exception as e:
        results.append({
            'name': f'{name} - {LEAKS_CHECKER_NAME}',
            'summary': summarize_failed_to_check_for_leaks(name, str(e)),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })

        return

    if NO_LEAKS_FOUND_TEXT in actual_output:
        results.append({
            'name': f'{name} - {LEAKS_CHECKER_NAME}',
            'summary': Summary(title=f"\n{name} - no Leaks!\n"),
            'passed': True
        })
        return
    else:
        results.append({
            'name': f'{name} - {LEAKS_CHECKER_NAME}',
            'summary': summarize_failed_to_check_for_leaks(name, actual_output),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })


def run_test(executable_path: str, relative_workdir: str, initial_workdir: str, test: TestCase,
             templates: TestTemplates,
             results: list[TestResult], total_tests: int) -> None:
    for key, key_type in get_type_hints(TestCase).items():
        if key == 'params_range':
            continue

        # If key is missing and None is not a valid type for said key
        if key not in test and not isinstance(None, key_type.__args__):
            name = test.get("name", "<missing>")
            results.append({
                'name': name,
                'summary': Summary(
                    title=f"\nTest \"{name}\": \"{key}\" missing from test object\n"),
                'passed': False
            })
            print_progress_bar(len(results), total_tests, prefix='Progress:', suffix='Complete',
                               length=50)
            return

    args: str = templates[test[TEMPLATE_NAME]]
    for param_name, param_value in test[PARAMS].items():
        args = args.replace(f':::{param_name}:::', param_value)

    name: str = test[TEST_NAME]
    expected_output_path = test.get(EXPECTED_OUTPUT_FILE, None)
    expected_is_substr: bool = test.get(EXPECTED_OUTPUT_IS_SUBSTR, False)
    # norm path makes sure the path is formatted correctly
    with open(normpath(expected_output_path), "r", encoding='utf-8') as file:
        expected_output = normalize_newlines(file.read())

    output_path = test[OUTPUT_FILE]
    test_command: str = f'{executable_path} {args}'

    execute_test(test_command, relative_workdir, name,
                 expected_output, output_path, results, expected_is_substr=expected_is_substr)
    if test.get("run_leaks") is not False:
        command_without_err_pipes: str = remove_error_pipes_from_command(test_command)
        leaks_check_command: str = f'{LEAKS_CHECKER_COMMAND} {command_without_err_pipes}'
        execute_memory_leaks_test(leaks_check_command, relative_workdir, name, results)
    # Advancing progress bar
    print_progress_bar(len(results), total_tests, prefix='Progress:', suffix='Complete', length=50)
    if EXPORT_TEMP_REPORT and not RUN_MULTI_THREAD:
        create_html_report_from_results(results, initial_workdir, TEMP_REPORT)


def get_tests_data_from_json(tests_file_path: str) -> TestFile:
    try:
        with open(tests_file_path, "r", encoding='utf-8') as file:
            json_data = json.load(file)
            return json_data
    except (IOError, json.JSONDecodeError) as e:
        print(f"Error reading tests JSON file: {e}")
        raise e
    except Exception as e:
        print(f"Unexpected error reading tests JSON file: {e}")
        raise e


def main():
    # Expect 3 at least args: script name, json path, executable path (may comprise multiple args if command is complex)
    if len(sys.argv) < EXPECTED_ARGS_AMOUNT:
        print(
            f"Bad Usage of local tester, make sure executable path and json test file's path are passed properly." +
            f" Total args passed: {len(sys.argv)}"
        )
        return

    initial_workdir = getcwd()

    # If EXECUTABLE_INDEX is a file, wrap it in ' so it works even with spaces in path
    exec_path = normpath(join(initial_workdir, sys.argv[EXECUTABLE_INDEX]))
    if isfile(exec_path):
        executable = f"'{exec_path}'"
    else:
        executable = exec_path

    # Build executable. May include multiple inputs, any input that comes beginning in EXECUTABLE_INDEX
    if len(sys.argv) > EXPECTED_ARGS_AMOUNT:
        for i in range(EXECUTABLE_INDEX + 1, len(sys.argv)):
            # norm path makes sure the path is formatted correctly
            # If arg is a file or a dir, wrap it in ' in case it contains a space
            curr_arg = normpath(join(initial_workdir, sys.argv[i]))
            if isfile(curr_arg) or isdir(curr_arg):
                curr_arg = f"'{curr_arg}'"
            executable += ' ' + curr_arg
    tests_file_path = normpath(join(initial_workdir, sys.argv[TESTS_JSON_FILE_INDEX]))

    workdir = dirname(tests_file_path)
    relative_workdir = dirname(sys.argv[TESTS_JSON_FILE_INDEX])
    chdir(workdir)

    tests_data: TestFile = get_tests_data_from_json(tests_file_path)
    tests_data['tests'] = parse_ranged_tests(tests_data['tests'])
    results: list[TestResult] = []

    print("Running tests, please wait", end="", flush=True)
    fn_args = []

    total_tests: int = 0
    for test in tests_data['tests']:
        # Default for run_leaks is true (for example, if not specified/defined)
        if test.get('run_leaks', True):
            total_tests += 2
        else:
            total_tests += 1

    print_progress_bar(0, total_tests, prefix='Progress:', suffix='Complete', length=50)
    for test in tests_data['tests']:
        fn_args.append(
            (executable, relative_workdir, initial_workdir, test, tests_data['templates'], results,
             total_tests)
        )

    if RUN_MULTI_THREAD:
        # none to use cpu count
        pool = ThreadPool(None)

        pool.starmap(run_test, fn_args)

        pool.close()
        pool.join()
    else:
        for args in fn_args:
            run_test(*args)

    # Print new line to avoid console starting on same line as the loading bar
    print("\n", end="", flush=True)
    create_html_report_from_results(results, initial_workdir, FINAL_REPORT)
    chdir(initial_workdir)


if __name__ == "__main__":
    main()

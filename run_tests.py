import sys
from os import environ, getcwd, chdir
from os.path import dirname, join, normpath
import subprocess
import json
from platform import system

if sys.version_info < (3, 10):
    sys.exit("Python %s.%s or later is required.\n" % (3, 10))
else:
    from typing import TypedDict, TypeAlias, get_type_hints

TestTemplates: TypeAlias = dict[str, str]
TestParams: TypeAlias = dict[str, str]

IS_MAC_OS = system() == 'Darwin'

LEAKS_CHECKER_NAME = 'leaks' if IS_MAC_OS else 'Valgrind'
LEAKS_CHECKER_COMMAND = 'export MallocStackLogging=1 && leaks --atExit --' \
    if IS_MAC_OS else 'valgrind --leak-check=full'

NO_LEAKS_FOUND_TEXT = '0 leaks for 0 total leaked bytes.' if IS_MAC_OS else 'no leaks are possible'


class TestCase(TypedDict):
    name: str
    template: str
    params: TestParams
    output_file: str
    expected_output_file: str
    run_leaks: bool | None


class TestFile(TypedDict):
    templates: TestTemplates
    tests: list[TestCase]


class Summary(TypedDict):
    title: str
    actual: str | None
    expected: str | None
    error: str | None


class TestResult(TypedDict):
    name: str
    summary: Summary
    passed: bool
    command: str | None


# Define constants
STDOUT = 0
STDERR = 1

EXECUTABLE_INDEX = 1
TESTS_JSON_FILE_INDEX = 2
EXPECTED_ARGS_AMOUNT = 3

HTML_COLORED_NEWLINE = '<span style="background-color: orange;">\\n</span><br/>'
HTML_COLORED_WHITESPACE = '<span style="background-color: red;">&nbsp;</span>'
NORMAL_HTML_NEWLINE = '<br/>'

TEST_NAME = 'name'
TEMPLATE_NAME = 'template'
PARAMS = 'params'
OUTPUT_FILE = 'output_file'
EXPECTED_OUTPUT_FILE = 'expected_output_file'

TIMEOUT = int(environ.get('LOCAL_GRADESCOPE_TIMEOUT', '1'))  # 1 second
VALGRIND_TIMEOUT = int(environ.get('LOCAL_GRADESCOPE_VALGRIND_TIMEOUT', '2'))  # 2 seconds


def simple_html_format(text: str) -> str:
    return text.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')


def format_test_string_for_html(field: str, field_title: str) -> str:
    less_than = '<'
    greater_than = '>'
    field = field.replace(less_than, '&lt;').replace(greater_than, '&gt;')
    field = field.replace(' \n', f'{HTML_COLORED_WHITESPACE}\n')
    field = field.replace('\n\n', f'{HTML_COLORED_NEWLINE}{NORMAL_HTML_NEWLINE}')
    if field.endswith('\n'):
        field = field[:-1] + HTML_COLORED_NEWLINE
    if field.endswith(' '):
        field = field[:-1] + HTML_COLORED_WHITESPACE
    field = field.replace('\n', NORMAL_HTML_NEWLINE)
    return f'<div class="grid-child-element"><p>{field_title}</p><p>{field}</p></div>'


def format_summary_for_html(summary: Summary) -> str:
    report = ''
    report += f'<p>{summary.get("title")}</p>'
    report += '<div class="grid-container-element">'
    expected: str = summary.get("expected")
    if expected is not None:
        report += format_test_string_for_html(expected, 'Expected Output:')
    error: str = summary.get("error")
    if error is not None:
        report += format_test_string_for_html(error, 'Error:')
    actual: str = summary.get("actual")
    if actual is not None:
        report += format_test_string_for_html(actual, 'Actual Output:')
    report += '</div>'
    return report


def generate_summary_html_content(results: list[TestResult], amount_failed: int) -> str:
    html = '''
<!DOCTYPE html>
<html>
<head>

</head>
<body>


    '''
    html += f'<h2><span style="color:red;">{amount_failed} Failed</span> out of {len(results)}</h2>'
    for result in results:
        command_element: str = f"<p>Test Command:</p><code>{simple_html_format(result['command'])}</code>" \
            if result.get('command', None) else ''
        html += f'''
        <button type="button" class="collapsible" style="color:{'green' if result['passed'] else 'red'}">
        {result['name']}</button>
<div class="content">
  {command_element}
  <p>{format_summary_for_html(result.get('summary'))}</p>
</div>
'''

    html += '''
</body>
</html>'''

    html += '''
<script>
var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.display === "block") {
      content.style.display = "none";
    } else {
      content.style.display = "block";
    }
  });
}
</script>
<style>
.collapsible {
  background-color: #eee;
  color: #444;
  cursor: pointer;
  padding: 18px;
  width: 100%;
  border: none;
  text-align: left;
  outline: none;
  font-size: 15px;
}

/* Add a background color to the button if it is clicked on (add the .active class with JS), and when you move the mouse over it (hover) */
.active, .collapsible:hover {
  background-color: #ccc;
}

/* Style the collapsible content. Note: hidden by default */
.content {
  padding: 0 18px;
  display: none;
  overflow: hidden;
  background-color: #f1f1f1;
}
.collapsible:after {
  content: '\\02795'; /* Unicode character for "plus" sign (+) */
  font-size: 13px;
  color: white;
  float: right;
  margin-left: 5px;
}

.active:after {
  content: "\\2796"; /* Unicode character for "minus" sign (-) */
}
</style>
<style>
.content {
  padding: 0 18px;
  background-color: white;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease-out;
}
</style>
<style>
.grid-container-element { 
    display: grid; 
    grid-template-columns: 1fr 1fr; 
    grid-gap: 20px; 
    width: 80%; 
} 
.grid-child-element { 
    margin: 10px; 
    border: 1px solid red; 
}
</style>

<script>
var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {
  coll[i].addEventListener("click", function() {
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.maxHeight){
      content.style.maxHeight = null;
    } else {
      content.style.maxHeight = content.scrollHeight + "px";
    }
  });
}
</script>
    '''
    return html


def normalize_newlines(txt: str) -> str:
    return txt.replace('\r\n', '\n').replace('\r', '\n')


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


def summarize_failed_test(test_name: str, expected_output: str, actual_output: str) -> Summary:
    return Summary(
        title=f"{test_name} - Failed!",
        expected=expected_output,
        actual=actual_output
    )


def summarize_failed_test_due_to_exception(test_name: str, expected_output: str,
                                           exception: str) -> Summary:
    return Summary(
        title=f"{test_name} - Failed due to an error in the tester!",
        expected=expected_output,
        error=exception,
    )


def summarize_failed_to_check_for_leaks(test_name: str, exception: str) -> Summary:
    return Summary(
        title=f'{test_name} has leaks!{NORMAL_HTML_NEWLINE}Failed due to an error raised by {LEAKS_CHECKER_NAME}!',
        error=exception
    )


def execute_test(command: str, relative_workdir: str, name: str, expected_output: str,
                 output_path: str,
                 results: list[TestResult]) -> None:
    try:
        with subprocess.Popen(command, shell=True, cwd=getcwd()) as proc:
            try:
                proc.communicate(timeout=TIMEOUT)
            except subprocess.TimeoutExpired as e:
                proc.kill()
                results.append({
                    'name': name,
                    'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                                      str(e.stderr) if e.stderr else e.stdout),
                    'passed': False,
                    'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
                })
                return
    except subprocess.CalledProcessError as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              e.stderr if e.stderr else e.stdout),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return
    except subprocess.TimeoutExpired as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              str(e.stderr) if e.stderr else e.stdout),
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

    # norm path makes sure the path is formatted correctly
    with open(normpath(output_path), "r", encoding='utf-8') as file:
        actual_output = normalize_newlines(file.read())

    if actual_output == expected_output:
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
            'summary': summarize_failed_to_check_for_leaks(name, e.stderr if e.stderr else e.stdout),
            'passed': False,
            'command': f'export TESTER_TMP_PWD=$(pwd) && cd {relative_workdir} && {command} && cd $TESTER_TMP_PWD && unset TESTER_TMP_PWD'
        })
        return
    except subprocess.TimeoutExpired as e:
        results.append({
            'name': f'{name} - {LEAKS_CHECKER_NAME}',
            'summary': summarize_failed_to_check_for_leaks(name, str(e.stderr) if e.stderr else e.stdout),
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


def run_test(executable_path: str, relative_workdir: str, test: TestCase, templates: TestTemplates,
             results: list[TestResult]) -> None:
    for key, key_type in get_type_hints(TestCase).items():
        # If key is missing and None is not a valid type for said key
        if key not in test and not isinstance(None, key_type.__args__):
            name = test.get("name", "<missing>")
            results.append({
                'name': name,
                'summary': Summary(
                    title=f"\nTest \"{name}\": \"{key}\" missing from test object\n"),
                'passed': False
            })
            return

    args: str = templates[test[TEMPLATE_NAME]]
    for param_name, param_value in test[PARAMS].items():
        args = args.replace(f':::{param_name}:::', param_value)

    name: str = test[TEST_NAME]
    expected_output_path = test[EXPECTED_OUTPUT_FILE]

    # norm path makes sure the path is formatted correctly
    with open(normpath(expected_output_path), "r", encoding='utf-8') as file:
        expected_output = normalize_newlines(file.read())

    output_path = test[OUTPUT_FILE]
    test_command: str = f'{executable_path} {args}'
    execute_test(test_command, relative_workdir, name, expected_output, output_path, results)
    if test.get("run_leaks") is not False:
        command_without_err_pipes: str = remove_error_pipes_from_command(test_command)
        leaks_check_command: str = f'{LEAKS_CHECKER_COMMAND} {command_without_err_pipes}'
        execute_memory_leaks_test(leaks_check_command, relative_workdir, name, results)


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


def create_html_report(html: str) -> None:
    try:
        with open('test_results.html', "w", encoding='utf-8') as file:
            file.write(html)
    except Exception as e:
        print('Could not create html report. Report content:')
        print(html)
        raise e


def main():
    # Expect 3 args: script name, executable path, json path
    if len(sys.argv) != EXPECTED_ARGS_AMOUNT:
        print(
            f"Bad Usage of local tester, make sure executable path and json test file's path are passed properly." +
            f" Total args passed: {len(sys.argv)}"
        )
        return

    initial_workdir = getcwd()

    # norm path makes sure the path is formatted correctly
    executable = normpath(join(initial_workdir, sys.argv[EXECUTABLE_INDEX]))
    tests_file_path = normpath(join(initial_workdir, sys.argv[TESTS_JSON_FILE_INDEX]))

    workdir = dirname(tests_file_path)
    relative_workdir = dirname(sys.argv[TESTS_JSON_FILE_INDEX])
    chdir(workdir)

    tests_data: TestFile = get_tests_data_from_json(tests_file_path)
    results: list[TestResult] = []

    print("Running tests, please wait", end="")
    for test in tests_data['tests']:
        run_test(executable, relative_workdir, test, tests_data['templates'], results)
        # Printing a dot after each test to make user aware of progress
        print(".", end="")

    # Print new line to avoid console starting on same line as dots
    print("\n", end="")

    amount_failed = 0
    for t in results:
        if t.get('passed', False) is False:
            amount_failed += 1

    html = generate_summary_html_content(results, amount_failed)
    chdir(initial_workdir)
    create_html_report(html)


if __name__ == "__main__":
    main()

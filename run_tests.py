import sys
from os import environ, getcwd, chdir
from os.path import dirname, join, normpath
import subprocess
import json
from typing import TypedDict, TypeAlias

TestTemplates: TypeAlias = dict[str, str]
TestParams: TypeAlias = dict[str, str]


class TestCase(TypedDict):
    name: str
    template: str
    params: TestParams
    output_file: str
    expected_output_file: str


class TestFile(TypedDict):
    templates: TestTemplates
    tests: list[TestCase]


class TestResult(TypedDict):
    name: str
    summary: str
    passed: bool
    command: str | None


# Define constants
STDOUT = 0
STDERR = 1

EXECUTABLE_INDEX = 1
TESTS_JSON_FILE_INDEX = 2
EXPECTED_ARGS_AMOUNT = 3

TEST_NAME = 'name'
TEMPLATE_NAME = 'template'
PARAMS = 'params'
OUTPUT_FILE = 'output_file'
EXPECTED_OUTPUT_FILE = 'expected_output_file'

TIMEOUT = int(environ.get('LOCAL_GRADESCOPE_TIMEOUT', '1'))  # 1 second
VALGRIND_TIMEOUT = int(environ.get('LOCAL_GRADESCOPE_VALGRIND_TIMEOUT', '2'))  # 2 seconds


def format_test_string_for_html(field: str) -> str:
    newline = '\n'
    less_than = '<'
    greater_than = '>'
    return field.replace(less_than, '&lt;').replace(greater_than, '&gt;').replace(newline, '<br/>')


def generate_summary_html_content(results: list[TestResult]) -> str:

    html = '''
<!DOCTYPE html>
<html>
<head>

</head>
<body>


    '''
    for result in results:
        command_element: str = f"<p>Test Command:<br/>{format_test_string_for_html(result['command'])}</p>" \
            if result.get('command', None) else ''
        html += f'''
        <button type="button" class="collapsible" style="color:{'green' if result['passed'] else 'red'}">{result['name']}</button>
<div class="content">
  {command_element}
  <p>{format_test_string_for_html(result['summary'])}</p>
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


def summarize_failed_test(test_name: str, expected_output: str, actual_output: str) -> str:
    return f"\n{test_name} - Failed!\nExpected Output:\n\n{expected_output}\nActual Output:\n\n{actual_output}\n"


def summarize_failed_test_due_to_exception(test_name: str, expected_output: str,
                                           exception: str) -> str:
    return f"{test_name} - Failed due to an error in the tester!\nExpected Output:\n{expected_output}\nError:\n{exception}\n"


def summarize_failed_valgrind(test_name: str, exception: str) -> str:
    return f'\n{test_name} has leaks!\n Failed due to an error raised by valgrind!\nError:\n{exception}\n'


def execute_test(command: str, name: str, expected_output: str, output_path: str,
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
                    'command': command
                })
                return
    except subprocess.CalledProcessError as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              e.stderr if e.stderr else e.stdout),
            'passed': False,
            'command': command
        })
        return
    except subprocess.TimeoutExpired as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output,
                                                              str(e.stderr) if e.stderr else e.stdout),
            'passed': False,
            'command': command
        })
        return
    except Exception as e:
        results.append({
            'name': name,
            'summary': summarize_failed_test_due_to_exception(name, expected_output, str(e)),
            'passed': False,
            'command': command
        })
        return

    # norm path makes sure the path is formatted correctly
    with open(normpath(output_path), "r", encoding='utf-8') as file:
        actual_output = normalize_newlines(file.read())

    if actual_output == expected_output:
        results.append({
            'name': name,
            'summary': f"\n{name} - Passed!\n",
            'passed': True
        })
    else:
        results.append({
            'name': name,
            'summary': summarize_failed_test(name, expected_output, actual_output),
            'passed': False,
            'command': command
        })


def execute_valgrind_test(command: str, name: str, results: list[TestResult]) -> None:
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True,
                                cwd=getcwd())
        try:
            result = proc.communicate(timeout=VALGRIND_TIMEOUT)[STDERR]
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
            'name': f'{name} - Valgrind',
            'summary': summarize_failed_valgrind(name, e.stderr if e.stderr else e.stdout),
            'passed': False,
            'command': command
        })
        return
    except subprocess.TimeoutExpired as e:
        results.append({
            'name': f'{name} - Valgrind',
            'summary': summarize_failed_valgrind(name, str(e.stderr) if e.stderr else e.stdout),
            'passed': False,
            'command': command
        })
        return
    except Exception as e:
        results.append({
            'name': f'{name} - Valgrind',
            'summary': summarize_failed_valgrind(name, str(e)),
            'passed': False,
            'command': command
        })

        return

    if 'no leaks are possible' in actual_output:
        results.append({
            'name': f'{name} - Valgrind',
            'summary': f"\n{name} - no Leaks!\n",
            'passed': True
        })
        return
    else:
        results.append({
            'name': f'{name} - Valgrind',
            'summary': summarize_failed_valgrind(name, actual_output),
            'passed': False,
            'command': command
        })


def run_test(executable_path: str, test: TestCase, templates: TestTemplates,
             results: list[TestResult]) -> None:
    for key in TestCase.__annotations__:
        if key not in test:
            name = test.get("name", "<missing>")
            results.append({
                'name': name,
                'summary': f"\nTest \"{name}\": \"{key}\" missing from test object\n",
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
    valgrind_command: str = f'valgrind --leak-check=full {executable_path} {args}'
    execute_test(test_command, name, expected_output, output_path, results)
    execute_valgrind_test(valgrind_command, name, results)


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
    chdir(workdir)

    tests_data: TestFile = get_tests_data_from_json(tests_file_path)
    results: list[TestResult] = []

    print("Running tests, please wait", end="")
    for test in tests_data['tests']:
        run_test(executable, test, tests_data['templates'], results)
        # Printing a dot after each test to make user aware of progress
        print(".", end="")

    # Print new line to avoid console starting on same line as dots
    print("\n", end="")

    html = generate_summary_html_content(results)
    chdir(initial_workdir)
    create_html_report(html)


if __name__ == "__main__":
    main()

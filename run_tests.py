import sys
from os import environ, path, getcwd
import subprocess
import json
from colorama import init, Fore, ansi

# Initialize colorama for cross-platform terminal coloring
init()

# Define constants
STDOUT = 0
STDERR = 1

TESTS_JSON_FILE_NAME = "uri_testim.json"
TESTS_FOLDER_INDEX = 1
EXPECTED_ARGS_AMOUNT = 2
TEMPLATES = 'templates'
EXECUTABLE = 'executable'

TEST_NAME = 'name'
TEMPLATE_NAME = 'template'
PARAMS = 'params'
OUTPUT_FILE = 'output_file'
EXPECTED_OUTPUT_FILE = 'expected_output_file'

TESTS_KEYS = (
    TEST_NAME,
    TEMPLATE_NAME,
    PARAMS,
    OUTPUT_FILE,
    EXPECTED_OUTPUT_FILE
)

TIMEOUT = int(environ.get('LOCAL_GRADESCOPE_TIMEOUT', '1'))  # 1 second
VALGRIND_TIMEOUT = int(environ.get('LOCAL_GRADESCOPE_VALGRIND_TIMEOUT', '2'))  # 2 seconds


def normalize_newlines(txt: str) -> str:
    return txt.replace('\r\n', '\n').replace('\r', '\n')


def print_divider() -> None:
    print(
        f"\n{Fore.CYAN}------------------------------------------------------------{Fore.RESET}\n")


def print_colored_text(color: ansi.AnsiFore | str, text: str, before_text: str,
                       after_text: str) -> None:
    print(
        f"{before_text}{color}{text}{Fore.RESET}{after_text}"
    )


def print_tests_summary(failed_count: int) -> None:
    print_divider()
    if failed_count == 0:
        print_colored_text(Fore.GREEN, "All Tests Passed! ", "\n", "\n")
    else:
        text = f"{failed_count} {'Test' if failed_count == 1 else 'Tests'} Failed!"
        print_colored_text(Fore.RED, text, "", "\n\n")


def print_failed_test(test_name: str, expected_output: str, actual_output: str) -> None:
    print_colored_text(Fore.RED, f"{test_name} - Failed!", "\n", "\n")
    print_colored_text(Fore.BLUE, "Expected Output:", "", "\n")
    print(f"{expected_output}\n")
    print_colored_text(Fore.BLUE, "Actual Output:", "", "\n")
    print(f"{actual_output}\n")


def print_failed_test_due_to_exception(test_name: str, expected_output: str,
                                       exception: str) -> None:
    print_colored_text(Fore.RED, f"{test_name} - Failed due to an error in the tester!", "\n", "\n")
    print_colored_text(Fore.BLUE, "Expected Output:", "", "\n")
    print(f"{expected_output}\n")
    print_colored_text(Fore.BLUE, "Error:", "", "\n")
    print(f"{exception}\n")


def print_failed_valgrind(test_name: str, exception: str) -> None:
    print_colored_text(Fore.RED, f"{test_name} - Failed due to an error raised by valgrind!", "\n", "\n")
    print_colored_text(Fore.BLUE, "Error:", "", "\n")
    print(f"{exception}\n")


def execute_test(executable_path: str, args: str, name: str, expected_output: str) -> bool:
    try:
        with subprocess.Popen(f'{executable_path} {args}', shell=True, cwd=getcwd()) as proc:
            try:
                proc.communicate(timeout=TIMEOUT)
            except subprocess.TimeoutExpired as e:
                proc.kill()
                print_failed_test_due_to_exception(name, expected_output,
                                                   str(e.stderr) if e.stderr else e.stdout)
                return False
    except subprocess.CalledProcessError as e:
        print_failed_test_due_to_exception(name, expected_output,
                                           e.stderr if e.stderr else e.stdout)
        return False
    except subprocess.TimeoutExpired as e:
        print_failed_test_due_to_exception(name, expected_output,
                                           str(e.stderr) if e.stderr else e.stdout)
        return False
    except Exception as e:
        print_failed_test_due_to_exception(name, expected_output, str(e))
        return False

    return True


def execute_valgrind_test(command: str, name: str) -> bool:
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
        print_failed_valgrind(name, e.stderr if e.stderr else e.stdout)
        return False
    except subprocess.TimeoutExpired as e:
        print_failed_valgrind(name, str(e.stderr) if e.stderr else e.stdout)
        return False
    except Exception as e:
        print_failed_valgrind(name, str(e))
        return False

    if 'no leaks are possible' in actual_output:
        print_colored_text(Fore.GREEN, f"{name} - no Leaks! ", "\n", "\n")
        return True
    else:
        print_colored_text(Fore.RED, f"{name} - has leaks!", "\n", "\n")
        print_failed_valgrind(name, actual_output)
        return False


def run_test(executable_path: str, test: dict[str, str | dict[str, str]],
             templates: dict[str, str]) -> bool:
    print_divider()
    for key in TESTS_KEYS:
        if key not in test:
            name = test.get("name", "<missing>")
            print_colored_text(Fore.RED, f"Test \"{name}\": {key} missing from test object", "\n",
                               "\n")
            return False

    args = templates[test[TEMPLATE_NAME]]
    for param_name, param_value in test[PARAMS].items():
        args = args.replace(f':::{param_name}:::', param_value)

    name = test[TEST_NAME]
    expected_output_path = test[EXPECTED_OUTPUT_FILE]

    with open(expected_output_path, "r", encoding='utf-8') as file:
        expected_output = normalize_newlines(file.read())

    test_success = execute_test(executable_path, args, name, expected_output)
    if test_success:
        output_path = test[OUTPUT_FILE]

        with open(output_path, "r", encoding='utf-8') as file:
            actual_output = normalize_newlines(file.read())

        if actual_output == expected_output:
            print_colored_text(Fore.GREEN, f"{name} - Passed! ", "\n", "\n")
            test_success = True
        else:
            print_failed_test(name, expected_output, actual_output)
            test_success = False

    valgrind_command = f'valgrind --leak-check=full {executable_path} {args}'
    valgrind_success = execute_valgrind_test(valgrind_command, name)
    return valgrind_success and test_success


def get_all_tests_from_json(workdir: str) -> list[dict[str, str]] | None:
    tests_file_path = path.join(workdir, TESTS_JSON_FILE_NAME)
    try:
        with open(tests_file_path, "r", encoding='utf-8') as file:
            json_data = json.load(file)
            return json_data["tests"]
    except (IOError, json.JSONDecodeError) as e:
        print_colored_text(Fore.RED, f"Error reading JSON file: {e}", "", "")
        return None
    except Exception as e:
        print_colored_text(Fore.RED, f"Unexpected error reading JSON file: {e}", "", "")
        return None


def get_all_templates_from_json(workdir: str) -> dict[str, str] | None:
    tests_file_path = path.join(workdir, TESTS_JSON_FILE_NAME)
    try:
        with open(tests_file_path, "r", encoding='utf-8') as file:
            json_data = json.load(file)
            return json_data[TEMPLATES]
    except (IOError, json.JSONDecodeError) as e:
        print_colored_text(Fore.RED, f"Error reading JSON file: {e}", "", "")
        return None
    except Exception as e:
        print_colored_text(Fore.RED, f"Unexpected error reading JSON file: {e}", "", "")
        return None


def get_exec_from_json(workdir: str) -> str | None:
    tests_file_path = path.join(workdir, TESTS_JSON_FILE_NAME)
    try:
        with open(tests_file_path, "r", encoding='utf-8') as file:
            json_data = json.load(file)
            return json_data[EXECUTABLE]
    except (IOError, json.JSONDecodeError) as e:
        print_colored_text(Fore.RED, f"Error reading JSON file: {e}", "", "")
        return None
    except Exception as e:
        print_colored_text(Fore.RED, f"Unexpected error reading JSON file: {e}", "", "")
        return None


def main():
    # Expect 2 args: script name, workdir, executable path
    if len(sys.argv) != EXPECTED_ARGS_AMOUNT:
        print(
            f"Bad Usage of local tester, make sure test folder's name are passed properly." +
            f" Total args passed: {len(sys.argv)}"
        )
        return

    failed_count = 0
    workdir = sys.argv[TESTS_FOLDER_INDEX]
    tests = get_all_tests_from_json(workdir)
    templates = get_all_templates_from_json(workdir)
    executable = get_exec_from_json(workdir)
    if tests is None:
        return

    for test in tests:
        if not run_test(executable, test, templates):
            failed_count += 1

    print_tests_summary(failed_count)


if __name__ == "__main__":
    main()

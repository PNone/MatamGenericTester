import sys
if sys.version_info < (3, 10):
    sys.exit("Python %s.%s or later is required.\n" % (3, 10))
else:
    from typing import TypedDict, TypeAlias, List

TestTemplates: TypeAlias = dict[str, str]
TestParams: TypeAlias = dict[str, str]

class TestParamRange(TypedDict):
    first: int
    last: int


class TestCase(TypedDict):
    name: str
    template: str
    params: TestParams
    output_file: str
    expected_output_file: str
    expected_output_is_substring: bool | None
    run_leaks: bool | None
    params_range: TestParamRange | List[str] | None


class TestFile(TypedDict):
    templates: TestTemplates
    tests: list[TestCase]


class Summary(TypedDict):
    title: str
    actual: str | None
    expected: str | None
    error: str | None
    diff_html: str | None


class TestResult(TypedDict):
    name: str
    summary: Summary
    passed: bool
    command: str | None


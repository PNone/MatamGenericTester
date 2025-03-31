from utils.config import NORMAL_HTML_NEWLINE, HTML_COLORED_NEWLINE, HTML_COLORED_WHITESPACE
from utils.matam_types import Summary, TestResult
from os import getcwd, chdir


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

def create_html_report(html: str, html_name: str) -> None:
    try:
        with open(html_name, "w", encoding='utf-8') as file:
            file.write(html)
    except Exception as e:
        print('Could not create html report. Report content:')
        print(html)
        raise e


def create_html_report_from_results(results: list[TestResult], initial_workdir: str, html_name: str) -> None:
    amount_failed: int = 0
    for t in results:
        if t.get('passed', False) is False:
            amount_failed += 1

    html: str = generate_summary_html_content(results, amount_failed)
    curr_workdir: str = getcwd()
    chdir(initial_workdir)
    create_html_report(html, html_name)
    chdir(curr_workdir)
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Button, Static, Label
from typing import List, Dict

class TestButton(Button):
    def __init__(self, name: str, passed: bool, id: str, is_valgrind: bool = False):
        status = "passed" if passed else "failed"
        classes = f"{status} {'valgrind' if is_valgrind else 'main'}"
        super().__init__(name, id=f"button_{id}", classes=classes)

class ResultDetails(Static):
    def __init__(self, summary: str):
        super().__init__(summary, id="result_details")
        self.visible = False

class TestReportApp(App):
    CSS_PATH = "styles.css"
    def __init__(self, results: List[Dict]):
        super().__init__()
        self.results = results

        if results:
            first_test = results[0]
            self.selected_summary = Static(first_test['summary'].strip(), id="result_details")
        else:
            self.selected_summary = Static("No test results available.", id="result_details")

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="test_list"):
                for i in range(0, len(self.results), 2):
                    yield TestButton(self.results[i]['name'], self.results[i]['passed'], f"test{i+1}")
                    yield TestButton(self.results[i+1]['name'], self.results[i+1]['passed'], f"test{i+2}", is_valgrind=True)
            yield self.selected_summary
        yield Label("Press Ctrl + C to exit", id="exit_label")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id.split('_')[1]
        index = int(button_id.replace('test', '')) - 1
        selected_result = self.results[index]
        self.selected_summary.update(selected_result['summary'].strip())
        self.selected_summary.visible = True
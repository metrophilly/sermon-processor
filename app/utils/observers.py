# app/utils/observers.py
class PipelineObserver:
    def __init__(self):
        self.logs = []

    def log(self, step_name, data):
        """
        Log the state of the data after each step.

        Args:
            step_name (str): Name of the executed step.
            data (PipelineData): The updated pipeline data.
        """
        self.logs.append(f"Step: {step_name}, Data: {data}")
        print(f"LOG: Step '{step_name}' completed. Data state: {data}")

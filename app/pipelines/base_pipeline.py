class PipelineStep:
    """
    Base class for a pipeline step. Each step must implement the `process` method.
    """

    def process(self, data):
        """
        Execute the step's logic.

        Args:
            data (dict): Shared pipeline data passed between steps.

        Returns:
            dict: Updated data.
        """
        raise NotImplementedError("Subclasses must implement the `process` method.")


class Pipeline:
    """
    A generic pipeline that executes a series of steps in order.
    """

    def __init__(self):
        self.steps = []

    def add_step(self, step):
        """
        Add a step to the pipeline.

        Args:
            step (PipelineStep): The step to add.

        Returns:
            Pipeline: The current pipeline (for method chaining).
        """
        if not isinstance(step, PipelineStep):
            raise TypeError("Step must inherit from PipelineStep")
        self.steps.append(step)
        return self

    def execute(self, data):
        """
        Execute all steps in the pipeline sequentially.

        Args:
            data (dict): Shared pipeline data.

        Returns:
            dict: Final data after all steps are executed.
        """
        for step in self.steps:
            data = step.process(data)
        return data

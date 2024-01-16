# Sermon Processor Project Setup

This guide will walk you through setting up a Python environment for the
sermon-processor project on macOS.

## Prerequisites

Before you start, make sure you have Python 3 and the Audacity app installed on
your system. You can check your Python version by running:

```bash
python3 --version
```

## Create a Virtual Environment

To create an isolated environment for the sermon-processor project, follow these
steps:

1. **Navigate to your project directory:**

```bash
cd path/to/your/sermon-processor
```

2. **Create the virtual environment:**

```bash
python3 -m venv sermon-processor-env
```

This command will create a new directory named `sermon-processor-env` in your
project directory containing the virtual environment.

## Activate the Virtual Environment

Before installing any packages, you need to activate the virtual environment.
You can do this by running:

```bash
source sermon-processor-env/bin/activate
```

Your prompt will change to indicate that you are now in a virtual environment.

## Install Required Packages

With the virtual environment activated, install the required packages using
`pip`:

```bash
pip install moviepy yt-dlp
```

These packages will only be available within this virtual environment and are
required for the sermon-processor project.

## Running the Project

After installing the required packages, you can run the project's Python script:

```bash
python process.py
```

Follow the prompts to input the YouTube URL and timestamps for audio processing.
Once the automated processing in complete, follow the steps of the resulting
helper text file to make final scrub edits in Audacity, export the file as a
.mp3, and hand it off to be uploaded and distributed.

## Deactivating the Virtual Environment

Once you are finished with your session, you can deactivate the virtual
environment by running:

```bash
deactivate
```

This will return you to the system's default Python interpreter.

## Additional Notes

- To manage different Python versions, consider using `pyenv`.
- For any additional project-specific instructions, update this section
  accordingly.

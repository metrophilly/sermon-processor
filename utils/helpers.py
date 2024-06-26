import subprocess


def run_command(command, capture_output=False):
    """Run a command and optionally capture its output."""
    print(f"Executing command: {' '.join(command)}")
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    output = ""
    while True:
        line = process.stdout.readline()
        if line == "" and process.poll() is not None:
            break
        if line:
            print(line.strip())
            if capture_output:
                output += line

    exit_code = process.poll()
    if exit_code != 0:
        raise Exception(
            f"Command {' '.join(command)} failed with exit code {exit_code}"
        )
    print("Command executed successfully.")
    return output if capture_output else None


# Function to print error messages in red
def print_error(message):
    print("\033[91m{}\033[0m".format(message))


# Function to print success messages in green
def print_success(message):
    print("\033[92m{}\033[0m".format(message))


# Function to print info messages in orange
def print_info(message):
    print("\033[93m{}\033[0m".format(message))

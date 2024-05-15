from utils.helpers import print_error, print_info


def confirmation_printout(upload_date):
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    print(
        f"""{GREEN}
    ===================
    🎛️ SERMON PROCESSOR
    ===================

    Your file has been processed and saved to {YELLOW}./data/{upload_date}/{upload_date}_ready_to_scrub.mp3{GREEN}.

    Please follow the manual finishing touches:

    1. Open the audio file in Audacity or a similar tool.
    2. Trim excess silence between clips, aiming for 1.5-second gaps (focus on the
      intro, scripture passage, and the sermon).
    3. Smooth out any rough transitions or "bumps" where clips are stitched
      together.
    4. Trim the pastor's final prayer at the end, while keeping Rhea's outro intact.
    5. Export the edited audio as an MP3 file named "yyyy-mm-dd.mp3".
    6. Send to the reviewer.

    Remember: Careful editing ensures a polished final product, and your attention to
    detail will enhance our listeners' experience. Thank you for your contribution!
    {RESET}"""
    )


def confirm_parameters(parameters: dict):
    """
    Ask the user to confirm the parameters before proceeding.

    Args:
        parameters (dict): A dictionary of parameter names and their values to confirm.

    Example:
    parameters = {
        "URL": "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "Start Time": "00:00:10",
        "End Time": "00:01:00",
        "Preacher": "John Doe",
        "Series": "Understanding Faith"
    }


    Exits the script if the user does not confirm.
    """
    print_info("Please confirm if these are the correct parameters:")
    for key, value in parameters.items():
        print_info(f"{key}: {value}")

    response = input(
        "\033[93m{}\033[0m".format("Continue with these parameters? [y/N]: ")
    )
    if response.strip().lower() != "y":
        print_error("Operation aborted by the user.")
        exit(0)

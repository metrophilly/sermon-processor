def confirmation_printout(upload_date):
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"

    print(
        f"""{GREEN}
    ===================
    🎛️ SERMON PROCESSOR
    ===================

    Your file has been processed and saved to {YELLOW}./data/{upload_date}_ready_to_scrub.mp3{GREEN}.

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


def confirm_parameters(youtube_url, start_time, end_time):
    """Ask the user to confirm the parameters before proceeding."""
    print("Please confirm if these are the correct parameters:")
    print(f"URL: {youtube_url}")
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    response = input("Continue with these parameters? [y/N]: ")
    if response.strip().lower() != "y":
        print("Operation aborted by the user.")
        exit(0)

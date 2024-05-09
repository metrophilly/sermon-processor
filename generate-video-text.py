import html
import os
import json
import re
import httpx  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
from dotenv import load_dotenv  # type: ignore

from utils.file import (
    create_and_change_directory,
    ensure_dir_exists,
)
from utils.config import (
    parse_video_description_parameters,
)
from utils.constants import TEMPLATE_DIR
from utils.helpers import print_error, print_info, print_success
from utils.media import get_video_upload_date
from utils.format_helper import format_passage_ref
from utils.studylight_api_helper import format_passage_ref_for_studylight
from utils.time import get_formatted_date
from utils.ui import confirm_parameters


def fetch_passage_via_studylight(formatted_passage: str) -> object:
    """
    Fetches Bible passage data from StudyLight API.

    Args:
      formatted_passage (str): The formatted passage to fetch.

    Returns:
      object: The fetched data.

    Raises:
      ValueError: If AUTH_ID or AUTH_CODE environment variables are not set.
    """
    load_dotenv()

    auth_id = os.getenv("STUDYLIGHT_AUTH_ID")
    auth_code = os.getenv("STUDYLIGHT_AUTH_CODE")

    if not auth_id or not auth_code:
        raise ValueError("AUTH_ID and AUTH_CODE environment variables must be set.")

    url = f"https://beta.studylight.org/sandbox/bible_verse.cgi?auth-id={auth_id}&auth-code={auth_code}&lang=eng&instructions=no&vsrefs=no&trans=n84&passage={formatted_passage}"

    response = httpx.get(url)
    if response.status_code == 200:
        data = response.json()
    else:
        print("Failed to fetch data")

    return data


def extract_and_format_text_from_studylight_html(json_data) -> str:
    """
    Extracts and formats text from HTML content embedded within JSON or dict data,
    ensuring that all text is processed by removing undesired HTML tags like <p>, <br>,
    and heading tags (<h1>, <h2>, <h3>, etc.). Processes the text line by line to maintain
    narrative flow as per each original line in the HTML, and prepends each line with
    5 white spaces.

    Args:
        json_data (str or dict): JSON string or dict containing the HTML content.

    Returns:
        str: The cleaned, extracted text content, formatted to maintain narrative flow
        with each line beginning with 5 white spaces.
    """
    if isinstance(json_data, dict):
        data = json_data
    else:
        data = json.loads(json_data)

    html_content = data["text"]
    html_content = re.sub(r"<h[1-6].*?>.*?</h[1-6]>", "", html_content, flags=re.DOTALL)
    html_content = re.sub(
        r"<p[^>]*>|<br\s*/?>", "\n", html_content, flags=re.IGNORECASE
    )
    html_content = re.sub(r"</p>|<span[^>]*>|</span>", "", html_content)

    lines = html_content.split("\n")
    formatted_text = []

    for line in lines:
        line = html.unescape(line).strip()
        if line:  # Ensure the line is not just whitespace
            formatted_text.append("     " + line)

    full_text = "\n".join(formatted_text)
    return full_text


def generate_title_from_template(
    title,
    passage_ref,
    preacher,
    template_path,
    output_path,
):
    """
    Appends multiple pieces of text to a given template and writes the result to a file.

    Args:
    title (str): The title of the sermon
    passage_ref (str): Reference text of the passage.
    preacher (str): The preacher of the sermon.
    template_path (str): Path to the template file.
    output_path (str): Path to the output file where the result will be saved.
    """
    with open(template_path, "r", encoding="utf-8") as file:
        template_content = file.read()

    template_content = template_content.replace("{{TITLE_REPLACE}}", title)
    template_content = template_content.replace("{{PASSAGE_REF_REPLACE}}", passage_ref)
    template_content = template_content.replace("{{PREACHER_REPLACE}}", preacher)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(template_content)


def generate_description_from_template(
    passage_ref_text,
    passage_text,
    series_text,
    air_date_text,
    template_path,
    output_path,
):
    """
    Appends multiple pieces of text to a given template and writes the result to a file.

    Args:
    passage_ref_text (str): Reference text of the passage.
    passage_text (str): The scripture text to append.
    series_text (str): The series title.
    air_date_text (str): The air date.
    template_path (str): Path to the template file.
    output_path (str): Path to the output file where the result will be saved.
    """
    with open(template_path, "r", encoding="utf-8") as file:
        template_content = file.read()

    template_content = template_content.replace(
        "{{PASSAGE_REF_REPLACE}}", passage_ref_text
    )
    template_content = template_content.replace(
        "{{PASSAGE_TEXT_REPLACE}}", passage_text
    )
    template_content = template_content.replace("{{SERIES_REPLACE}}", series_text)
    template_content = template_content.replace("{{AIR_DATE_REPLACE}}", air_date_text)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(template_content)


def main() -> None:
    print_info("Generating YouTube video title and description...")

    load_dotenv()
    ensure_dir_exists("data")

    youtube_url, title, preacher, passage, series = parse_video_description_parameters()

    confirm_parameters(
        {
            "Title": title,
            "Preacher": preacher,
            "Passage": passage,
            "Series": series,
        }
    )

    try:
        upload_date = get_video_upload_date(youtube_url)
        output_dir = create_and_change_directory(upload_date)
        title_output_path = os.path.join(output_dir, f"generated_title.txt")
        description_output_path = os.path.join(output_dir, f"generated_description.txt")

        studylight_passage_ref = format_passage_ref_for_studylight(passage)
        json_data = fetch_passage_via_studylight(studylight_passage_ref)
        passage_text = extract_and_format_text_from_studylight_html(json_data)
        formatted_passage_ref_for_description = format_passage_ref(passage)
        formatted_date = get_formatted_date(upload_date)

        title_template_path = os.path.join(TEMPLATE_DIR, "video_title.txt")
        generate_title_from_template(
            title,
            passage,
            preacher,
            title_template_path,
            title_output_path,
        )
        print_success(
            f"Success: Video title generated at ./data/{upload_date}/generated_title.txt."
        )

        description_template_path = os.path.join(TEMPLATE_DIR, "video_description.txt")
        generate_description_from_template(
            formatted_passage_ref_for_description,
            passage_text,
            series,
            formatted_date,
            description_template_path,
            description_output_path,
        )
        print_success(
            f"Success: Video description generated at ./data/{upload_date}/generated_description.txt."
        )

    except ValueError as ve:
        print_error(f"Value error: {ve}")
    except Exception as e:
        print_error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

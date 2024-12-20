def test_test():
    assert "hello" == "hello"


# def test_video_download():
#     # Example: Verify if the video download script runs successfully
#     result = subprocess.run(
#         ["python3", "process-video.py"],
#         stdout=subprocess.PIPE,
#         stderr=subprocess.PIPE
#     )
#     assert result.returncode == 0, f"Error: {result.stderr.decode()}"

# def test_output_file():
#     # Example: Check if output file is created
#     assert os.path.exists("output.mp4"), "Output file not found!"
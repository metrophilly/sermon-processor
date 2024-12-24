import os


def main():
    # print("running scripts/run_audio_video_pipeline.py")
    # os.system("python3 scripts/run_audio_video_pipeline.py")

    print("running scripts/run_audio_pipeline.py")
    os.system("python3 scripts/run_audio_pipeline.py")

    # choice = input("Choose script ( [a]udio / [v]ideo ): ").strip().lower()
    # if choice == "v" or choice == "video":
    #     os.system("python3 process-video.py")
    # elif choice == "a" or choice == "audio":
    #     os.system("python3 process-audio.py")
    # else:
    #     print("Not a valid choice. Exiting.")
    #     exit(1)


if __name__ == "__main__":
    main()

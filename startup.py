import os


def main():
    choice = input("Choose script ( [a]udio / [v]ideo / [b]oth ): ").strip().lower()
    if choice == "v" or choice == "video":
        os.system("python3 scripts/run_video_pipeline.py")
    if choice == "a" or choice == "audio":
        os.system("python3 scripts/run_audio_pipeline.py")
    elif choice == "b" or choice == "both":
        os.system("python3 scripts/run_audio_pipeline.py")
        os.system("python3 scripts/run_video_pipeline.py")

    else:
        print("Not a valid choice. Exiting.")
        exit(1)


if __name__ == "__main__":
    main()

import os


def main():
    choice = (
        input("Choose script ( [a]udio / [v]ideo / [d]escription ): ").strip().lower()
    )
    if choice == "v" or choice == "video":
        os.system("python3 process-video.py")
        os.system("python3 generate-video-text.py")
    elif choice == "a" or choice == "audio":
        os.system("python3 process-audio.py")
    elif choice == "d" or choice == "description":
        os.system("python3 generate-video-text.py")
    else:
        print("Not a valid choice. Exiting.")
        exit(1)


if __name__ == "__main__":
    main()

import os

def main():
    choice = input("Choose processing type ([a]udio/[v]ideo): ").strip().lower()
    if choice == 'v' or choice == 'video':
        os.system("python3 process-video.py")
    elif choice == 'a' or choice == 'audio':
        os.system("python3 process-audio.py")
    else:
        print("Not a valid choice. Exiting.")
        exit(1)

if __name__ == "__main__":
    main()

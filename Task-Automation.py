import os
import shutil
import logging
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import hashlib
import json
import schedule
import time

def setup_logging():
    logging.basicConfig(
        filename="file_organizer.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def load_custom_extensions():
    if os.path.exists("file_types.json"):
        with open("file_types.json", "r") as f:
            return json.load(f)
    else:
        return {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xls", ".xlsx"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov"],
            "Audio": [".mp3", ".wav", ".aac"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Others": []
        }

def save_custom_extensions(file_types):
    with open("file_types.json", "w") as f:
        json.dump(file_types, f, indent=4)

def organize_files(directory, file_types):
    if not os.path.exists(directory):
        logging.error("Directory does not exist: %s", directory)
        print("Error: Directory does not exist.")
        return

    # Create folders for each file type
    for folder in file_types.keys():
        folder_path = os.path.join(directory, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            logging.info("Created folder: %s", folder_path)

    # Organize files
    for file in os.listdir(directory):
        file_path = os.path.join(directory, file)

        # Skip directories
        if os.path.isdir(file_path):
            continue

        # Identify the file type and move it
        file_ext = os.path.splitext(file)[1].lower()
        destination_folder = "Others"

        for folder, extensions in file_types.items():
            if file_ext in extensions:
                destination_folder = folder
                break

        dest_path = os.path.join(directory, destination_folder, file)
        try:
            shutil.move(file_path, dest_path)
            logging.info("Moved file: %s -> %s", file_path, dest_path)
        except Exception as e:
            logging.error("Failed to move file: %s. Error: %s", file_path, e)

    print("Files organized successfully!")
    logging.info("File organization completed successfully.")

    # Save the state for undo functionality
    with open("undo_state.json", "w") as undo_file:
        json.dump({"directory": directory, "file_types": file_types}, undo_file)

def undo_last_organization():
    if not os.path.exists("undo_state.json"):
        print("No previous organization to undo.")
        return

    with open("undo_state.json", "r") as undo_file:
        state = json.load(undo_file)

    directory = state["directory"]
    file_types = state["file_types"]

    for folder, extensions in file_types.items():
        folder_path = os.path.join(directory, folder)
        if not os.path.exists(folder_path):
            continue

        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            dest_path = os.path.join(directory, file)
            try:
                shutil.move(file_path, dest_path)
                logging.info("Moved file back: %s -> %s", file_path, dest_path)
            except Exception as e:
                logging.error("Failed to move file back: %s. Error: %s", file_path, e)

        # Remove the now-empty folder
        if len(os.listdir(folder_path)) == 0:
            os.rmdir(folder_path)
            logging.info("Removed folder: %s", folder_path)

    os.remove("undo_state.json")
    print("Undo completed successfully!")
    logging.info("Undo operation completed successfully.")

def find_duplicates(directory):
    file_hashes = {}
    duplicates = []

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            with open(file_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
                if file_hash in file_hashes:
                    duplicates.append((file_path, file_hashes[file_hash]))
                else:
                    file_hashes[file_hash] = file_path

    if duplicates:
        print("Duplicate files found:")
        for dup, original in duplicates:
            print(f"Duplicate: {dup} -> Original: {original}")
    else:
        print("No duplicates found.")
    return duplicates

def clean_temp_files(directory):
    temp_extensions = [".tmp", ".log", ".bak", ".old"]
    for root, _, files in os.walk(directory):
        for file in files:
            if os.path.splitext(file)[1].lower() in temp_extensions:
                file_path = os.path.join(root, file)
                try:
                    os.remove(file_path)
                    logging.info("Removed temp file: %s", file_path)
                except Exception as e:
                    logging.error("Failed to remove temp file: %s. Error: %s", file_path, e)

def remove_empty_folders(directory):
    for root, dirs, _ in os.walk(directory, topdown=False):
        for dir in dirs:
            folder_path = os.path.join(root, dir)
            if not os.listdir(folder_path):
                os.rmdir(folder_path)
                logging.info("Removed empty folder: %s", folder_path)

def generate_disk_space_report(directory):
    report_path = os.path.join(directory, "disk_space_report.txt")
    with open(report_path, "w") as report:
        report.write(f"Disk Space Report - {datetime.now()}\n")
        report.write("=" * 50 + "\n")
        total_size = 0

        for folder in os.listdir(directory):
            folder_path = os.path.join(directory, folder)
            if os.path.isdir(folder_path):
                folder_size = sum(
                    os.path.getsize(os.path.join(root, file))
                    for root, _, files in os.walk(folder_path)
                    for file in files
                )
                total_size += folder_size
                report.write(f"Folder: {folder} - {folder_size / (1024 ** 2):.2f} MB\n")

        report.write(f"\nTotal Size: {total_size / (1024 ** 2):.2f} MB\n")
    print(f"Disk space report generated: {report_path}")
    logging.info("Disk space report generated at: %s", report_path)

def schedule_maintenance(directory):
    def task():
        file_types = load_custom_extensions()
        organize_files(directory, file_types)
        clean_temp_files(directory)
        remove_empty_folders(directory)
        generate_disk_space_report(directory)
        logging.info("Scheduled maintenance completed.")

    schedule.every().day.at("02:00").do(task)
    print("Scheduled maintenance set for 2:00 AM daily.")

    while True:
        schedule.run_pending()
        time.sleep(1)

def choose_directory():
    root = tk.Tk()
    root.withdraw()
    directory = filedialog.askdirectory(title="Select Directory to Organize")
    return directory

def main():
    setup_logging()
    print("Welcome to the  File Organizer!")

    root = tk.Tk()
    root.withdraw()

    while True:
        action = messagebox.askquestion(
            "Choose Action",
            "What would you like to do?\n\n1. Organize Files\n2. Undo Last Organization\n3. Remove Duplicates\n4. Clean Temp Files\n5. Generate Disk Space Report\n6. Exit",
        )

        if action == "yes":
            directory = choose_directory()
            if directory:
                file_types = load_custom_extensions()
                organize_files(directory, file_types)
                generate_disk_space_report(directory)
            else:
                print("No directory selected.")
        elif action == "no":
            undo_last_organization()
        elif action == "cancel":
            clean_temp_files(directory)
            remove_empty_folders(directory)
            generate_disk_space_report(directory)
        else:
            break

if __name__ == "__main__":
    main()

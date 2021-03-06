"""
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import os, shutil, random, json, argparse, logging

# Default values
user_path = os.path.expanduser('~')
input_directory = os.path.abspath('.')
destination_dir = os.path.join(user_path, 'Podcasts', 'Phone')
save_dir = os.path.join(user_path, '.cache', 'rdmfileselector')
quantity = 5
max_score = 30
max_files = 100
savefile = 'cache.json'

def load_args():
    """ Parse and load arguments
    """
    global input_directory
    global destination_dir
    global quantity
    global save_dir
    global max_files

    # Initializer
    parser = argparse.ArgumentParser(description="Picks files randomly.")
    # Argument definition
    # optional
    parser.add_argument("-q", "--quantity", type=int, help="how many files to pick from the input directory.")
    parser.add_argument("-i", "--input", help="where to select the files from.")
    parser.add_argument("-v", "--verbose", help="make the application more verbose.", action="store_true")
    parser.add_argument("-c", "--cache", help="use a different directory for the cache file.")
    parser.add_argument("-o", "--condition", type=int, help="only proceed if there are less files in the dir than the chosen parameter.")
    # positional
    parser.add_argument("destination", help="where to put the randomly picked files.")
    args = parser.parse_args()

    # Loads arguments
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: [%(funcName)s] %(message)s")
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s:  [%(funcName)s] %(message)s")

    if args.quantity is not None:
        quantity = args.quantity

    if args.input.startswith('~', 0, 1):
        input_directory = os.path.expanduser(args.input)
    elif args.input is not None:
        input_directory = os.path.abspath(args.input)

    if args.destination.startswith('~', 0, 1):
        destination_dir = os.path.expanduser(args.destination)
    elif args.destination is not None:
        destination_dir = os.path.abspath(args.destination)

    if args.cache is not None:
        save_dir = os.path.expanduser(args.cache)
    
    if args.condition is not None:
        max_files = args.condition

    logging.debug(f"Quantity: {quantity}")
    logging.debug(f"Input: {input_directory}")
    logging.debug(f"Destination: {destination_dir}")

def save_data(directories):
    """ Save directory data.
    """
    if not os.path.isdir(save_dir):
        os.mkdir(save_dir)

    with open(os.path.join(save_dir, savefile), 'w') as file:
        file.write(json.dumps(directories))

    logging.info("Save successful!")

def load_data():
    """ Load saved data.
    """
    if os.path.isfile(os.path.join(save_dir, savefile)):
        logging.info("Savedata found!")
        with open(os.path.join(save_dir, savefile), 'r') as cacheFile:
            directories = json.load(cacheFile)

        return directories

    logging.info("No savedata found...")
    return []

def copy_files(files):
    """ Copy a list of files.
    """
    for item in files:
        logging.info(f"Copying {item} to {destination_dir}")
        filepath = os.path.join(input_directory, item)
        shutil.copy(filepath, destination_dir)

def up_scores(directory):
    """ Should be called every run to increase all scores by one.
    """
    for directory_file in directory['files']:
        if directory_file['score'] != max_score:
            directory_file['score'] += 1
            logging.debug(f"Increased the score of: {directory_file['filename']} to {directory_file['score']}")

    return directory

def lower_scores(files, directory):
    """ Lower to 0 the score of files that were picked.
    """
    for item in files:
        for directory_file in directory['files']:
            if item == directory_file['filename']:
                logging.debug(f"Lowered the score of: {directory_file['filename']} to 0.")
                directory_file['score'] = 0
                break

    return directory

def scan_score(directory):
    """ Shuffle the file list and pick the highest scores for files.
    """
    files = directory['files']
    random.shuffle(files)
    picked_files = []
    count = 0
    isDone = False
    prefer_score = max_score

    if quantity > len(files):
        logging.info(f"Directory does not have more than {quantity} files. Less files will be picked.")

    while not isDone:
        logging.debug(f"Preffered score is now {prefer_score}")
        for item in files:
            if item['score'] == prefer_score:
                logging.debug(f"Picked: {item['filename']}, with score: {item['score']}")
                picked_files.append(item['filename'])
                count += 1
            if count == quantity:
                logging.debug("Hit quantity limit.")
                isDone = True
                break
        if prefer_score == 0 and not isDone:
            logging.debug("Unable to hit quantity limit.")
            isDone = True
        elif prefer_score != 0 and not isDone:
            prefer_score = prefer_score - 1
        else:
            isDone = True

    return picked_files

def find_dir(directory_name, directories):
    """ Find a directory by name inside a list of directories and return a tuple with index and True/False
    """
    for i, item in enumerate(directories):
        if item['directory_name'] == directory_name:
            logging.debug(f"Directory: {directory_name} found at index {i}")
            return (True, i)

    return (False, -1)

def dir_is_updated(previous_directory):
    """ Check if the directory is unchanged.
    """
    previous_file_number = previous_directory['file_quantity']
    current_file_number = len(os.listdir(input_directory))
    if previous_file_number == current_file_number:
        logging.debug("Directory is up to date!")
        return True

    logging.debug("Directory is not up to date.")
    return False

def update_dir(directory, directories):
    """ Update a directory's entry in the directories.
    """
    logging.info(f"Directory: {directory['directory_name']} has been changed. Updating...")
    isFound, index = find_dir(directory['directory_name'], directories)
    files = os.listdir(input_directory)
    if isFound:
        if len(files) > directory['file_quantity']:
            for item in files:
                fileIsUpToDate = False
                for directory_file in directory['files']:
                    if item == directory_file['filename']:
                        fileIsUpToDate = True
                        break
                if not fileIsUpToDate:
                    logging.debug(f"New file found: `{item}`, Adding it with default score.")
                    directory['files'].append({ "filename": item, "score": max_score })
        else:
            deletedFiles = []
            for directory_file in directory['files']:
                fileHasBeenDeleted = True
                for item in files:
                    if directory_file['filename'] == item:
                        fileHasBeenDeleted = False
                        break
                if fileHasBeenDeleted:
                    deletedFiles.append(directory_file)

            for removed_file in deletedFiles:
                logging.debug(f"File not found: `{removed_file['filename']}`, Removing entry.")
                directory['files'].remove(removed_file)

        directory['file_quantity'] = len(directory['files'])
        directories[index] = directory
        logging.debug(f"Updated directory {directory['directory_name']} in cache.")

    return directories

def add_dir(directory, directories):
    """ Add a directory to the directories.
    """
    logging.debug(f"Adding directory: {directory['directory_name']}")
    directories.append(directory)

    return directories

def scan_dir():
    """ Scan a directory if it hasn't been scanned before.
    """
    logging.info(f"Directory: {input_directory} has not yet been scanned.")
    files = os.listdir(input_directory)
    aggregated = []
    logging.info("Scanning destination directory...")
    logging.info(f"Found {len(files)} files.")

    for item in files:
        aggregated.append({ "filename": item, "score": max_score })
        logging.debug(f"File: {item}, score: {max_score}")

    directory = {
        "directory_name": input_directory,
        "file_quantity": len(aggregated),
        "files": aggregated
    }

    return directory

def excess_files_in_dir():
    files = os.listdir(destination_dir)
    logging.debug(f"Destination has {len(files)} files. Limit is {max_files} files.")

    if len(files) < max_files:
        return False

    return True

def main():
    load_args()

    if excess_files_in_dir():
        print("Destination directory has too many files, aborting.")
    else:
        directories = load_data()
        isFound, index = find_dir(input_directory, directories)
        if isFound:
            directory = directories[index]
            up_scores(directory)
            if not dir_is_updated(directory):
                directories = update_dir(directory, directories)
        else:
            directory = scan_dir()
            directories = add_dir(directory, directories)

        if quantity > 0:
            picked_files = scan_score(directory)
            directory = lower_scores(picked_files, directory)
            copy_files(picked_files)
        else:
            # A quantity of less than 0 means that no files will be picked and only directory scans/updates will be done.
            print("Nothing to do.")

        save_data(directories)

if __name__ == "__main__":
    main()

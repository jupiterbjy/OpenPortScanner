from os import path, listdir


# Not sure dumping all results in SharedData is a good idea or not.
def save_rename_conflicting(data: str, directory: str, file_name: str, extension=''):
    # only for text mode

    # make sure dir end with slash, and normalize it.
    if not directory.endswith(('/', '\\')):
        directory = path.abspath(directory + '/')

    new_file_name = file_name + '_0'

    while True:
        try:
            with open(directory + new_file_name + extension, 'xt') as f:
                f.write(data)
                print(f"File saved at {directory + new_file_name + extension}")
        except FileExistsError:
            # file exists

            similar_files = [i for i in listdir(directory) if i.startswith(file_name)]
            exists = [i.split('_')[-1].split('.')[0] for i in similar_files]

            new_file_name = file_name + '_' + str(max(map(int, exists)) + 1)
        else:
            break

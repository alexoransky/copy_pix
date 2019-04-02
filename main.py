import os
import sys
import pathlib
import time
import hashlib

PRINT_SKIPPED = False

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


class PicFile:
    def __init__(self, name, src, dest):
        self.name = name
        self.src = pathlib.Path(src)
        self.dest = pathlib.Path(dest)
        self.copied = False
        self.error = False
        self.verified = False

    def is_same(self):
        src_path = self.src / self.name
        dest_path = self.dest / self.name

        if not os.path.isfile(src_path):
            return False

        if not os.path.isfile(dest_path):
            return False

        src_md5 = md5(src_path)
        dest_md5 = md5(dest_path)
        if PRINT_SKIPPED:
            if dest_md5 == src_md5:
                print("{} : File already exists and is the same. Skipped.".format(self.name))

        return dest_md5 == src_md5

    def _copy_file(self, src_path, dest_path, verify):
        try:
            fi = open(src_path, "rb")
        except:
            print("Cannot open file: {}".format(src_path))
            self.error = True
            return False

        try:
            fo = open(dest_path, "wb")
        except:
            print("Cannot open file: {}".format(dest_path))
            fi.close()
            self.error = True
            return False

        try:
            data = fi.read()
            fo.write(data)
        except:
            print("Cannot copy file.".format(self.name))
            fi.close()
            fo.close()
            try:
                os.remove(dest_path)
            except:
                print("Exception deleting file: {}".format(dest_path))

            self.error = True
            return False

        self.copied = True

        if verify:
            src_md5 = md5(src_path)
            dest_md5 = md5(dest_path)
            self.error = (dest_md5 != src_md5)

        print("Copied: {} to {}".format(src_path, dest_path))

        return True

    def copy(self, delete_existing=False, verify=True):
        print("{} : ".format(self.name), end="")

        src_path = self.src / self.name
        dest_path = self.dest / self.name

        if not os.path.isfile(src_path):
            print("Not a file: {}".format(src_path))
            self.error = True
            return False

        # check if the dest file exists
        if os.path.isfile(dest_path):
            # size = os.stat(dest_path).st_size
            size = os.path.getsize(dest_path)
            if size == 0:
                print("Dest file is of 0 size: {}. ".format(dest_path), end="")
            else:
                print("File already exists but is NOT the same: {}. ".format(dest_path), end="")

            # delete the file if exists
            if delete_existing or (size == 0):
                try:
                    os.remove(dest_path)
                except FileNotFoundError:
                    print("File deleted: {}.".format(dest_path))
                    pass
                except:
                    print("Cannot delete file: {}.".format(dest_path))
                    self.error = True
                    return False
            else:
                print("Skipped.")
                return False

        # copy file
        return self._copy_file(src_path, dest_path, verify)


def copy_files(src, dest):
    if not os.path.isdir(src):
        print("Not a folder: {} . Exiting.".format(src))
        return 0

    os.makedirs(dest, exist_ok=True)
    if not os.path.isdir(dest):
        print("Not a folder: {} . Exiting.".format(dest))
        return 0

    print("Copying files from {} to {}".format(src, dest))

    # get all JPG and CR2 files from the source folder
    file_list = []
    for f in os.listdir(src):
        if f.lower().endswith(".jpg") or f.lower().endswith(".cr2"):
            pf = PicFile(f, src, dest)
            file_list.append(pf)

    total_cnt = len(file_list)
    print("Found {} files in the source folder...".format(total_cnt))
    if total_cnt == 0:
        return 0

    print("Checking if files are the same... ", end="")
    files_to_copy = []
    cnt = 0
    for f in file_list:
        cnt += 1
        if not f.is_same():
            files_to_copy.append(f)

        if cnt % 10 == 0:
            print("\rChecking if files are the same... {}%".format(round(cnt*100/total_cnt, 1)), end="")

    print()

    if cnt > 0:
        print("Found {} identical files.".format(cnt))

    to_copy_cnt = len(files_to_copy)
    print("Found {} files to copy...".format(to_copy_cnt))
    if to_copy_cnt == 0:
        print("No need to copy files. All files are the same.")
        return 0

    # sort files to copy by name
    files_to_copy.sort(key=lambda f: f.name)
    to_copy_cnt = len(files_to_copy)

    cnt = 0
    copied_cnt = 0
    error_cnt = 0
    for f in files_to_copy:
        cnt += 1
        f.copy(verify=True)

        if f.copied:
            copied_cnt += 1

        if f.error:
            error_cnt += 1

        if cnt % 10 == 0:
            print("Progress: {} / {} files : {}%  Copied: {} Errors: {}".format(cnt, to_copy_cnt, round(cnt*100/to_copy_cnt, 1), copied_cnt, error_cnt), flush=True)

    print("Copied {} files.".format(copied_cnt))

    files_not_copied = [f for f in files_to_copy if (f.error and not f.copied)]
    if len(files_not_copied) > 0:
        print("Files not copied due to errors:")
        for f in files_not_copied:
            print(f.name)

    files_copied = [f for f in files_to_copy if (f.error and f.copied)]
    if len(files_copied) > 0:
        print("Files copied with errors:")
        for f in files_copied:
            print(f.name)

    print("Statistics:")
    print("Total files in the source folder: {}".format(total_cnt))
    print("Copied files: {}".format(copied_cnt))
    print("Could not copy: {}".format(error_cnt))

    return total_cnt


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: copy_pix <source folder> <destination folder>")
        print("copy_pix will try to copy all .JPG and .CR2 files.")
        sys.exit(1)

    t1 = time.time()

    total_cnt = copy_files(sys.argv[1], sys.argv[2])

    t2 = time.time()
    delta_t = round(t2-t1, 1)

    if total_cnt > 0:
        print("Elapsed time: {} sec: {} sec per file.".format(delta_t, round(delta_t/total_cnt, 3)))
    else:
        print("Elapsed time: {} sec.".format(delta_t))

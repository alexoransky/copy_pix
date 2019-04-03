import os
import sys
import pathlib
import hashlib
import tqdm

DELETE_DEST = False
VERIFY_COPY = True
EXT_TO_COPY = [".cr2", ".jpg"]

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
        self.same_dest_exists = False
        self.diff_dest_exists = False

    def identical(self):
        src_path = self.src / self.name
        dest_path = self.dest / self.name

        if not os.path.isfile(src_path):
            return False

        if not os.path.isfile(dest_path):
            return False

        src_md5 = md5(src_path)
        dest_md5 = md5(dest_path)

        return dest_md5 == src_md5

    def copy_file(self, src_path, dest_path):
        try:
            fi = open(src_path, "rb")
        except:
            self.error = True
            return False

        try:
            fo = open(dest_path, "wb")
        except:
            fi.close()
            self.error = True
            return False

        try:
            data = fi.read()
            fo.write(data)
        except:
            fi.close()
            fo.close()
            try:
                os.remove(dest_path)
            except:
                pass

            self.error = True
            return False

        self.copied = True
        return True

    def copy(self):
        src_path = self.src / self.name
        dest_path = self.dest / self.name

        if not os.path.isfile(src_path):
            self.error = True
            return False

        # check if the dest file exists
        if os.path.isfile(dest_path):
            if self.identical():
                self.same_dest_exists = True
                return False

            # delete the file if exists
            if DELETE_DEST:
                try:
                    os.remove(dest_path)
                except FileNotFoundError:
                    pass
                except:
                    self.error = True
                    return False
            else:
                self.diff_dest_exists = True
                return False

        # copy file
        self.copy_file(src_path, dest_path)

        if VERIFY_COPY:
            src_md5 = md5(src_path)
            dest_md5 = md5(dest_path)
            self.error = (dest_md5 != src_md5)

        return self.copied


def list_files(files):
    for f in files:
        yield f


def copy_files(src, dest):
    if not os.path.isdir(src):
        print("Not a folder: {} . Exiting.".format(src))
        return 0

    os.makedirs(dest, exist_ok=True)
    if not os.path.isdir(dest):
        print("Not a folder: {} . Exiting.".format(dest))
        return 0

    print("Copying files from {} to {}".format(src, dest), flush=True)

    # get all JPG and CR2 files from the source folder
    file_list = []
    for f in os.listdir(src):
        fn, fext = os.path.splitext(f)
        if fext.lower() in EXT_TO_COPY:
            pf = PicFile(f, src, dest)
            file_list.append(pf)

    total_cnt = len(file_list)
    if total_cnt == 0:
        print("No files to copy found in the source folder.")
        return 0

    # sort the file list by name
    file_list.sort(key=lambda f: f.name)

    # print("Checking if files are the same... ", end="")
    copied_cnt = 0
    error_cnt = 0
    same_dest_cnt = 0
    diff_dest_cnt = 0

    pbar = tqdm.tqdm(total=total_cnt, unit="file", mininterval=1.0, ascii=True)

    for f in file_list:
        pbar.set_postfix_str(f.name.lower(), refresh=False)
        f.copy()
        pbar.update()

        if f.same_dest_exists:
            same_dest_cnt += 1

        if f.diff_dest_exists:
            diff_dest_cnt += 1

        if f.copied:
            copied_cnt += 1

        if f.error:
            error_cnt += 1

    pbar.close()

    print("", flush=True)

    files_not_copied = [f for f in file_list if (f.error and not f.copied)]
    not_copied_cnt = len(files_not_copied)
    if not_copied_cnt > 0:
        print("Files not copied due to errors:")
        for f in files_not_copied:
            print(f.name)

    files_copied_err = [f for f in file_list if (f.error and f.copied)]
    copied_err_cnt = len(files_copied_err)
    if copied_err_cnt > 0:
        print("Files copied with errors:")
        for f in files_copied_err:
            print(f.name)

    diff_files = [f for f in file_list if (f.diff_dest_exists)]
    diff_files_cnt = len(diff_files)
    if diff_files_cnt > 0:
        print("Files not copied because a different file already existed:")
        for f in diff_files:
            print(f.name)

    print("Statistics:")
    print("Total files found in the source folder: {}".format(total_cnt))
    print("Copied files: {}".format(copied_cnt))
    print("Skipped copying because files are the same: {}".format(same_dest_cnt))
    print("Skipped copying because files are different: {}".format(diff_dest_cnt))
    print("Total errors: {}".format(error_cnt))
    print("    Files not copied due to read/access errors: {}".format(not_copied_cnt))
    print("    Files copied with errors: {}".format(copied_err_cnt))

    return total_cnt


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: copy_pix <source folder> <destination folder>")
        print("copy_pix will try to copy all .JPG and .CR2 files.")
        sys.exit(1)

    copy_files(sys.argv[1], sys.argv[2])

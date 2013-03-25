#!/usr/bin/env python

import ftplib, getpass, os, sys

def upload(repo_path, host, user, remote_path):

    ftp = ftplib.FTP(host)
    ftp.login(user, getpass.getpass())
    ftp.cwd("/")
    
    path = ""
    for piece in remote_path.split("/"):
        if not piece:
            continue
        path += "/" + piece
        if piece not in ftp.nlst():
            print "Creating remote directory:", path
            ftp.mkd(piece)

        print "Entering remote directory:", path
        ftp.cwd(piece)
    
    upload_files(remote_path, repo_path, ftp)
    ftp.quit()

def upload_files(remote_path, path, ftp):

    for child in os.listdir(path):
    
        child_path = os.path.join(path, child)

        if os.path.isfile(child_path):
            f = open(child_path, "rb")
            ftp.storbinary("STOR " + child, f)
            f.close()

        elif os.path.isdir(child_path):
            if child not in ftp.nlst():
                print "Creating remote directory:", remote_path+"/"+child
                ftp.mkd(child)

            print "Entering remote directory:", remote_path+"/"+child
            ftp.cwd(child)
            upload_files(remote_path+"/"+child, child_path, ftp)
            ftp.cwd("..")


if __name__ == "__main__":

    if len(sys.argv) != 5:
        sys.stderr.write("Usage: %s <repository path> <FTP server> <user name> <remote path>\n" % sys.argv[0])
        sys.exit(1)

    repo_path, host, user, remote_path = sys.argv[1:]

    try:
        upload(repo_path, host, user, remote_path)
    except ftplib.Error:
        sys.stderr.write("FTP transfer failed.\n")
        sys.exit(1)
    
    sys.exit()

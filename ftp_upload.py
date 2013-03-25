#!/usr/bin/env python

import ftplib, getpass, os, stat, sys

def upload(repo_path, host, user, remote_path, force = False):

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
    
    upload_files(remote_path, repo_path, ftp, check_size = not force)
    ftp.quit()

def upload_files(remote_path, path, ftp, check_size = False):

    remote_files = set(ftp.nlst())
    
    for child in os.listdir(path):
    
        child_path = os.path.join(path, child)

        if os.path.isfile(child_path):
        
            copy = True
            local_size = os.stat(child_path)[stat.ST_SIZE]

            if check_size and child in remote_files:
            
                ftp.sendcmd("TYPE I")
                remote_size = ftp.size(child)
                ftp.sendcmd("TYPE A")
                
                if local_size == remote_size:
                    copy = False
            
            if copy:
                f = open(child_path, "rb")
                ftp.storbinary("STOR " + child, f)
                f.close()

        elif os.path.isdir(child_path):
            if child not in ftp.nlst():
                print "Creating remote directory:", remote_path+"/"+child
                ftp.mkd(child)

            print "Entering remote directory:", remote_path+"/"+child
            ftp.cwd(child)
            upload_files(remote_path+"/"+child, child_path, ftp, check_size = check_size)
            ftp.cwd("..")


if __name__ == "__main__":

    args = sys.argv[:]
    force = "-f" in args
    if force:
        args.remove("-f")
    
    if len(args) != 5:
        sys.stderr.write("Usage: %s <repository path> <FTP server> <user name> <remote path>\n" % args)
        sys.exit(1)

    repo_path, host, user, remote_path = args[1:]

    try:
        upload(repo_path, host, user, remote_path, force = force)
    except ftplib.Error:
        sys.stderr.write("FTP transfer failed.\n")
        raise
        sys.exit(1)
    
    sys.exit()

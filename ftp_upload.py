#!/usr/bin/env python

# Copyright (C) 2013 met.no
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

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
        
            # Always copy Release*, Packages* and Sources* files.
            copy = True
            
            if child.startswith("Release"):
                copy = True
            
            elif child.startswith("Packages"):
                copy = True
            
            elif child.startswith("Sources"):
                copy = True
            
            elif check_size and child in remote_files:
            
                # Copy files if required to, or if the remote size differs
                # from the local size. Ideally, we should also compare the
                # file hashes.
                local_size = os.stat(child_path)[stat.ST_SIZE]
                
                ftp.sendcmd("TYPE I")
                remote_size = ftp.size(child)
                ftp.sendcmd("TYPE A")
                
                if local_size == remote_size:
                    copy = False
            
            if copy:
                print "Copying", child_path
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
        sys.stderr.write("Usage: %s <repository path> <FTP server> <user name> <remote path>\n" % args[0])
        sys.exit(1)

    repo_path, host, user, remote_path = args[1:]

    try:
        upload(repo_path, host, user, remote_path, force = force)
    except ftplib.Error:
        sys.stderr.write("FTP transfer failed.\n")
        raise
        sys.exit(1)
    
    sys.exit()

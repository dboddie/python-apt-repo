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

def delete(host, user, remote_path):

    ftp = ftplib.FTP(host)
    ftp.login(user, getpass.getpass())
    ftp.cwd("/")
    
    path = ""
    for piece in remote_path.split("/"):
        if not piece:
            continue
        path += "/" + piece
        if piece not in ftp.nlst():
            sys.stderr.write("Failed to enter remote directory: %s\n" % path)
            sys.exit(1)

        print "Entering remote directory:", path
        ftp.cwd(piece)
    
    delete_files(path, ftp)
    ftp.quit()

def delete_files(path, ftp):

    remote_files = set(ftp.nlst())
    
    for child in remote_files:
    
        try:
            print "Deleting", path + "/" + child
            ftp.delete(child)

        except ftplib.error_perm:
        
            ftp.cwd(child)
            delete_files(path + "/" + child, ftp)
            ftp.cwd("..")
            
            ftp.rmd(child)


if __name__ == "__main__":

    args = sys.argv[:]
    
    if len(args) != 4:
        sys.stderr.write("Usage: %s <FTP server> <user name> <remote path>\n" % args[0])
        sys.exit(1)

    host, user, remote_path = args[1:]

    try:
        delete(host, user, remote_path)
    except ftplib.Error:
        sys.stderr.write("FTP operation failed.\n")
        raise
        sys.exit(1)
    
    sys.exit()

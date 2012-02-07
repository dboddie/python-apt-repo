#!/usr/bin/env python

import bz2, gzip, glob, os, stat, subprocess, sys, time

suite_Release_headings = [
    "Architectures", "Codename", "Components", "Date", "Label", "Origin",
    "Suite", "Description"
    ]

arch_Release_headings = [
    "Archive", "Component", "Label", "Origin", "Architecture", "Description"
    ]

details = {"Architectures": ["amd64", "i386", "source"],
           "Codename": "lucid",
           "Suite": "lucid",
           "Components": ["experimental"],
           "Date": time.strftime("%a, %d %b %Y %H:%M:%S %Z"),
           "Label": "met.no",
           "Origin": "met.no",
           "Description": "Experimental Debian and Ubuntu packages for the Norwegian Meteorological Institute"}

hashes = [("MD5Sum", "md5sum"), ("SHA1", "sha1sum"), ("SHA256", "sha256sum")]
checksums = {"Files": "md5sum", "Checksums-Sha1": "sha1sum", "Checksums-Sha256": "sha256sum"}

Packages_compression = [("gz", gzip.GzipFile), ("bz2", bz2.BZ2File)]
Sources_compression = [("gz", gzip.GzipFile), ("bz2", bz2.BZ2File)]

def chdir(path):

    print "Entering", path
    os.chdir(path)

def mkdir(path):

    print "Creating", path
    os.mkdir(path)

def create_tree(levels, parent_path):

    if not levels:
        return
    
    subdirs = levels[0]
    
    if isinstance(subdirs, str):
        subdirs = [subdirs]
    
    for subdir in subdirs:
        child_path = os.path.join(parent_path, subdir)
        mkdir(child_path)
        create_tree(levels[1:], child_path)

def create_repo(path):

    architectures = []
    for arch in details["Architectures"]:
        if arch != "source":
            arch = "binary-" + arch
        architectures.append(arch)
    
    if not os.path.exists(path):
        mkdir(path)
    
    create_tree([details["Label"], "dists", details["Suite"], details["Components"],
                 architectures], path)

def catalogue_packages(path, root_path, component, architecture):

    Packages_path = os.path.join(path, "Packages")
    Packages_file = open(Packages_path, "w")
    packages = glob.glob(os.path.join(path, "*", "*"+os.extsep+"deb"))
    
    for package in packages:
    
        s = subprocess.Popen(["dpkg-deb", "-I", package, "control"], stdout=subprocess.PIPE)
        info = s.stdout.read()
        Packages_file.write(info)
        
        pieces = package.split(os.sep)
        Packages_file.write("Filename: " + os.sep.join(pieces[-6:]) + "\n")
        
        size = os.stat(package)[stat.ST_SIZE]
        Packages_file.write("Size: %i\n" % size)
        
        for name, command in hashes:
        
            s = subprocess.Popen([command, package], stdout=subprocess.PIPE)
            result = s.stdout.read().strip().split()[0]
            Packages_file.write(name + ": " + result + "\n")
        
        Packages_file.write("\n")
    
    Packages_file.close()
    
    compressed_files = compress_files(Packages_path, Packages_compression)
    
    Release_path = write_component_release(path, component, architecture)
    
    return packages, [Packages_path, Release_path] + compressed_files

def catalogue_sources(path, root_path, component):

    Sources_path = os.path.join(path, "Sources")
    Sources_file = open(Sources_path, "w")
    sources = glob.glob(os.path.join(path, "*", "*"+os.extsep+"dsc"))
    
    for source in sources:
    
        info = read_dsc_file(source)
        if not info:
            continue
        
        Source_line = filter(lambda x: x.startswith("Source: "), info)[0]
        Sources_file.write("Package: " + Source_line[8:])
        
        for line in info:
        
            if line.startswith("Source: "):
                continue
            
            Sources_file.write(line)
            
            if not line.startswith(" ") and ":" in line:
            
                try:
                    command = checksums[line.split(":")[0]]
                except KeyError:
                    continue
                
                s = subprocess.Popen([command, source], stdout=subprocess.PIPE)
                result = s.stdout.read().strip().split()[0]
                size = os.stat(source)[stat.ST_SIZE]
                file_name = os.path.split(source)[1]
                
                Sources_file.write(" %s %i %s\n" % (result, size, file_name))
    
    Sources_file.close()
    
    compressed_files = compress_files(Sources_path, Sources_compression)
    
    Release_path = write_component_release(path, component, "source")
    
    return sources, [Sources_path, Release_path] + compressed_files

def read_dsc_file(path):

    f = open(path)
    first_line = f.readline()
    if first_line.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
    
        f.close()
        s = subprocess.Popen(["gpg", "--decrypt", path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        lines = s.stdout.readlines()
        if s.wait() != 0:
            sys.stderr.write("Problem with file: %s\n" % path)
            for line in s.stderr.readlines():
                sys.stderr.write("  "+line)
    else:
        lines = [first_line] + f.readlines()
    
    return lines

def compress_files(path, compression_types):

    compressed_files = []
    
    for ext, Class in compression_types:
    
        obj = Class(path + os.extsep + ext, "w")
        obj.write(open(path).read())
        obj.close()
        compressed_files.append(path + os.extsep + ext)
    
    return compressed_files

def write_component_release(path, component, architecture):

    Release_path = os.path.join(path, "Release")
    Release_file = open(Release_path, "w")
    
    arch_details = details.copy()
    arch_details["Archive"] = details["Suite"]
    arch_details["Component"] = component
    arch_details["Architecture"] = architecture
    
    for heading in arch_Release_headings:
        Release_file.write(heading + ": " + arch_details[heading] + "\n")
    
    return Release_path

def write_suite_release(files, path):

    Release_file = open(os.path.join(path, "Release"), "w")
    
    for heading in suite_Release_headings:
    
        value = details[heading]
        if not isinstance(value, str):
            value = " ".join(value)
        
        Release_file.write(heading + ": " + value + "\n")
    
    sizes = {}
    for file_path in files:
    
        sizes[file_path] = os.stat(file_path)[stat.ST_SIZE]
    
    max_size = max(sizes.values())
    max_size_length = len(str(max_size))
    
    for name, command in hashes:
    
        Release_file.write(name + ":\n")
        
        for file_path in files:
        
            s = subprocess.Popen([command, file_path], stdout=subprocess.PIPE)
            result = s.stdout.read().strip().split()[0]
            
            padding = "    " + (max_size_length - len(str(sizes[file_path]))) * " "
            pieces = file_path.split(os.sep)
            Release_file.write(" %s%s%i %s\n" % (result, padding, sizes[file_path], os.sep.join(pieces[-3:])))

def update_tree(levels, parent_path, root_path = None, component = None, architecture = None):

    if not levels:
        # In each architecture directory, catalogue all the section subdirectories.
        # In the source directory, catalogue the sources for the section instead.
        if architecture == "source":
            return catalogue_sources(parent_path, root_path, component)
        else:
            return catalogue_packages(parent_path, root_path, component, architecture)
    
    elif len(levels) == 5:
        root_path = levels[0]
    
    subdirs = levels[0]
    
    if isinstance(subdirs, str):
        subdirs = [subdirs]
   
    files = []
    packages = []
    
    for subdir in subdirs:
    
        if len(levels) == 1:
            # In the last level, the subdirectories represent architectures.
            architecture = subdir
            if subdir != "source":
                subdir = "binary-" + subdir
        elif len(levels) == 2:
            # In the penultimate level, the subdirectories represent components.
            component = subdir
        
        child_path = os.path.join(parent_path, subdir)
        new_packages, new_files = update_tree(levels[1:], child_path, root_path, component, architecture)
        packages += new_packages
        files += new_files
    
    if len(levels) == 2:
    
        # When in the suite/distribution directory, write a Release file.
        write_suite_release(files, parent_path)
    
    return packages, files

def update_repo(path):

    # Catalogue the packages themselves.
    update_tree([details["Label"], "dists", details["Suite"], details["Components"],
                 details["Architectures"]], path)

if __name__ == "__main__":

    if len(sys.argv) != 3:
    
        sys.stderr.write("Usage: %s [create|update] <directory containing the repository root>\n" % sys.argv[0])
        sys.exit(1)
    
    command = sys.argv[1]
    path = sys.argv[2]
    
    if command == "create":
        sys.exit(create_repo(path))
    elif command == "update":
        sys.exit(update_repo(path))
    else:
        sys.exit(1)

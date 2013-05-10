#!/usr/bin/env python

# Copyright (C) 2012 met.no
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

import bz2, gzip, glob, os, shutil, stat, subprocess, sys, time

__version__ = "0.1.0"

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

class PackageFile:

    def _read_entry(self, lines):

        previous = None
        info = {}
        headings = []
        kept_lines = []
        
        for line in lines:
        
            # Keep each line for situations where the source text is required.
            kept_lines.append(line)
            
            if not line.strip():
                if info:
                    yield info, headings, kept_lines
                    info = {}
                    headings = []
                    kept_lines = []
                else:
                    continue
            
            elif not line.startswith(" "):
                at = line.find(":")
                heading = line[:at]
                value = line[at+1:].strip()
                if value == "":
                    info[heading] = []
                else:
                    info[heading] = value
                
                previous = heading
                if heading not in headings:
                    headings.append(heading)
            
            elif previous:
                if isinstance(info[previous], list):
                    info[previous].append(line.strip())
                else:
                    info[previous] += line.rstrip()
        
        if info:
            yield info, headings, kept_lines

class Package(PackageFile):

    suffix = ".deb"
    
    def __init__(self, path = None, info = None):
    
        self.path = path
        
        if info:
            self._has_info = True
            self._info = info
        else:
            self._has_info = False
            self._info = {}
        
        if path:
        
            # The file name includes everything in the path from the repository root.
            # dists/<suite>/<component>/<architecture>/<section>/<file name>
            self._info["Filename"] = "/".join(path.split(os.sep)[-6:])
            
            size = os.stat(path)[stat.ST_SIZE]
            self._info["Size"] = size
            
            for name, command in hashes:
            
                s = subprocess.Popen([command, path], stdout=subprocess.PIPE)
                result = s.stdout.read().strip().split()[0]
                self._info[name] = result
        
        self._headings = []
        self.lines = []
    
    def __repr__(self):
    
        self._get_info()
        if self.path:
            return "<Package %s>" % self.path
        else:
            self._get_info()
            return "<Package %s>" % str(self._info)
    
    def __getitem__(self, key):
    
        self._get_info()
        return self._info[key]
    
    def _get_info(self):
    
        if self._has_info:
            return
        
        s = subprocess.Popen(["dpkg-deb", "-I", self.path, "control"], stdout=subprocess.PIPE)
        
        for info, headings, lines in self._read_entry(s.stdout.readlines()):
        
            self._info.update(info)
            self._headings = headings
            self.lines += lines
            self._has_info = True
    
    def architecture(self):
    
        self._get_info()
        return self._info["Architecture"]
    
    def section(self):
    
        self._get_info()
        return self._info["Section"]
    
    def packages_text(self):
    
        self._get_info()
        
        text = "".join(self.lines)
        headings = ("Filename", "Size") + zip(*hashes)[0]
        
        for key in headings:
            text += key + ": " + str(self._info[key]) + "\n"
        
        return text

class Packages(PackageFile):

    def __init__(self, path):
    
        self.path = path
        self.repo_path = os.sep.join(self.path.split(os.sep)[:-5])
        self.packages = {}
        self.lines = []
    
    def add_package(self, package):
    
        self.packages[package["Package"]] = package
    
    def read(self):
    
        self.packages = {}
        self.lines = []
        
        for info, headings, lines in self._read_entry(open(self.path).readlines()):
        
            try:
                file_name = info["Filename"]
            except KeyError:
                if info.has_key("Package"):
                    sys.stderr.write("Failed to find a file name for package: %s\n" % info["Package"])
            
            path = os.path.join(self.repo_path, file_name)
            self.add_package(Package(path = path))
            
            self.lines += lines
    
    def write(self):
    
        Packages_file = open(self.path, "w")
        
        for package in self.packages.values():
            Packages_file.write(package.packages_text() + "\n")
        
        Packages_file.write("\n")
        Packages_file.close()
    
    def find(self, name):
    
        try:
            return self.packages[name]
        except KeyError:
            return None

class Source(PackageFile):

    suffix = ".dsc"
    
    def __init__(self, path):
    
        self.path = path
        self.file_name = os.path.split(path)[1]
        self._has_info = False
        self._info = {}
        self._headings = []
        self.lines = []
    
    def __repr__(self):
    
        self._get_info()
        return "<Source %s %s>" % (self.path, self._info)
    
    def __getitem__(self, key):
    
        self._get_info()
        return self._info[key]
    
    def _get_info(self):
    
        if self._has_info:
            return
        
        f = open(self.path)
        first_line = f.readline()
        if first_line.startswith("-----BEGIN PGP SIGNED MESSAGE-----"):
        
            f.close()
            s = subprocess.Popen(["gpg", "--decrypt", self.path], stdout=subprocess.PIPE,
                                                                  stderr=subprocess.PIPE)
            lines = s.stdout.readlines()
            if s.wait() != 0:
                sys.stderr.write("Problem with file: %s\n" % self.path)
                for line in s.stderr.readlines():
                    sys.stderr.write("  "+line)
        else:
            lines = [first_line] + f.readlines()
        
        for info, headings, lines in self._read_entry(lines):
            self._info = info
            self._headings = headings
            self.lines += lines
            self._has_info = True
    
    def sources_text(self):
    
        self._get_info()
        
        text = ""
        
        for heading in self._headings:
        
            value = self._info[heading]
            
            if heading == "Source":
                heading = "Package"
            
            text += heading + ":"
            
            if isinstance(value, list):
            
                text += "\n"
                for item in value:
                    text += " " + item + "\n"
                
                if heading in checksums:
                
                    try:
                        command = checksums[heading]
                    except KeyError:
                        continue
                    
                    s = subprocess.Popen([command, self.path], stdout=subprocess.PIPE)
                    result = s.stdout.read().strip().split()[0]
                    size = os.stat(self.path)[stat.ST_SIZE]
                    text += " %s %i %s\n" % (result, size, self.file_name)
            else:
                text += " " + value + "\n"
        
        source_dir = os.path.split(os.path.abspath(self.path))[0]
        text += "Directory: " + os.sep.join(source_dir.split(os.sep)[-5:]) + "\n"
        
        return text
    
    def find_section(self, path):
    
        self._get_info()
        
        for binary in self._info["Binary"].split(","):
        
            version = self._info["Version"].split(":")[-1]
            template = binary.strip() + "_" + version + "_*.deb"
            
            search_path = os.path.join(path, "binary-*", "*", template)
            packages = glob.glob(search_path)
            
            if not packages:
                sys.stderr.write("Failed to find packages for binary: %s\n" % binary)
                continue
            
            section_dir_path = os.path.split(packages[0])[0]
            return os.path.split(section_dir_path)[1]
        
        return None
    
    def original_archive_names(self):
    
        self._get_info()
        
        files = map(lambda line: line.split()[-1], self._info["Files"])
        names = []
        
        for name in files:
            if ".orig." in name:
                names.append(name)
        
        return names
    
    def diff_archive_name(self):
    
        self._get_info()
        
        files = map(lambda line: line.split()[-1], self._info["Files"])
        for name in files:
            if ".diff." in name:
                return name
        
        return None

class Sources(PackageFile):

    def __init__(self, path):
    
        self.path = path
        self.repo_path = os.sep.join(self.path.split(os.sep)[:-5])
        self.sources = {}
    
    def add_source(self, source):
    
        self.sources[source["Source"]] = source
    
    def read(self):
    
        self.sources = {}
        self.lines = []
        
        for info, headings, lines in self._read_entry(open(self.path).readlines()):
        
            try:
                dsc = filter(lambda i: i.endswith(".dsc"), info["Files"])[0].split()[-1]
            except (KeyError, IndexError):
                if info.has_key("Package"):
                    sys.stderr.write("Failed to find a dsc file for package: %s\n" % info["Package"])
            
            path = os.path.join(self.repo_path, info["Directory"], dsc)
            self.add_source(Source(path))
            
            self.lines += lines
    
    def write(self):
    
        Sources_file = open(self.path, "w")

        for source in self.sources.values():
            Sources_file.write(source.sources_text() + "\n")
        
        Sources_file.close()
    
    def find(self, name):
    
        try:
            return self.sources[name]
        except KeyError:
            return None


def mkdir(path):

    if not os.path.exists(path):
        print "Creating", path
        os.mkdir(path)

def mkdirs(pieces):

    path = pieces.pop(0)
    mkdir(path)
    
    for piece in pieces:
        path = os.path.join(path, piece)
        mkdir(path)

def copy_file(src_path, dest_path):

    if os.path.exists(dest_path) or os.path.islink(dest_path):
        print "Removing", dest_path
        os.remove(dest_path)
    print "Copying", src_path, "to", dest_path
    shutil.copy2(src_path, dest_path)

def link_file(src_path, dest_path):

    if os.path.exists(dest_path) or os.path.islink(dest_path):
        print "Removing", dest_path
        os.remove(dest_path)
    print "Linking", src_path, "to", dest_path
    os.symlink(os.path.abspath(src_path),
               os.path.abspath(dest_path))

def remove_file(path):

    if os.path.exists(path):
        print "Removing", path
        os.remove(path)

def subdirectories(path):

    for child in os.listdir(path):
        child_path = os.path.join(path, child)
        if os.path.isdir(child_path):
            yield child_path

def find_files(path, FileClass):

    for obj in os.listdir(path):
    
        obj_path = os.path.join(path, obj)
        if os.path.isdir(obj_path):
            for child in find_files(obj_path, FileClass):
                yield child
        elif obj_path.endswith(FileClass.suffix):
            yield FileClass(path = obj_path)

def find_files_from_pattern(pattern, FileClass):

    for obj_path in glob.glob(pattern):
    
        if os.path.isfile(obj_path) and obj_path.endswith(FileClass.suffix):
            yield FileClass(path = obj_path)


def catalogue_packages(path, root_path):

    packages = glob.glob(os.path.join(path, "*", "*.deb"))
    return map(lambda p: Package(path = p), packages)

def write_catalogue_package_file(component, architecture, path, packages):

    Packages_path = os.path.join(path, "Packages")
    Packages_obj = Packages(Packages_path)
    
    for package in packages:
        Packages_obj.add_package(package)
    
    Packages_obj.write()
    compressed_files = compress_files(Packages_path, Packages_compression)
    
    suite = path.split(os.sep)[-3]
    Release_path = write_component_release(path, suite, component, architecture)
    
    return [Packages_path, Release_path] + compressed_files

def catalogue_sources(path, root_path):

    sources = glob.glob(os.path.join(path, "*", "*.dsc"))
    return map(lambda s: Source(s), sources)

def write_catalogue_sources_file(path, root_path, component, sources):

    Sources_path = os.path.join(path, "Sources")
    Sources_obj = Sources(Sources_path)
    
    for source in sources:
        Sources_obj.add_source(source)
    
    Sources_obj.write()
    compressed_files = compress_files(Sources_path, Sources_compression)
    
    suite = path.split(os.sep)[-3]
    Release_path = write_component_release(path, suite, component, "source")
    
    return Sources_obj.sources.values(), [Sources_path, Release_path] + compressed_files, ["source"]

def compress_files(path, compression_types):

    compressed_files = []
    
    for ext, Class in compression_types:
    
        obj = Class(path + "." + ext, "w")
        obj.write(open(path).read())
        obj.close()
        compressed_files.append(path + "." + ext)
    
    return compressed_files

def write_component_release(path, suite, component, architecture):

    Release_path = os.path.join(path, "Release")
    Release_file = open(Release_path, "w")
    
    arch_details = details.copy()
    arch_details["Archive"] = suite
    arch_details["Component"] = component
    arch_details["Architecture"] = architecture
    
    for heading in arch_Release_headings:
        Release_file.write(heading + ": " + arch_details[heading] + "\n")
    
    return Release_path

def write_suite_release(files, path, suite, components, architectures):

    Release_file = open(os.path.join(path, "Release"), "w")
    
    suite_details = details.copy()
    suite_details["Suite"] = suite
    suite_details["Codename"] = suite
    suite_details["Components"] = components
    suite_details["Architectures"] = architectures
    
    for heading in suite_Release_headings:
    
        value = suite_details[heading]
        if not isinstance(value, str):
            value = " ".join(value)
        
        Release_file.write(heading + ": " + value + "\n")
    
    sizes = {}
    for file_path in files:
        sizes[file_path] = os.stat(file_path)[stat.ST_SIZE]
    
    if not sizes:
        return
    
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

# Create repository

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

def create_repo(path, suites, components):

    mkdir(path)
    
    create_tree(["dists", suites, components], path)
    return 0

# Add packages and sources

def add_package(package, path, link = False):

    architecture = package.architecture()
    section = package.section()
    
    dest_dir = os.path.join(path, "binary-" + architecture, section)
    mkdirs([path, "binary-" + architecture, section])
    dest_path = os.path.join(dest_dir, os.path.split(package["Filename"])[1])
    if link:
        link_file(package.path, dest_path)
    else:
        copy_file(package.path, dest_path)

def add_source(source, path, link = False):

    section = source.find_section(path)
    
    if not section:
        sys.stderr.write("Failed to find a binary package for source: %s\n" % source.path)
        return
    
    source_file_missing = False
    
    source_dir_path = os.path.split(source.path)[0]
    orig_names = []
    
    for orig_name in source.original_archive_names():
    
        orig_path = os.path.join(source_dir_path, orig_name)
        
        if os.path.exists(orig_path):
            break
        else:
            orig_names.append(orig_name)
    else:
        sys.stderr.write("Failed to find any original archive: %s\n" % ",".join(orig_names))
        source_file_missing = True
    
    diff_name = source.diff_archive_name()
    
    if diff_name:
        diff_path = os.path.join(source_dir_path, diff_name)
        
        if not os.path.exists(diff_path):
            sys.stderr.write("Failed to find diff archive: %s\n" % diff_path)
            source_file_missing = True
    
    if source_file_missing:
        return
    
    dest_dir = os.path.join(path, "source", section)
    mkdirs([path, "source", section])
    
    # Copy the .dsc file.
    dest_path = os.path.join(dest_dir, source.file_name)
    if link:
        link_file(source.path, dest_path)
    else:
        copy_file(source.path, dest_path)
    
    # Copy the original archive.
    if link:
        link_file(orig_path, os.path.join(dest_dir, orig_name))
    else:
        copy_file(orig_path, os.path.join(dest_dir, orig_name))
    
    # Copy the diff archive, if present.
    if diff_name:
        if link:
            link_file(diff_path, os.path.join(dest_dir, diff_name))
        else:
            copy_file(diff_path, os.path.join(dest_dir, diff_name))

def add_packages_and_sources(path, file_paths, link = False):

    for file_path in file_paths:
    
        for package in find_files_from_pattern(file_path, Package):
            add_package(package, path, link)
    
    for file_path in file_paths:
    
        for source in find_files_from_pattern(file_path, Source):
            add_source(source, path, link)
    
    return 0

# Remove packages and sources

def remove_packages_and_sources(component_path, names):

    names = set(names)
    
    # Examine the different architectures available.
    
    catalogues = {}
    
    for arch in os.listdir(component_path):
    
        arch_path = os.path.join(component_path, arch)
        
        if arch == "source":
            Sources_obj = Sources(os.path.join(arch_path, "Sources"))
            Sources_obj.read()
            catalogues[arch] = Sources_obj
        else:
            Packages_obj = Packages(os.path.join(arch_path, "Packages"))
            Packages_obj.read()
            catalogues[arch] = Packages_obj
    
    # Read the binary packages first to obtain all the source packages, then read
    # the binary packages referred to by the source packages.
    
    sources = {}
    packages = {}
    source_names = set()
    package_names = set()
    
    for arch in catalogues:
    
        if arch == "source":
            continue
        
        for name in names:
        
            package = catalogues[arch].find(name)
            if package:
                packages[name] = package
                try:
                    source_names.add(package["Source"])
                except KeyError:
                    pass
    
    # Read the source packages. Note that the original list of names may
    # contain source package names.
    
    if "source" in catalogues:
    
        for name in source_names.union(names):
        
            source = catalogues["source"].find(name)
            if source:
                sources[name] = source
                for binary_name in map(lambda b: b.strip(), source["Binary"].split(",")):
                    package_names.add(binary_name)
    
    # Find the packages corresponding to the newly found package names.
    
    for arch in catalogues:
    
        if arch == "source":
            continue
        
        for name in package_names:
        
            package = catalogues[arch].find(name)
            if package:
                packages[name] = package
    
    if "source" in catalogues:
    
        for source in sources.values():
            remove_file(source.path)
            source_dir = os.path.split(source.path)[0]
            for file_name in map(lambda n: n.strip().split()[-1], source["Files"]):
                remove_file(os.path.join(source_dir, file_name))
    
    for package in packages.values():
        remove_file(package.path)
    
    return 0

# Update repository

def update_tree(levels, parent_path, root_path = None, component = None, architecture = None):

    # <repo>/dists/<suite>/<component>/<architecture>
    
    if len(levels) == 0:
        root_path = parent_path
    
    print "Entering", parent_path
    
    subdirs = os.listdir(parent_path)
    
    files = []
    packages = []
    architectures = []
    components = []
    
    if len(levels) == 4:

        info_dict = {}
        
        # In the component level, the subdirectories represent architectures.
        child_path = os.path.join(parent_path, "source")
        if "source" in subdirs and os.path.isdir(child_path):
            print "Entering", child_path
            sources = catalogue_sources(child_path, root_path)
            packages, files, architectures = write_catalogue_sources_file(child_path, root_path, component, sources)
            subdirs.remove("source")
        
        # Add a binary-i386 subdirectory if not present.
        #if "binary-i386" not in subdirs:
        #    os.mkdir(os.path.join(parent_path, "binary-i386"))
        #    subdirs.append("binary-i386")
        
        for subdir in subdirs:
        
            child_path = os.path.join(parent_path, subdir)
            if not os.path.isdir(child_path):
                continue
            
            print "Entering", child_path
            architecture = subdir.replace("binary-", "")
            
            # In each architecture directory, catalogue all the section subdirectories.
            # In the source directory, catalogue the sources for the section instead.
            new_packages = catalogue_packages(child_path, root_path)
            
            packages += new_packages
            info_dict[architecture] = (child_path, new_packages)
        
        # Write the package files.
        for architecture, (path, new_packages) in info_dict.items():
        
            # Add the all entries to each of the package files for the architectures.
            if architecture != "all" and "all" in info_dict:
                files += write_catalogue_package_file(component, architecture, path, new_packages + info_dict["all"][1])
            else:
                files += write_catalogue_package_file(component, architecture, path, new_packages)
    
    else:
        for subdir in subdirs:
        
            child_path = os.path.join(parent_path, subdir)
            if not os.path.isdir(child_path):
                continue
            
            elif len(levels) == 3:
                # In the suite level, the subdirectories represent components.
                component = subdir
            
            new_packages, new_files, new_archs = update_tree(levels + [subdir], child_path, root_path, component, architecture)
            packages += new_packages
            files += new_files
            architectures += new_archs
            components.append(component)
        
        if len(levels) == 3:
        
            # When in the suite/distribution directory, write a Release file.
            suite = os.path.split(parent_path)[1]
            write_suite_release(files, parent_path, suite, components, architectures)
    
    return packages, files, architectures

def update_repo(path):

    # Catalogue the packages themselves.
    origin = os.path.split(os.path.abspath(path))[1]
    update_tree([origin], path)
    return 0

def sign_repo(root_path, suites):

    for suite in suites:
    
        path = os.path.join(root_path, "dists", suite)
        Release_path = os.path.join(path, "Release")
        Release_gpg_path = Release_path + ".gpg"
        
        if os.path.exists(Release_path):
        
            if os.path.exists(Release_gpg_path):
                os.remove(Release_gpg_path)
                
            s = subprocess.Popen(["gpg", "-a", "-b", "--sign", "-o",
                                  Release_gpg_path, Release_path],
                                  stderr=subprocess.PIPE)
            if s.wait() != 0:
                sys.stderr.write("Problem with file: %s\n" % Release_path)
                for line in s.stderr.readlines():
                    sys.stderr.write("  "+line)
                    return 1
        else:
            sys.stderr.write("Release file not found: %s\n" % Release_path)
            return 1
    
    return 0

create_syntax = "create <repository root directory> <suites> <components>"
add_syntax = "add <repository component directory> [--link] <package or source file> ..."
remove_syntax = "remove <repository component directory> <package name> ..."
update_syntax = "update <repository root directory>"
sign_syntax = "sign <repository root directory> <suites>"

general_help = (
    "    <suites> is a comma-separated list of releases. "
    "For example: hardy,lucid,precise\n"
    "    <components> is a comma-separated list of components. "
    "For example: main,universe,contrib\n\n"
    )

if __name__ == "__main__":

    if len(sys.argv) > 1:
    
        command = sys.argv[1]
    
        if command == "create":
            if len(sys.argv) != 5:
                sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], create_syntax))
                sys.exit(1)
            
            suites = sys.argv[3].split(",")
            components = sys.argv[4].split(",")
            sys.exit(create_repo(sys.argv[2], suites, components))
        
        elif command == "add":
            if len(sys.argv) < 4:
                sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], add_syntax))
                sys.exit(1)
            
            if sys.argv[3] == "--link":
                sys.exit(add_packages_and_sources(sys.argv[2], sys.argv[4:], True))
            else:
                sys.exit(add_packages_and_sources(sys.argv[2], sys.argv[3:], False))
        
        elif command == "remove":
            if len(sys.argv) < 3:
                sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], remove_syntax))
                sys.exit(1)
            
            sys.exit(remove_packages_and_sources(sys.argv[2], sys.argv[3:]))
        
        elif command == "update":
            if len(sys.argv) != 3:
                sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], update_syntax))
                sys.exit(1)
            
            sys.exit(update_repo(sys.argv[2]))
    
        elif command == "sign":
            if len(sys.argv) != 4:
                sys.stderr.write("Usage: %s %s\n" % (sys.argv[0], sign_syntax))
                sys.exit(1)
            
            suites = sys.argv[3].split(",")
            sys.exit(sign_repo(sys.argv[2], suites))
    
    this_file = os.path.split(sys.argv[0])[1]
    sys.stderr.write("Usage: %s %s\n" % (this_file, create_syntax))
    sys.stderr.write("       %s %s\n" % (this_file, add_syntax))
    sys.stderr.write("       %s %s\n" % (this_file, remove_syntax))
    sys.stderr.write("       %s %s\n" % (this_file, update_syntax))
    sys.stderr.write("       %s %s\n" % (this_file, sign_syntax))
    sys.stderr.write("\n" + general_help)
    sys.exit(1)


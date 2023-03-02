#!/usr/bin/env python3
import inspect
import os
import re
import shutil
import sys
import subprocess
import requests
import tarfile

dependencies = {
    "enabled": ("libstdc++6",
                """
                "libpcsclite-dev",
                "libcurl4-openssl-dev",
                "libsrt-openssl-dev"
                """
                ),
    "global-dependencies": ("git", "git-lfs", "g++", "cmake", "dos2unix",
                            "curl", "tar", "zip", "doxygen", "graphviz",
                            "dialog", "apt-utils",
                            "linux-libc-dev", "libedit-dev", "libusb-1.0-0-dev",
                            "pcscd", "dpkg-dev", "default-jdk", "software-properties-common",
                            "gcc-6"),
    "libstdc++6": {
        "version": "6.5.0",
        "download-url": "https://bigsearcher.com/mirrors/gcc/releases/gcc-6.5.0/gcc-6.5.0.tar.gz",
        "unique-deps": ('libgmp-dev', 'libmpfr-dev', 'libmpc-dev', 'gcc-multilib'),
        "configure-steps": (
            ('mkdir', 'build'),
            ('chdir', 'build'),
            ('configure',
             "configure -v --with-pkgversion='Qencode-TSDUCK 6.5.0' --with-bugurl=file:///usr/share/doc/gcc-6/README.Bugs --enable-languages=c,c++ --prefix=<%prefix%> --with-as=<%check_path:/usr/bin/x86_64-linux-gnu-as%> --with-ld=<%check_path:/usr/bin/x86_64-linux-gnu-ld%> --program-suffix=-6 --program-prefix=x86_64-linux-gnu- --enable-shared --enable-linker-build-id --libexecdir=<%prefix%>/lib --without-included-gettext --enable-threads=posix --libdir=<%libdir%> --enable-nls --with-sysroot=/ --enable-clocale=gnu --enable-libstdcxx-debug --enable-libstdcxx-time=yes --with-default-libstdcxx-abi=new --enable-gnu-unique-object --disable-vtable-verify --enable-libmpx --enable-plugin --enable-default-pie --with-system-zlib --with-target-system-zlib --enable-multiarch --disable-werror --with-arch-32=i686 --with-abi=m64 --with-multilib-list=m32,m64,mx32 --enable-multilib --with-tune=generic --enable-checking=release --build=x86_64-linux-gnu --host=x86_64-linux-gnu --target=x86_64-linux-gnu")
        ),
        "make-steps": (),
        "install-steps": ()
    },
    "libpcsclite-dev": {
        "version": "1.9.9",
        "download-url": "https://pcsclite.apdu.fr/files/pcsc-lite-1.9.9.tar.bz2",
        "unique-deps": (),
        "configure-steps": (),
        "make-steps": (),
        "install-steps": ()
    },
    "libcurl4": {
        "version": "7.88.0",
        "download-url": "https://github.com/curl/curl/releases/download/curl-7_88_0/curl-7.88.0.tar.gz",
        "unique-deps": (),
        "configure-steps": (),
        "make-steps": (),
        "install-steps": ()
    },
    "libcurl4-openssl-dev": {
        "version": "7.88.0",
        "download-url": "https://github.com/curl/curl/releases/download/curl-7_88_0/curl-7.88.0.tar.gz",
        "unique-deps": (),
        "configure-steps": (),
        "make-steps": (),
        "install-steps": ()
    },
    "libsrt-openssl-dev": {
        "version": "1.4.4",
        "download-url": "https://github.com/Haivision/srt/archive/refs/tags/v1.4.4.tar.gz",
        "unique-deps": (),
        "configure-steps": (),
        "make-steps": (),
        "install-steps": ()
    }
}


def is_util_available(util_path, util_name: str) -> bool:
    if util_path is None:
        print("Cant find " + util_name)
        return False
    return True


def create_folder(path: str, with_sudo: bool = False) -> bool:
    cli_command = list()
    if with_sudo:
        cli_command.append('sudo')
    cli_command.extend(('mkdir', '-p', path))

    if not os.path.exists(path):
        p = subprocess.Popen(cli_command,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        if p.returncode != 0 and p.returncode != None:
            print("Can't create directory:", p.stderr.readlines())
            return False
    return True


def remove_dir(dir_path: str, with_sudo: bool = False) -> bool:
    cli_command = list()
    if with_sudo:
        cli_command.append('sudo')
    cli_command.extend(('rm', '-rf', dir_path))
    p = subprocess.Popen(cli_command,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    if p.returncode != 0 and p.returncode != None:
        print("Can't delete folder: ", p.stderr.readlines())
        return False
    print(dir_path, 'folder removed due to distribution cleaning')
    return True


def distclean(prefix_path: str, libdir: str, tempdir: str) -> (bool, bool, bool):
    res_prefix_path = remove_dir(prefix_path, with_sudo=True)
    res_libdir_path = remove_dir(libdir)
    res_tempdir_path = remove_dir(tempdir)
    return res_prefix_path, res_libdir_path, res_tempdir_path


def clean_cmd_output(output: list) -> (bool, tuple):
    _output_ = list()
    if len(output) == 0:
        return False, _output_

    for o in output:
        o_ = o.decode('utf-8')
        if o_[-1] == '\n':
            o_ = o_[:-1]
        if len(o_) > 0:
            _output_.append(o_)
    return True, _output_


def install_apt_package(package: str) -> bool:
    echo_path = shutil.which("echo")
    debconf_path = shutil.which("debconf")
    dss_path = shutil.which("debconf-set-selections")
    sudo_path = shutil.which("sudo")
    aptget_path = shutil.which("apt-get")
    p = subprocess.Popen((echo_path, "'" + debconf_path + ' debconf/frontend select Noninteractive' + "'|", dss_path),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    if p.returncode != None:
        if p.returncode != 0:
            print("Error ocurred while setting debconf environment variable:", clean_cmd_output(p.stderr.readlines())[1])
        return False

    out: (bool, tuple) = clean_cmd_output(p.stdout.readlines())
    if out[0]:
        print("STDOUT of setting environment variable:", out[1])

    p = subprocess.Popen((sudo_path, aptget_path, '-qq', 'install', '-y', package),
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
    if p.returncode != None:
        if p.returncode != 0:
            print('Error due installing package', package, 'with error:', clean_cmd_output(p.stderr.readlines())[1])
        return False

    print('Package', package, 'installed successfully')
    return True


def download_archive(download_url: str, path: str) -> (bool, str):
    if len(download_url) == 0:
        return False, None

    filename = path + '/' + download_url.split('/')[-1]
    print("Downloading file: " + download_url, end=' ')
    r = requests.get(download_url, allow_redirects=True, stream=True, timeout=120)
    if r.status_code < 200 or r.status_code >= 300:
        print("Can't download file from", download_url)
        return False, None
    with open(filename, 'wb') as f:
        if type(r.headers.get('content-length')) is not type(None):
            file_size = int(r.headers.get('content-length'))
        else:
            file_size = 1
        total_downloaded = 0
        last_percent_num = 0
        for chunk in r.iter_content(chunk_size=128):
            total_downloaded += len(chunk)
            if file_size == 1:
                progress = int((total_downloaded * 100) / total_downloaded)
            else:
                progress = int((total_downloaded * 100) / file_size)
            if last_percent_num < progress:
                last_percent_num = progress
                if last_percent_num % 2 == 0:
                    print('.', end='')
            f.write(chunk)
            f.flush()
    f.close()
    print(" Done!")
    print("Archive received to:", filename, "with size", os.path.getsize(filename), "bytes")
    return True, filename


def decompress_archive(archive_path: str, decompress_path: str) -> (bool, str):
    if not tarfile.is_tarfile(archive_path):
        return False, None

    try:
        arch = tarfile.open(archive_path, mode='r:*')
    except tarfile.ReadError as e:
        print("Can't open archive for", archive_path, "due to the error", e)
        return False, None

    try:
        arch.extractall(path=decompress_path)
    except tarfile.ExtractError as e:
        print("Can't extract archive ", archive_path, "due to the error", e)
        return False, None

    try:
        os.remove(archive_path)
    except OSError as e:
        print("Can't remove archive ", archive_path, "due to the error", e)
        return False, None

    fs_objs = os.listdir(decompress_path)
    if len(fs_objs) > 1:
        print("There is more than one element at the root of archive", archive_path)
        return False, None
    elif len(fs_objs) == 0:
        print("There is no element at the root of archive", archive_path)
        return False, None

    return True, (decompress_path + '/' + fs_objs[0])


def compile_library(libname: str, prefix_path: str, tempdir_path: str, libdir_path: str, **kwargs) -> bool:
    unique_deps = dependencies.get(libname).get('unique-deps')
    if len(unique_deps) > 0:
        for next_dep in unique_deps:
            if not install_apt_package(next_dep):
                return False

    ret: (bool, str) = download_archive(dependencies.get(libname).get("download-url"), tempdir_path)
    if not ret[0]:
        return False
    archive_path = ret[1]

    ret: (bool, str) = decompress_archive(archive_path=archive_path, decompress_path=tempdir_path)
    if not ret[0]:
        return False

    source_path = ret[1]

    configure_steps: tuple = dependencies.get(libname).get('configure-steps')
    building_directory = str()
    configure_command = str()
    chdir_for_building = False
    if len(configure_steps) > 0:
        for next_step in configure_steps:
            if next_step[0] == 'mkdir':
                building_directory = source_path + '/' + next_step[1]
                if not create_folder(building_directory):
                    print("Failed to make build folder.")
                    return False
            elif next_step[0] == 'chdir':
                chdir_for_building = True
            elif next_step[0] == 'configure':
                configure_command_args = next_step[1].split()
                for (i, next_argument) in enumerate(configure_command_args):
                    if i == 0:
                        configure_command_args[i] = source_path + '/' + next_argument
                        continue

                    if next_argument.find(r'<%prefix%>') != -1:
                        configure_command_args[i] = re.sub(r'<%prefix%>', prefix_path, next_argument)

                    if next_argument.find(r'<%libdir%>') != -1:
                        configure_command_args[i] = re.sub(r'<%libdir%>', lib_dir, next_argument)

                    for next_arg in kwargs.keys():
                        if next_argument.find(next_arg) != -1:
                            configure_command_args[i] = re.sub(next_arg, kwargs.get(next_arg), next_argument)

                    if next_argument.find(r'<%check_path:') != -1:
                        next_argument = next_argument.replace(r'<%check_path:', '')
                        next_argument = next_argument.replace(r'%>', '')
                        path2check = next_argument.split('=')

                        if not os.path.exists(path2check[1]):
                            print('Path does not exist:', path2check[1])
                            return False
                        configure_command_args[i] = "=".join(path2check)

                configure_command = ' '.join(configure_command_args)

        if len(configure_command) > 0:
            print("Configure command:", configure_command)
        else:
            return False

        # p = subprocess.Popen(configure_command,
        #                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE,
        #                      cwd=building_directory if chdir_for_building else '.')
        #
        # if p.returncode != None and p.returncode != 0:
        #     print("Can't configure ", libname, "due to error:", p.stderr.readlines())
        #     return False

    print("Archive path:", source_path)
    # if not remove_dir(source_path):
    #     return False
    return True


if __name__ == '__main__':
    print('Starting installation of dependencies of the TSDUCK project', end='\n\n')
    current_path = os.path.dirname(__file__)
    if not current_path.endswith('/'):
        current_path += '/'

    _prefix_path = '/opt/tsduck.static'
    temp_dir = current_path + r'/' + 'temp'
    temp_dir = r'/var/video/' + 'temp'
    lib_dir = _prefix_path + '/lib'

    print("Trying to clean installation folders")
    if not distclean(prefix_path=_prefix_path, libdir=lib_dir, tempdir=temp_dir):
        sys.exit("Can't make distclean scenario")

    if not create_folder(_prefix_path, with_sudo=True):
        sys.exit("Can't create prefix path folder directory")

    if not create_folder(temp_dir):
        sys.exit("Can't create temporary directory")

    if not create_folder(lib_dir):
        sys.exit("Can't create library directory")

    print('\nGetting the list of all installed packages...')

    for next_deb_packet in dependencies['global-dependencies']:
        dpkg_path = shutil.which("dpkg")
        p = subprocess.Popen((dpkg_path, '-l', next_deb_packet),
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=None)
        err = clean_cmd_output(p.stderr.readlines())
        if err[0]:
            if not install_apt_package(next_deb_packet):
                sys.exit(1)
        else:
            print('«', next_deb_packet, '» package already installed', sep='')

    for next_lib in dependencies['enabled']:
        if not compile_library(next_lib, _prefix_path, temp_dir, lib_dir):
            print('Error due compilation of the', next_lib,
                  'library. Installation of TSDUCK project will be terminated.')
            sys.exit(1)
        else:
            print(next_lib, 'library successfully instaled.')

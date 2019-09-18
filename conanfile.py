from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os
import shutil


class DoxygenInstallerConan(ConanFile):
    name = "doxygen_installer"
    version = "1.8.16"
    source_sha = '336d367ca081dd6117ddaa7503314b4a0241e548b0571d6b413fb0b826468089'
    description = "A documentation system for C++, C, Java, IDL and PHP --- Note: Dot is disabled in this package"
    topics = ("conan", "doxygen", "installer", "devtool", "documentation")
    url = "https://github.com/bincrafters/conan-doxygen_installer"
    homepage = "https://github.com/doxygen/doxygen"
    author = "Inexor <info@inexor.org>"
    license = "GPL-2.0-only"
    exports = ["LICENSE"]

    settings = "os_build", "arch_build", "compiler", "arch"
    options = {"build_from_source": [False, True]}
    default_options = "build_from_source=False"

    generators = "cmake"

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def config(self):
        if self.settings.os_build in ["Linux", "Macos"] and self.settings.arch_build == "x86":
            raise ConanInvalidConfiguration("x86 is not supported on Linux or Macos")

    def build_requirements(self):
        if self.options.build_from_source:
            self.build_requires("flex_installer/2.6.4@bincrafters/stable")
            self.build_requires("bison_installer/3.3.2@bincrafters/stable")
            self.build_requires("cmake_installer/3.15.3@conan/stable")

    def source(self):
        if not self.options.build_from_source:
            return

        archive_name = "Release_{!s}".format(self.version.replace('.', '_'))
        archive_url = "https://github.com/doxygen/doxygen/archive/{!s}.zip".format(archive_name)
        tools.get(archive_url, sha256=self.source_sha)
        os.rename("doxygen-{!s}".format(archive_name), self._source_subfolder)

        cmakefile = "{!s}/CMakeLists.txt".format(self._source_subfolder)
        executeable = "doxygen"
        if self.settings.os_build == "Windows":
            executeable += ".exe"

        tools.replace_in_file(cmakefile, "include(version)", 'include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/version.cmake")')
        tools.replace_in_file(cmakefile, "project(doxygen)", """project(doxygen)
include("../conanbuildinfo.cmake")
conan_basic_setup()""")

    def _configure_cmake(self):
        cmake = CMake(self)
        # cmake.definitions["win_static"] = "ON" if self.settings.os == 'Windows' and self.options.shared == False else "OFF"
        # cmake.definitions["use_libclang"] = "ON" if self.options.use_libclang else "OFF"

        cmake.configure(source_folder=self._source_subfolder,
                        build_folder=self._build_subfolder)
        return cmake

    def build_from_source(self):
        self.settings.arch = self.settings.arch_build  # workaround for cross-building to get the correct arch during the build
        cmake = self._configure_cmake()
        cmake.build()


    def get_download_filename(self):
        program = "doxygen"

        if self.settings.os_build == "Windows":
            if self.settings.arch_build == "x86":
                ending = "windows.bin.zip"
            else:
                ending = "windows.x64.bin.zip"
        elif self.settings.os_build == "Macos":
            program = "Doxygen"
            ending = "dmg"
        else:
            ending = "linux.bin.tar.gz"


        return "%s-%s.%s" % (program, self.version, ending)

    def unpack_dmg(self, dest_file):
        mount_point = os.path.join(self.build_folder, "mnt")
        tools.mkdir(mount_point)
        self.run("hdiutil attach -mountpoint %s %s" % (mount_point, dest_file))
        try:
            for program in ["doxygen", "doxyindexer", "doxysearch.cgi"]:
                shutil.copy(os.path.join(mount_point, "Doxygen.app", "Contents",
                                         "Resources", program), self.build_folder)
            shutil.copy(os.path.join(mount_point, "Doxygen.app", "Contents",
                                    "Frameworks", "libclang.dylib"), self.build_folder)
        finally:
            self.run("diskutil eject %s" % (mount_point))
            tools.rmdir(mount_point)

    def build_from_archive(self):
        # source location:
        # https://downloads.sourceforge.net/project/doxygen/rel-1.8.16/doxygen-1.8.16.linux.bin.tar.gz

        url = "http://downloads.sourceforge.net/project/doxygen/rel-{}/{}".format(self.version, self.get_download_filename())

        if self.settings.os_build == "Linux":
            dest_file = "file.tar.gz"
        elif self.settings.os_build == "Macos":
            dest_file = "file.dmg"
        else:
            dest_file = "file.zip"

        self.output.warn("Downloading: {}".format(url))
        tools.download(url, dest_file, verify=False)
        if self.settings.os_build == "Macos":
            self.unpack_dmg(dest_file)
            # Redirect the path of libclang.dylib to be adjacent to the doxygen executable, instead of in Frameworks
            self.run('install_name_tool -change "@executable_path/../Frameworks/libclang.dylib" "@executable_path/libclang.dylib" doxygen')
        else:
            tools.unzip(dest_file)
        os.unlink(dest_file)

        executeable = "doxygen"
        if self.settings.os_build == "Windows":
            executeable += ".exe"

    def build(self):
        if self.options.build_from_source:
            self.build_from_source()
        else:
            self.build_from_archive()

    def package(self):
        if self.options.build_from_source:
            cmake = self._configure_cmake()
            cmake.install()

        if self.settings.os_build == "Linux":
            srcdir = "doxygen-{}/bin".format(self.version)
            self.copy("*", dst="bin", src=srcdir)

        self.copy("doxygen", dst="bin")
        self.copy("doxyindexer", dst="bin")
        self.copy("doxysearch.cgi", dst="bin")
        self.copy("*.exe", dst="bin")
        self.copy("*.dylib", dst="bin")
        self.copy("*.dll", dst="bin")

    def package_info(self):
        self.env_info.PATH.append(os.path.join(self.package_folder,"bin"))

    def package_id(self):
        self.info.include_build_settings()
        if self.settings.os_build == "Windows":
            del self.info.settings.arch_build # same build is used for x86 and x86_64
        del self.info.settings.arch
        del self.info.settings.compiler

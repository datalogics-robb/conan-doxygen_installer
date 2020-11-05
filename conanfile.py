from conans import ConanFile, CMake, tools
from conans.errors import ConanInvalidConfiguration
import os
import shutil


class DoxygenInstallerConan(ConanFile):
    name = "doxygen_installer"
    version = "1.8.20"
    source_sha = '3dbdf8814d6e68233d5149239cb1f0b40b4e7b32eef2fd53de8828fedd7aca15'
    description = "A documentation system for C++, C, Java, IDL and PHP --- Note: Dot is disabled in this package"
    topics = ("conan", "doxygen", "installer", "devtool", "documentation")
    url = "https://github.com/datalogics/conan-doxygen_installer"
    homepage = "https://github.com/doxygen/doxygen"
    author = "Inexor <info@inexor.org>"
    license = "GPL-2.0-only"
    exports = ["LICENSE"]
    settings = "os_build", "arch_build", "compiler", "arch"
    options = {"build_from_source": [True,]}
    default_options = "build_from_source=True"
    generators = "cmake", "virtualenv"
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def config(self):
        if self.settings.os_build in ["Linux", "Macos"] and self.settings.arch_build == "x86":
            raise ConanInvalidConfiguration("x86 is not supported on Linux or Macos")


    def build_requirements(self):
        self.build_requires("flex_installer/2.6.4@bincrafters/stable")
        self.build_requires("bison/3.5.3")

    def source(self):
        archive_name = "Release_{!s}".format(self.version.replace('.', '_'))
        archive_url = 'https://github.com/doxygen/doxygen/archive/{}.tar.gz'.format(archive_name)
        tools.get(archive_url, sha256=self.source_sha)
        os.rename("doxygen-{!s}".format(archive_name), self._source_subfolder)

        cmakefile = "{!s}/CMakeLists.txt".format(self._source_subfolder)
        executeable = "doxygen"
        if self.settings.os_build == "Windows":
            executeable += ".exe"

        tools.replace_in_file(cmakefile, "include(version)", 'include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/version.cmake")')
        tools.replace_in_file(cmakefile, "project(doxygen)", """project(doxygen)
include("../conanbuildinfo.cmake")
conan_basic_setup()
set(TARGET_ARCHIVES_MAY_BE_SHARED_LIBS ON)""")
        tools.replace_in_file(cmakefile, 'find_package(Iconv REQUIRED)',
                              """if(CMAKE_SYSTEM_NAME STREQUAL "AIX" AND CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
  # CMake's check for iconv fails on AIX when iconv is there and properly working
  set(Iconv_INCLUDE_DIR  "/usr/include")
  set(Iconv_LIBRARY "-liconv")
else()
  find_package(Iconv REQUIRED)
endif()""")
        qglobal = "{!s}/qtools/qglobal.h".format(self._source_subfolder)
        tools.replace_in_file(qglobal, '#define QGLOBAL_H', """#define QGLOBAL_H
#include <cinttypes>""")
        mscgen_b = "{!s}/libmscgen/mscgen_bool.h".format(self._source_subfolder)
        tools.replace_in_file(mscgen_b, '#define MSCGEN_BOOL_H',"""#define MSCGEN_BOOL_H
#if defined(FALSE)
#undef FALSE
#endif
#if defined(TRUE)
#undef TRUE
#endif
""")
        util_cpp = "{!s}/src/util.cpp".format(self._source_subfolder)
        tools.replace_in_file(util_cpp, '#include "htmlentity.h"',"""#include "htmlentity.h"
#ifndef PRIu64
#define PRIu64 "%u"
#endif
""")


    def _configure_cmake(self):
        cmake = CMake(self)
        cmake.configure(source_folder=self._source_subfolder,
                        build_folder=self._build_subfolder)
        return cmake

    def build(self):
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


    def package(self):
        cmake = self._configure_cmake()
        cmake.install()

        if self.settings.os_build in ['Linux', 'AIX', 'SunOS']:
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools

class TestPackageConan(ConanFile):
    options = {"build_from_source": [False, True]}
    default_options = "build_from_source=True"
    generators = "cmake_paths"
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        
    def test(self):
        if not tools.cross_building(self.settings):
            self.output.info("Version:")
            self.run("doxygen --version", run_environment=True)

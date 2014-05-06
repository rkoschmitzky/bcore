#-*-coding:utf-8-*-
"""
@package bprocess.plugins.be
@brief A program launcher for the be command framework

@author Sebastian Thiel
@copyright [GNU Lesser General Public License](https://www.gnu.org/licenses/lgpl.html)
"""
__all__ = ['LauncherBeSubCommand']

import os

import bapp
from bapp import ApplicationSettingsClient
from butility import Version
from bcmd import InputError
from be import BeSubCommand
from bprocess import (PackageDataIteratorMixin,
                      ProcessController,
                      package_schema)


class LauncherBeSubCommand(BeSubCommand, ApplicationSettingsClient, PackageDataIteratorMixin, 
                           bapp.plugin_type()):
    """A progam to launch arbitrary configured bprocess executables"""
    __slots__ = ()

    name = 'go'
    version = Version('0.1.0')
    description = "launch any configured program"

    # defaults to package schema - we just get all the values
    # NOTE: could be more efficient by only getting what we need
    _schema = PackageDataIteratorMixin.new_controller_schema()

    # Those are to be passed to the application
    allow_unknown_args = True

    def _executable_package_names(self):
        """@return a list of program names that are executable, based on our context
        We have to emulate the behaviour of the process controller, using it's own functionality
        """
        res = list()
        packages = self.settings_value(bapp.main().context().settings())
        becmd = self._main_command_name()
        for package_name in packages.keys():
            if package_name == becmd:
                continue
            # end don't place ourselves to prevent the guys from calling themselves just for fun ;)
            package = self._to_package(package_name, packages[package_name])
            package = ProcessController._resolve_package_alias(package, lambda n: self._to_package(n, packages[n]))
            try:
                # this raises if there is nothing
                package.executable(os.environ)
                res.append(package_name)
            except Exception:
                continue
            # end handle no executable configured
        # end for each package
        return res
        
    def setup_argparser(self, parser):
        """Setup your flags using argparse"""
        choices = self._executable_package_names()
        if not choices:
            raise InputError("No program configured for launch")
        # end handle nothing there

        help = "The name of the program to start"
        parser.add_argument('program', 
                             choices=choices,
                             help=help)
        return self

    def execute(self, args, remaining_args):
        # This will never return, spawn is off (unless the delegate overrides it).
        # Also we let it build it's Context from scratch, and won't pass ours
        # It's important to pass the CWD as major context provider to the called program
        process = ProcessController(args.program, remaining_args, cwd = os.getcwd()).execute()

        # If the delegate wanted something else, we use the return code of the program
        return process.returncode

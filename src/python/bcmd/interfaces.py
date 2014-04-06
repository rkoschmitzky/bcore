#-*-coding:utf-8-*-
"""
@package bcmd.interfaces
@brief Interfaces for the command framework

@copyright 2013 Sebastian Thiel
"""
__all__ = ['ICommand', 'ISubCommand']

import bapp
from bapp import Version
from bapp.core.kvstore import (   
                                KeyValueStoreSchema,
                                RootKey
                            )

class ICommand(bapp.InterfaceBase):
    """A command implementing the command pattern, specialized for use with the commandline."""
    __slots__ = ()
    
    info_schema = KeyValueStoreSchema(RootKey, \
    {
    # The name of the command
    'name' : str,
    # The version of the command, ideally as semantic version
    'version' : Version('UNKNOWN'),
    # A name that should be used as prefix in logs
    'log_id' : str,
    # A more detailed description about what your command does
    'description' : str,
    })
    
    ## @name Interface
    # @{
    
    @bapp.abstractmethod
    def info(self):
        """@return KeyValueStoreProvider with information matching ICommand.info_schema"""
    
    @bapp.abstractmethod
    def setup_argparser(self, argparser):
        """Called to add arguments to the argparser
        @param argparser bcmd.argparse.ArgumentParser compatible instance which is to be configured
        @return self
        @note see [the argparse module](http://docs.python.org/2/library/argparse.html#module-argparse) for 
        more information on how to set it up"""
        
    @bapp.abstractmethod
    def log(self):
        """@return our logging.Logger instance for general use"""
        
    @bapp.abstractmethod
    def execute(self, args, remaining_args):
        """Method implementing the actual functionality of the command
        @param args argparse.Namespace instance as generated by our ArgumentParser.parse_args() method
        @param remaining_args tuple of remaining positional argument strings passed to the process on 
        the commandline which  could not be understood by our argument parser
        @return exit code of your command which is an integer between 0 (success) and 255 (error state) 
        the caller is responsible to translate this into a respective  system exit, which depends
        on the current host application.
        @note by definition, a command is required to support multiple invocations of this method with the 
        same instance. Therefore it must manage its internal state accordingly."""
        
    ## -- End Interface -- @}
        
# end class ICommand


class ISubCommand(ICommand):
    """Represents a particular mode for a command, e.g. 'install' for the 'yum' command.
    
    A SubCommand is a command which is associated with a main command that will delegate the work to the 
    subcommand selected on the commandline.
    
    Subcommands provide additional information to associate them with their respective main command. This 
    assures the right subcommands can be instantiated for a particular main command using the component framework.
    """
    __slots__ = ()
    
    # Required as this only works automatically for direct decendants of SubCommand
    place_into_root_package = True
    
    def __init__(self):
        """Subcommands must have a default constructor"""
        super(ISubCommand, self).__init__()
    
    # -------------------------
    ## @name Interface
    # @{
    
    @bapp.abstractmethod
    def is_compatible(self, command):
        """@return True if this subcommand is valid for use with the given ICommand compatible instance.
        You could use the info() method to check the program name for instance.
        """
    
    ## -- End Interface -- @}

# end class SubCommand

#-*-coding:utf-8-*-
"""
@package bapp.utility
@brief Contains utilities with minimal dependencies

@author Sebastian Thiel
@copyright [GNU Lesser General Public License](https://www.gnu.org/licenses/lgpl.html)
"""
from __future__ import unicode_literals
from butility.future import str

__all__ = ['ApplicationSettingsMixin', 'LogConfigurator', 'StackAwareHierarchicalContext',
           'preserve_application']

import os
import warnings
import hashlib
import logging
import logging.config

from butility import (Path,
                      OrderedDict,
                      wraps)

from bkvstore import KeyValueStoreSchema
from bcontext import HierarchicalContext

import bapp


# ==============================================================================
# @name Decorators
# ------------------------------------------------------------------------------
# @{

def preserve_application(fun):
    """A wrapper which preserves whichever value was in bapp.Application.main.
    Useful if a method or fucntion wants to temporarily swap the processes Application instance
    to manipulate code using the global instance.
    Code should whenever feasible not rely on the global instance"""
    @wraps(fun)
    def wrapper(*args, **kwargs):
        prev = bapp.Application.main
        try:
            return fun(*args, **kwargs)
        finally:
            # the default context might have been picked up by the Application fun created, and
            # we need to be sure to put it back to where it was
            new_app = bapp.Application.main
            if not prev and new_app:
                new_app = new_app.first_application()
                default_ctx = None
                for ctx in new_app.context().stack():
                    if ctx.name() == bapp.Application.PRE_APPLICATION_CONTEXT_NAME:
                        default_ctx = ctx
                        break
                    # end context found
                # end find default context if possible
                if default_ctx:
                    assert len(bapp.Application.Plugin.default_stack) == 0
                    bapp.Application.Plugin.default_stack.push(default_ctx)
                # end reapply default context
            # end check default context
            bapp.Application.main = prev
        # end reset Application
    # end wrapper
    return wrapper

# -- End Decorators -- @}


# ==============================================================================
# @name Types
# ------------------------------------------------------------------------------
# @{

class ApplicationSettingsMixin(object):

    """A mixin to allow anyone to safely use the context of the global Context stack.
    Everyone using the global context should derive from it to facilitate context usage and to allow the 
    ContextStack to verify its data.

    This type basically brings together a schema with another type, to make data access to any context easy
    @todo this system is for review, as there will be no 'global' state that we may know here. This would go to the bapplication interface
    """
    __slots__ = ()

    # Schema specifying how we would like to access the global context
    # It must be set by subclasses if they access the context
    # The base implementation of schema() will just return this class-level instance, per instance
    # schemas are generally possible though
    _schema = None

    @classmethod
    def settings_schema(cls):
        """@return our schema instance, by default it will return the class level instance
        """
        assert isinstance(cls._schema, KeyValueStoreSchema), "Subclass must provide a schema instance"
        return cls._schema

    @classmethod
    def settings_value(cls, context=None, resolve=True):
        """@return a nested dict with getattr access as obtained from the current ContextStack's context, 
        validated against our schema.
        @param cls
        @param context if not None, use the given context (KeyValueStoreProvider) instead of the global one
        @param resolve if True, string values will be resolved
        @note use this method when you need access to the datastructure matching your schema"""
        return (context or bapp.main().context().settings()).value_by_schema(cls.settings_schema(), resolve=resolve)


# end class ApplicationSettingsMixin


class StackAwareHierarchicalContext(HierarchicalContext):

    """A context which will assure a configuration file is never loaded twice.
    This can happen if paths have common roots, which is the case almost always.

    To prevent duplicate loads, which in turn may yield somewhat unexpected application settings, this implementation 
    uses the current applications stack to find other Contexts of our type.
    """
    __slots__ = ('_hash_map',
                 '_app')

    def __init__(self, directory, application=None, **kwargs):
        """Initialize this instance. Additionally, you may specify the application to use.
        If unspecified, the global one will be used instead"""
        super(StackAwareHierarchicalContext, self).__init__(directory, **kwargs)
        self._hash_map = OrderedDict()
        self._app = application

    def _iter_application_contexts(self):
        """@return iterator yielding environments of our type on the stack, which are not us"""
        for ctx in (self._app or bapp.main()).context().stack():
            # we should be last, but lets not assume that
            if ctx is self or not isinstance(ctx, StackAwareHierarchicalContext):
                continue
            yield ctx
        # end for each environment

    def _filter_files(self, files):
        """@note our implementation will compare file hashes in our own hash map with ones of other
        instances of this type on the stack to assure we don't accidentally load the same file
        @note This method will update our _hash_map member"""
        # NOTE: it's important to stay within the ascii range (thus hexdigest()), as this mep at some
        # point gets encoded. In py2, there's just bytes, in py3, it will be tempted to interpret these
        # as strings, without having a chance to find a suitable encoding
        for config_file in files:
            self._hash_map[hashlib.md5(open(config_file, 'rb').read()).hexdigest()] = config_file
        # end for each file

        # subtract all existing hashes
        our_files = set(self._hash_map.keys())
        for env in self._iter_application_contexts():
            our_files -= set(env._hash_map.keys())
        # end for each environment

        # return all remaining ones
        # Make sure we don't change the sorting order !
        return list(self._hash_map[key] for key in self._hash_map if key in our_files)

    # -------------------------
    # @name Interface
    # @{

    def hash_map(self):
        """@return a dictionary of a mapping of md5 binary strings to the path of the loaded file"""
        return self._hash_map

    # -- End Interface -- @}

# end class StackAwareHierarchicalContext


class _KVStoreLoggingVerbosity(object):

    """Implements a valid verbosity"""
    __slots__ = ('level')

    def __init__(self, value='INFO'):
        if not hasattr(logging, value):
            raise ValueError("Invalid logging verbosity: %s" % value)
        # end check if value exists
        self.level = getattr(logging, value)

# end class _KVStoreLoggingVerbosity


class LogConfigurator(ApplicationSettingsMixin):

    """Implements the ILog interface and allows to initialize the logging system using context configuration"""
    __slots__ = ()

    # -------------------------
    # @name Configuration
    # @{

    _schema = KeyValueStoreSchema('logging', {'logdir': Path,
                                              # Directory into which to drop files. If empty, there
                                              # will be no file logger
                                              'inifile': Path,
                                              # Ini file to read to configure logging.
                                              'verbosity': _KVStoreLoggingVerbosity,
                                              # Disables any kind of logging configuration
                                              # which may be provided by the host application
                                              # NOTE: At some point we should control it precisely
                                              # enough to never use this flag
                                              'disable': True
                                              })

    # -- End Configuration -- @}

    @classmethod
    def initialize(cls, verbosity=None):
        """Initialize the logging system using the information provided by the context
        @param verbosity may be a logging.LEVEL value, which will override anything that is set elsewhere.
        @note at some point we might want to implement a more sophisticated yaml based log initialization"""
        # definition of possible overrides (i.e. which configuration file to use)
        value = cls.settings_value()
        log_config_file = value.inifile

        # See #6239
        # NOTE: at least the environment variable can probably be removed once the actual culprit is found
        # Why does our configuration kill pythons logging entirely in case of katana at least ?
        if value.disable or 'BAPP_LOGGING_INITIALIZATION_DISABLE' in os.environ:
            return
        # end no init if disabled

        # initialize fallback defaults if no configuration file was found
        if not log_config_file or not os.path.isfile(log_config_file):
            # Resort to standard setup if there is no further configuration
            logging.basicConfig()
        else:
            additional_exception = getattr(__builtins__, 'WindowsError', IOError)

            # BUGFIX 2759
            # make sure the appropriate path exists and is writable, otherwise warn and use different temporary
            # directory..
            try:
                # DO NOT DISABLE LOGGERS CREATED SO FAR ! What a shitty default !
                logging.config.fileConfig(log_config_file, disable_existing_loggers=False)
            except (IOError, additional_exception) as err:
                warnings.warn("logging configuration from ini file failed with error: %s" % str(err))
                base_setup()
            # end handle unwritable paths
        # end create configuration if not yet set

        log = logging.root
        log.setLevel(verbosity or value.verbosity.level)

        # Setup logfile
        if value.logdir:
            if not value.logdir.isdir():
                try:
                    value.logdir.makedirs()
                    # Make sure that everyone can write into that folder - especially important for the farm
                    # available on windows
                    value.logdir.chmod(0o777)
                except (OSError, IOError):
                    log.error("Could not create log directory at %s", value.logdir)
            # end handle logdir creation

            if value.logdir.isdir():
                try:
                    logfile_handler = handlers.DefaultLogFileHandler(value.logdir)
                    logfile_handler.setFormatter(formatters.LogFileFormatter())
                    log.addHandler(logfile_handler)
                except (OSError, IOError):
                    log.error("Could not write log into directory '%s'", value.logdir)
                # end handle write problems - we must never abort ...
            else:
                log.error("Log directory at %s did not exist - file logging disabled", value.logdir)
            # end handle logdir exists
        # end handle logdir exists

# end class LogConfigurator

# -- End Types -- @}

#-*-coding:utf-8-*-
"""
@package bcmd.daemon
@brief Create powerful daemon processes quickly

@author Sebastian Thiel
@copyright [GNU Lesser General Public License](https://www.gnu.org/licenses/lgpl.html)
"""
__all__ = []

__all__ = ['DaemonCommandMixin']

import sys
import os
import signal
from time import sleep

from bapp import ApplicationSettingsMixin
from butility import (Path,
                      daemonize)
                    

class DaemonCommandMixin(object):
    """Main Daemon command without subcommands. Just starts a thread which can be an EnvironmentStackContextClient
    """

    # -------------------------
    ## @name Subclass Configuration
    # @note all CommandBase configuration must be provided too
    # @{

    ## The kind of TerminatableThread, which must be a context client, to daemonize
    # Must be set in subclass
    ThreadType = None
    
    ## -- End Subclass Configuration -- @}


    # -------------------------
    ## @name Settings
    # Allows to override names taken on the commandline
    # @{

    ## we check every now and then for intterups or exceptions, and sleep in the meanwhile
    check_period_s = 0.5

    pid_file_args = ['-d', '--pid-file']

    # only used if ThreadType has custom configuration
    show_config_args = ['-c', '--show-configuration']

    ## -- End Settings -- @}

    # -------------------------
    ## @name Utilities
    # @{

    def _sighandler_term(self, signum, frame, dt):
        """Handle termination of the main thread"""
        self.log().info("Process interrupted - please wait while threads are being stopped ...")
        dt.stop_and_join()

    ## -- End Utilities -- @}

    # -------------------------
    ## @name Subclass Interface
    # @{

    def _check_thread(self, thread):
        """A call to check if the thread is alright, aside from is_alive(), which is done for you.
        You should sleep an interval (done by base) to prevent wasting cycles
        @throw an exception to interrupt the thread"""
        sleep(self.check_period_s)
    
    ## -- End Subclass Interface -- @}

    def setup_argparser(self, parser):
        super(DaemonCommandMixin, self).setup_argparser(parser)

        assert self.ThreadType is not None, "ThreadType must be set in subclass"

        help = "Start ourselves as daemon and write the PID to the given path."
        help += "Fails if the file already exists - we won't check for orphaned files"
        parser.add_argument(*self.pid_file_args, dest='pid_file', type=Path, help=help)

        if self.show_config_args and issubclass(self.ThreadType, ApplicationSettingsMixin):
            help = "Show the daemons effective configuration and exit"
            parser.add_argument(*self.show_config_args, default=False, 
                                    dest='show_config', action='store_true', help=help)
        # end handle commandargs

        return self

    def execute(self, args, remaining_args):
        if getattr(args, 'show_config', None):
            sys.stdout.write("%s.*\n" % self.ThreadType.settings_schema().key())
            sys.stdout.write(str(self.ThreadType.context_value()))
            return self.SUCCESS
        # end handle config printing

        # Whatever happens, make sure we delete the pid file
        if args.pid_file is not None:
            if args.pid_file.isfile():
                self.log().error("PID file at '%s' exists - daemon is already running. Otherwise, delete the file and retry", args.pid_file)
                args.pid_file = None
                return self.ERROR
            # end handle pid file
            daemonize(args.pid_file)
        # end handle daemonization

        prev_signal = signal.signal(signal.SIGTERM, lambda sig, frame: self._sighandler_term(sig, frame, dt))
        try:
            self._thread = dt = self.ThreadType()
            dt.start()

            self.log().info("Running in debug mode - press Ctrl+C to interrupt")
            try:
                # Wait for it to come up
                sleep(self.check_period_s)
                # Thread will run forever, we have to watch for interrupts
                while dt.is_alive():
                    self._check_thread(dt)
                # end wait loop
            except (KeyboardInterrupt, SystemExit):
                self._sighandler_term(15, None, dt)
            except Exception:
                # we raised, make sure thread shuts down
                self._sighandler_term(15, None, dt)
                self.log().error("Unknown exception occurred", exc_info=True)
                return self.ERROR
            else:
                # it terminated ... can have it's reason
                self.log().info("Daemon thread terminated - please see log for details")
                return self.SUCCESS
            # end handle interrupts

            return self.SUCCESS
        finally:
            # restore previous signal, just to assure we don't alter state in tests
            signal.signal(signal.SIGTERM, prev_signal)
            if args.pid_file and args.pid_file.isfile():
                args.pid_file.remove()
            # end remove pid file
        #end handle pid file

    # -------------------------
    ## @name Interface
    # @{

    def thread(self):
        """@return our thread instance. May be None if execute didn't run yet"""
        return getattr(self, '_thread', None)
        
    ## -- End Interface -- @}


# end class DaemonCommandMixin


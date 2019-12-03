import os
import shutil
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Union, List

from distutils.dir_util import copy_tree

from riptide.config.files import path_in_project
from riptide.engine.results import StartStopResultStep, MultiResultQueue


RIPTIDE_HOST_HOSTNAME = "host.riptide.internal"  # the engine has to make the host reachable under this hostname


class ExecError(BaseException):
    pass


class AbstractEngine(ABC):
    @abstractmethod
    def start_project(self,
                      project: 'Project',
                      services: List[str],
                      unimportant_paths_unsynced=False) -> MultiResultQueue[StartStopResultStep]:
        """
        Starts all services in the project.

        All containers started for a project must be in the same isolated container network and service
        containers must be reachable by name as hostname. In addition the services started must also be added
        to the container networks of all projects within the 'links' list of the project.

        The container must also have all hostnames returned by riptide.config.hosts.get_localhost_hosts()
        routable to the host system.

        :type project: 'Project'
        :param services: Names of the services to start
        :param unimportant_paths_unsynced: If True, the engine should mount
                                           unimportant_paths defined in the
                                           project so, that changes in the
                                           container are not stored on the host.
                                           Only applicable for services with role 'src'.
        :return: MultiResultQueue[StartResult]
        """
        pass

    @abstractmethod
    def stop_project(self, project: 'Project', services: List[str]) -> MultiResultQueue[StartStopResultStep]:
        """
        Stops all services in the project

        :type project: 'Project'
        :param services: Names of the services to stop
        :return: MultiResultQueue[StopResult]
        """
        pass

    @abstractmethod
    def status(self, project: 'Project', system_config: 'Config') -> Dict[str, bool]:
        """
        Returns the status for the given project (whether services are started or not)

        :param system_config: Main system config
        :param project: 'Project'
        :return: Dict[str, bool]
        """
        pass

    @abstractmethod
    def service_status(self, project: 'Project', service_name: str, system_config: 'Config') -> bool:
        """
        Returns the status for a single service in a given project (whether service is started or not)

        :param system_config: Main system config
        :param project: 'Project'
        :param service_name: str
        :return: bool
        """
        pass

    @abstractmethod
    def container_name_for(self, project: 'Project', service_name: str) -> str:
        """
        Returns the container name for the given service or whatever is the equivalent.

        :param project: 'Project'
        :param service_name: str
        :return: bool
        """
        pass

    @abstractmethod
    def address_for(self, project: 'Project', service_name: str) -> Union[None, Tuple[str, int]]:
        """
        Returns the ip address and port of the host providing the service for project.

        :param project: 'Project'
        :param service_name: str
        :return: Tuple[str, int]
        """
        pass

    @abstractmethod
    def cmd(self,
            project: 'Project',
            command_name: str,
            arguments: List[str],
            unimportant_paths_unsynced=False) -> int:
        """
        Execute the command identified by command_name in the project environment and
        attach command to stdout/stdin/stderr.
        Returns when the command is finished. Returns the command exit code.

        All containers started for a project must be in the same isolated container network and service
        containers must be reachable by name as hostname. In addition the command started must also be added
        to the container networks of all projects within the 'links' list of the project.

        The container must also have all hostnames returned by riptide.config.hosts.get_localhost_hosts()
        routable to the host system.

        The command must be a "normal" command. "In service" commands may be run with
        cmd_in_service.

        :param project: 'Project'
        :param command_name: str
        :param arguments: List of arguments
        :param unimportant_paths_unsynced: If True, the engine should mount
                                           unimportant_paths defined in the
                                           project so, that changes in the
                                           container are not stored on the host.
        :return: exit code
        """

    @abstractmethod
    def cmd_in_service(self,
                       project: 'Project',
                       command_name: str,
                       service_name: str,
                       arguments: List[str]) -> int:
        """
        Execute the command identified by command_name in the service container identified
        by service_name and attach command to stdout/stdin/stderr.
        Returns when the command is finished. Returns the command exit code.

        Accepts normal and "in service" style commands and does not validate the defined
        service of the command.

        :param project: 'Project'
        :param command_name: str
        :param service_name: str
        :param arguments: List of arguments
        :return: exit code
        :todo exception type:
        :raises: XyzException: If the service is not running.
        """

    @abstractmethod
    def service_fg(self,
                   project: 'Project',
                   service_name: str,
                   arguments: List[str],
                   unimportant_paths_unsynced=False
    ) -> None:
        """
        Execute a service and attach output to stdout/stdin/stderr.
        Returns when the service container is finished.

        Following service options are ignored:

        * logging.stdout (is false)
        * logging.stderr (is false)
        * pre_start (is empty)
        * post_start (is empty)
        * roles.src (is set)
        * working_directory (is set to current working directory)

        :param project: 'Project'
        :param service_name: str
        :param arguments: List of arguments
        :param unimportant_paths_unsynced: If True, the engine should mount
                                           unimportant_paths defined in the
                                           project so, that changes in the
                                           container are not stored on the host.
        :return:
        """

    @abstractmethod
    def cmd_detached(self, project: 'Project', command: 'Command', run_as_root=False) -> (int, str):
        """
        Execute the command in the project environment and
        return the exit code (int), stdout/stderr of the command (str).
        Src/Current working directory is not mounted.
        Returns when finished.

        All containers started for a project must be in the same isolated container network and service
        containers must be reachable by name as hostname. In addition the command started must also be added
        to the container networks of all projects within the 'links' list of the project.

        The container must also have all hostnames returned by riptide.config.hosts.get_localhost_hosts()
        routable to the host system.

        :param run_as_root: Force execution of the command container with the highest possible permissions
        :param project: 'Project'
        :param command: Command Command to run. May not be part of the passed project object but must be treated as such.
        :return:
        """

    @abstractmethod
    def exec(self, project: 'Project', service_name: str, cols=None, lines=None, root=False) -> None:
        """
        Open an interactive shell into service_name and attach stdout/stdin/stderr.
        Returns when the shell is exited.

        :param root: If true, run as root user instead of current shell user
        :param lines: Number of lines in the terminal, optional
        :param cols: Number of columns in the terminal, optional
        :param project: 'Project'
        :param service_name: str
        :return:
        """
        pass

    @abstractmethod
    def exec_custom(self, project: 'Project', service_name: str, command: str, cols=None, lines=None, root=False) -> None:
        """
        Run a custom command in service service_name and attach stdout/stdin/stderr.
        Returns when the command is exited.

        Commands in the server container are execute using a sh shell.

        :param root: If true, run as root user instead of current shell user
        :param command: The command string to execute.
        :param lines: Number of lines in the terminal, optional
        :param cols: Number of columns in the terminal, optional
        :param project: 'Project'
        :param service_name: str
        :return:
        """
        pass

    @abstractmethod
    def pull_images(self, project: 'Project', line_reset='\n', update_func=lambda msg: None) -> None:
        """
        Pull new versions of images for commands and services described in project.

        Not fining an image should NOT raise an error and instead print a warning as status report.

        :param project:     The project to pull all images for. Applies to all commands and services in project.

        :param line_reset:  Characters that represent a line reset for the current terminal.

        :param update_func: Function to send status updates to.
                            Resetting the line via the provided parameter is allowed.
                            Calling it does NOT add new lines (\\n).
                            End result should be looking like this::

                                [service/service1] Pulling 'image/name':
                                    Status report... Can use carriage return here.
                                [service/service2] Pulling 'image/name':
                                    Status report... Can use carriage return here.
                                [command/command1] Pulling 'image/name':
                                    Warning: Image not found in repository.

                                Done.
        """
        pass

    def path_rm(self, path, project: 'Project'):
        """
        Delete a path. Default is using python builtin functions.
        PATH MUST BE WITHIN PROJECT.

        path was created using an engine service or command.
        If paths created with this engine may not be writable with the user calling riptide,
        override this method to remove the folder using elevated rights (eg. running a Docker container as root).

        Returns without an exception if the path was moved (or didn't exist).
        """
        if not path_in_project(path, project):
            raise PermissionError(f"Tried to delete a file/directory that is not within the project: {path}")
        if os.path.isfile(path):
            os.remove(path)
        else:
            shutil.rmtree(path)

    def path_copy(self, fromm, to, project: 'Project'):
        """
        Copy a path. Default is using python builtin functions. 'to' may not exist already.
        TO PATH MUST BE WITHIN PROJECT.

        See notes at path_rm
        Returns without an exception if the path was copied.
        """
        if not path_in_project(to, project):
            raise PermissionError(f"Tried to copy into a path that is not within the project: {fromm} -> {to}")
        if os.path.isfile(fromm):
            shutil.copy2(fromm, to)
        else:
            copy_tree(fromm, to)

    @abstractmethod
    def performance_value_for_auto(self, key: str, platform: str) -> bool:
        """
        Whether or not performance optimization for the provided key
        should be activated for the provided platform, because they
        drastically increase performance.

        :param key: Optimization key, as found in the Config schema's "performance" entry.
        :param platform: windows/mac/linux/unknown.
        """
        pass

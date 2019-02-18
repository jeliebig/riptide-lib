import os
import requests
import stat

from riptide.lib.cross_platform import cpuser
from riptide.tests.integration.project_loader import load
from riptide.tests.integration.testcase_engine import EngineTest


class EngineServiceTest(EngineTest):

    # without src is implicitly tested via EngineStartStopTest.test_simple_result
    def test_with_src(self):
        for project_ctx in load(self,
                                ['integration_all.yml'],
                                ['.', 'src']):
            with project_ctx as loaded:
                project = loaded.config["project"]
                service_name = "simple_with_src"

                # Put a index.html file into the root of the project folder and one in the src folder, depending on
                # what src we are testing right now, we will expect a different file to be served.
                index_file_in_dot = b'hello dot\n'
                index_file_in_src = b'hello src\n'

                with open(os.path.join(loaded.temp_dir, 'index.html'), 'wb') as f:
                    f.write(index_file_in_dot)
                os.makedirs(os.path.join(loaded.temp_dir, 'src'))
                with open(os.path.join(loaded.temp_dir, 'src', 'index.html'), 'wb') as f:
                    f.write(index_file_in_src)

                # START
                self.run_start_test(loaded.engine, project, [service_name], loaded.engine_tester)

                # Check response
                if loaded.src == '.':
                    self.assert_response(index_file_in_dot, loaded.engine, project, service_name)
                elif loaded.src == 'src':
                    self.assert_response(index_file_in_src, loaded.engine, project, service_name)
                else:
                    AssertionError('Error in test: Unexpected src')

                # Check permissions
                user, group, mode = loaded.engine_tester.get_permissions_at('.', loaded.engine, project,
                                                                            project["app"]["services"][service_name])

                # we use the cpuser module so this technically also works on windows because the cpuser module returns 0
                # and Docker mounts for root.
                self.assertEqual(cpuser.getuid(), user, 'The current user needs to own the src volumes')
                self.assertEqual(cpuser.getgid(), group, 'The current group needs to be the group of the src volumes')
                self.assertTrue(bool(mode & stat.S_IRUSR), 'The src volume must be readable by owner')
                self.assertTrue(bool(mode & stat.S_IWUSR), 'The src volume must be writable by owner')

                # STOP
                self.run_stop_test(loaded.engine, project, [service_name], loaded.engine_tester)

    def test_custom_command(self):
        for project_ctx in load(self,
                                ['integration_all.yml'],
                                ['.']):
            with project_ctx as loaded:
                project = loaded.config["project"]
                service_name = "custom_command"

                # START
                self.run_start_test(loaded.engine, project, [service_name], loaded.engine_tester)

                # Check response
                # The custom command disables auto-index of http-server so we should get a directory
                # listing instead
                self.assert_response_matches_regex('<title>Index of /</title>', loaded.engine, project, service_name)

                # STOP
                self.run_stop_test(loaded.engine, project, [service_name], loaded.engine_tester)

    def test_environment(self):
        for project_ctx in load(self,
                                ['integration_all.yml'],
                                ['.']):
            with project_ctx as loaded:
                engine = loaded.engine
                project = loaded.config["project"]
                service_name = "env"
                service = loaded.config["project"]["app"]["services"][service_name]

                # START
                self.run_start_test(loaded.engine, project, [service_name], loaded.engine_tester)

                self.assertEqual('TEST_ENV_VALUE', loaded.engine_tester.get_env('TEST_ENV_KEY',
                                                                                engine, project, service))
                self.assertIsNone(loaded.engine_tester.get_env('TEST_ENV_DOES_NOT_EXIST',
                                                               engine, project, service))

                # STOP
                self.run_stop_test(loaded.engine, project, [service_name], loaded.engine_tester)

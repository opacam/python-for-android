import os

import unittest

try:
    from unittest import mock
except ImportError:
    # Python 2 does not have the `unittest.mock` module built-in
    import mock
from pythonforandroid.bootstrap import Bootstrap
from pythonforandroid.distribution import Distribution
from pythonforandroid.recipe import Recipe
from pythonforandroid.archs import ArchARMv7_a
from pythonforandroid.build import Context
from pythonforandroid.logger import info


class TestBootstrap(unittest.TestCase):
    def setUp(self):
        self.ctx = Context()
        self.ctx.ndk_api = 21
        self.ctx.android_api = 27
        self.ctx._sdk_dir = "/opt/android/android-sdk"
        self.ctx._ndk_dir = "/opt/android/android-ndk"
        self.ctx.setup_dirs(os.getcwd())
        self.ctx.recipe_build_order = [
            "hostpython3",
            "python3",
            "sdl2",
            "kivy",
        ]

    def test_bootstrap_basic_properties(self):
        bs = Bootstrap().get_bootstrap("sdl2", self.ctx)
        self.assertEqual(bs.name, "sdl2")
        self.assertEqual(bs.jni_dir, "sdl2/jni")
        self.assertEqual(bs.get_build_dir_name(), "sdl2-python3")

        # test dist_dir error (fails on travis, variables not reseated)
        # with self.assertRaises(SystemExit) as e:
        #     bs.dist_dir
        # self.assertEqual(e.exception.args[0], 1)

        # test dist_dir success
        self.ctx.bootstrap = bs
        self.ctx.bootstrap.distribution = Distribution.get_distribution(
            self.ctx, name="test_prj", recipes=["python3", "kivy"]
        )
        self.assertTrue(bs.dist_dir.endswith("dists/test_prj"))

    def test_bootstrap_gets(self):
        bs = Bootstrap().get_bootstrap("sdl2", self.ctx)

        self.assertTrue(
            bs.get_build_dir().endswith("build/bootstrap_builds/sdl2-python3")
        )
        self.assertTrue(bs.get_dist_dir("test_prj").endswith("dists/test_prj"))
        self.assertTrue(
            bs.get_common_dir().endswith("pythonforandroid/bootstraps/common")
        )

    def test_get_bootstraps(self):
        bootstraps = {"empty", "service_only", "webview", "sdl2"}
        for bs_name in Bootstrap().list_bootstraps():
            self.assertIn(bs_name, bootstraps)

    def test_get_bootstraps_from_recipes(self):
        recipes_service = {"pyjnius", "python3"}
        bs = Bootstrap().get_bootstrap_from_recipes(recipes_service, self.ctx)
        self.assertEqual(bs.name, "service_only")

        # test wrong recipes
        wrong_recipes = {"python2", "python3", "pyjnius"}
        bs = Bootstrap().get_bootstrap_from_recipes(wrong_recipes, self.ctx)
        self.assertIsNone(bs)

    @mock.patch("pythonforandroid.bootstrap.shprint")
    @mock.patch("pythonforandroid.bootstrap.sh.cp")
    @mock.patch("pythonforandroid.bootstrap.glob.glob")
    @mock.patch("pythonforandroid.bootstrap.ensure_dir")
    @mock.patch("pythonforandroid.build.ensure_dir")
    def test_bootstrap_distribute(
        self, mock_build_dir, mock_bs_dir, mock_glob, mock_sh_cp, mock_shprint
    ):
        mock_build_dir.return_value = True
        mock_bs_dir.return_value = True
        mock_sh_cp.return_value = True
        mock_shprint.return_value = True
        # prepare bootstrap, context and distribution to perform the tests
        bs = Bootstrap().get_bootstrap("sdl2", self.ctx)
        arch = ArchARMv7_a(self.ctx)
        self.ctx.bootstrap = bs
        self.ctx.bootstrap.distribution = Distribution.get_distribution(
            self.ctx, name="test_prj", recipes=["python3", "kivy"]
        )
        # test that distribute methods runs with a basic distribution
        mock_glob.return_value = [
            "/fake_dir/libsqlite3.so",
            "/fake_dir/libpng16.so",
        ]
        bs.distribute_libs(arch, [self.ctx.get_libs_dir(arch.arch)])
        bs.distribute_javaclasses(self.ctx.javaclass_dir)
        bs.distribute_aars(arch)

    @mock.patch("pythonforandroid.bootstrap.shprint")
    @mock.patch("pythonforandroid.bootstrap.sh.Command")
    @mock.patch("pythonforandroid.build.ensure_dir")
    @mock.patch("pythonforandroid.archs.find_executable")
    @mock.patch("pythonforandroid.bootstrap.sh.find")
    def test_bootstrap_strip(
        self,
        mock_sh_find,
        mock_find_executable,
        mock_ensure_dir,
        mock_sh_command,
        mock_sh_print,
    ):
        mock_sh_find.return_value = [
            "/fake_dir/libsqlite3.so",
            "/fake_dir/libpng16.so",
        ]
        mock_find_executable.return_value = "arm-linux-androideabi-gcc"
        mock_ensure_dir.return_value = True
        mock_sh_command.return_value = mock.Mock()
        # the bake command is supposed to run the desired command, we replace
        # it some fake bake function so we make sure that we succeed and the
        # test go on)

        def bake(*args):
            def fake_run(*args, **kwars):
                info(
                    "Command strip with args {} and kwargs {}"
                    "\nSuccessfully mocked".format(args, kwars)
                )

            return fake_run

        mock_sh_command.return_value.bake = bake

        mock_sh_print.return_value = mock.Mock()
        mock_sh_print.return_value.stdout = (
            "/fake_dir/libsqlite3.so"
            "\n/fake_dir/libpng16.so\n".encode("ascii")
        )
        # prepare bootstrap, context and distribution to perform the tests
        bs = Bootstrap().get_bootstrap("sdl2", self.ctx)
        arch = ArchARMv7_a(self.ctx)
        self.ctx.bootstrap = bs
        self.ctx.python_recipe = Recipe.get_recipe("python3", self.ctx)
        self.ctx.bootstrap.distribution = Distribution.get_distribution(
            self.ctx, name="test_prj", recipes=["python3", "kivy"]
        )
        # test that strip_libraries runs with a fake distribution
        bs.strip_libraries(arch)

    @mock.patch("pythonforandroid.bootstrap.listdir")
    @mock.patch("pythonforandroid.bootstrap.sh.rm")
    @mock.patch("pythonforandroid.bootstrap.sh.mv")
    @mock.patch("pythonforandroid.bootstrap.isdir")
    def test_bootstrap_fry_eggs(
        self, mock_isdir, mock_sh_mv, mock_sh_rm, mock_listdir
    ):
        mock_isdir.return_value = True
        mock_sh_mv.return_value = "sh.mv successfully mocked"
        mock_sh_rm.return_value = "sh.rm successfully mocked"
        mock_listdir.return_value = [
            "jnius",
            "kivy",
            "Kivy-1.11.0.dev0-py3.7.egg-info",
            "pyjnius-1.2.1.dev0-py3.7.egg",
        ]

        # prepare bootstrap, context and distribution to perform the tests
        bs = Bootstrap().get_bootstrap("sdl2", self.ctx)
        self.ctx.bootstrap = bs

        # test that fry_eggs runs with a fake distribution
        site_packages = os.path.join(
            bs.dist_dir, "_python_bundle", "_python_bundle"
        )
        bs.fry_eggs(site_packages)

    @mock.patch("pythonforandroid.bootstrap.open", create=True)
    @mock.patch("pythonforandroid.util.chdir")
    @mock.patch("pythonforandroid.bootstrap.shutil.copy")
    @mock.patch("pythonforandroid.bootstrap.os.makedirs")
    @mock.patch("pythonforandroid.bootstrap.sh.ln")
    @mock.patch("pythonforandroid.bootstrap.listdir")
    @mock.patch("pythonforandroid.bootstrap.sh.mkdir")
    @mock.patch("pythonforandroid.bootstrap.sh.rm")
    @mock.patch("pythonforandroid.bootstrap.isdir")
    def test_bootstrap_prepare_build_dir(
        self,
        mock_isdir,
        mock_sh_rm,
        mock_sh_mkdir,
        mock_listdir,
        mock_sh_ln,
        mock_os_makedirs,
        mock_shutil_copy,
        mock_chdir,
        mock_open,
    ):
        mock_isdir.return_value = True
        mock_sh_mkdir.return_value = "sh.mkdir successfully mocked"
        mock_sh_rm.return_value = "sh.rm successfully mocked"
        mock_listdir.return_value = [
            "jnius",
            "kivy",
            "Kivy-1.11.0.dev0-py3.7.egg-info",
            "pyjnius-1.2.1.dev0-py3.7.egg",
        ]
        mock_sh_ln.return_value = True
        mock_os_makedirs.return_value = True
        mock_shutil_copy.return_value = True
        mock_chdir.return_value = True

        mock_open.side_effect = [
            mock.mock_open(read_data="target=android-21").return_value,
        ]

        # prepare bootstrap, context and distribution to perform the tests
        bs = Bootstrap().get_bootstrap("sdl2", self.ctx)
        self.ctx.bootstrap = bs

        bs.prepare_build_dir()
        # make sure that the open command has been called only once
        mock_open.assert_called_once_with("project.properties", "w")
        mock_open.reset_mock()

import os
import types
import unittest
import warnings
from pythonforandroid.build import Context
from pythonforandroid.recipe import Recipe, import_recipe
from pythonforandroid.archs import ArchAarch_64
from pythonforandroid.bootstrap import Bootstrap
from test_bootstrap import BaseClassSetupBootstrap

try:
    from unittest import mock
except ImportError:
    # `Python 2` or lower than `Python 3.3` does not
    # have the `unittest.mock` module built-in
    import mock


class TestRecipe(unittest.TestCase):
    def test_recipe_dirs(self):
        """
        Trivial `recipe_dirs()` test.
        Makes sure the list is not empty and has the root directory.
        """
        ctx = Context()
        recipes_dir = Recipe.recipe_dirs(ctx)
        # by default only the root dir `recipes` directory
        self.assertEqual(len(recipes_dir), 1)
        self.assertTrue(recipes_dir[0].startswith(ctx.root_dir))

    def test_list_recipes(self):
        """
        Trivial test verifying list_recipes returns a generator with some
        recipes.
        """
        ctx = Context()
        recipes = Recipe.list_recipes(ctx)
        self.assertTrue(isinstance(recipes, types.GeneratorType))
        recipes = list(recipes)
        self.assertIn('python3', recipes)

    def test_get_recipe(self):
        """
        Makes sure `get_recipe()` returns a `Recipe` object when possible.
        """
        ctx = Context()
        recipe_name = 'python3'
        recipe = Recipe.get_recipe(recipe_name, ctx)
        self.assertTrue(isinstance(recipe, Recipe))
        self.assertEqual(recipe.name, recipe_name)
        recipe_name = 'does_not_exist'
        with self.assertRaises(ValueError) as e:
            Recipe.get_recipe(recipe_name, ctx)
        self.assertEqual(
            e.exception.args[0], 'Recipe does not exist: {}'.format(recipe_name))

    def test_import_recipe(self):
        """
        Verifies we can dynamically import a recipe without warnings.
        """
        p4a_root_dir = os.path.dirname(os.path.dirname(__file__))
        name = 'pythonforandroid.recipes.python3'
        pathname = os.path.join(
            *([p4a_root_dir] + name.split('.') + ['__init__.py'])
        )
        with warnings.catch_warnings(record=True) as recorded_warnings:
            warnings.simplefilter("always")
            module = import_recipe(name, pathname)
        assert module is not None
        assert recorded_warnings == []


class TestLibraryRecipe(BaseClassSetupBootstrap, unittest.TestCase):
    def setUp(self):
        """
        Initialize a Context with a Bootstrap and a Distribution to properly
        test an library recipe, to do so we reuse `BaseClassSetupBootstrap`
        """
        super(TestLibraryRecipe, self).setUp()
        self.ctx.bootstrap = Bootstrap().get_bootstrap('sdl2', self.ctx)
        self.setUp_distribution_with_bootstrap(self.ctx.bootstrap)

    def test_built_libraries(self):
        """The openssl recipe is a library recipe, so it should have set the
        attribute `built_libraries`, but not the case of `pyopenssl` recipe.
        """
        recipe = Recipe.get_recipe('openssl', self.ctx)
        self.assertTrue(recipe.built_libraries)

        recipe = Recipe.get_recipe('pyopenssl', self.ctx)
        self.assertFalse(recipe.built_libraries)

    @mock.patch('pythonforandroid.recipe.exists')
    def test_should_build(self, mock_exists):
        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('openssl', self.ctx)
        recipe.ctx = self.ctx
        self.assertFalse(recipe.should_build(arch))

        mock_exists.return_value = False
        self.assertTrue(recipe.should_build(arch))

    @mock.patch('pythonforandroid.recipe.Recipe.get_libraries')
    @mock.patch('pythonforandroid.recipe.Recipe.install_libs')
    def test_do_install_libs(self, mock_install_libs, mock_get_libraries):
        mock_get_libraries.return_value = {
            '/build_lib/libsample1.so',
            '/build_lib/libsample2.so',
        }
        self.ctx.recipe_build_order = [
            "hostpython3",
            "openssl",
            "python3",
            "sdl2",
            "kivy",
        ]
        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('openssl', self.ctx)
        recipe.do_install_libs(arch)
        mock_install_libs.assert_called_once_with(
            arch, *mock_get_libraries.return_value
        )


class TesSTLRecipe(BaseClassSetupBootstrap, unittest.TestCase):
    def setUp(self):
        """
        Initialize a Context with a Bootstrap and a Distribution to properly
        test a recipe which depends on android's STL library, to do so we reuse
        `BaseClassSetupBootstrap`
        """
        super(TesSTLRecipe, self).setUp()
        self.ctx.bootstrap = Bootstrap().get_bootstrap('sdl2', self.ctx)
        self.setUp_distribution_with_bootstrap(self.ctx.bootstrap)
        self.ctx.python_recipe = Recipe.get_recipe('python3', self.ctx)

    def test_get_stl_lib_dir(self):
        """
        Test that :meth:`~pythonforandroid.recipe.STLRecipe.get_stl_lib_dir`
        returns the expected path for the stl library
        """
        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        self.assertTrue(recipe.need_stl_shared)
        self.assertEqual(
            recipe.get_stl_lib_dir(arch),
            os.path.join(
                self.ctx.ndk_dir,
                'sources/cxx-stl/llvm-libc++/libs/{arch}'.format(
                    arch=arch.arch
                ),
            ),
        )

    @mock.patch('pythonforandroid.archs.find_executable')
    @mock.patch('pythonforandroid.build.ensure_dir')
    def test_get_recipe_env_with(
        self, mock_ensure_dir, mock_find_executable
    ):
        """
        Test that :meth:`~pythonforandroid.recipe.STLRecipe.get_recipe_env`
        returns some expected keys and values.

        .. note:: We don't check all the env variables, only those one specific
                  of :class:`~pythonforandroid.recipe.STLRecipe`, the others
                  should be tested in the proper test.
        """
        expected_compiler = 'aarch64-linux-android-gcc'
        mock_find_executable.return_value = expected_compiler
        mock_ensure_dir.return_value = True

        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        assert recipe.need_stl_shared, True
        env = recipe.get_recipe_env(arch)
        # check `find_executable` calls
        mock_find_executable.assert_called_once_with(
            expected_compiler, path=os.environ['PATH']
        )
        self.assertIsInstance(env, dict)

        # check `CPPFLAGS`
        expected_cppflags = {
            '-I{stl_include}'.format(stl_include=recipe.stl_include_dir)
        }
        self.assertIn('CPPFLAGS', env)
        for flags in expected_cppflags:
            self.assertIn(flags, env['CPPFLAGS'])

        # check `LIBS`
        self.assertIn('LDFLAGS', env)
        self.assertIn('-L' + recipe.get_stl_lib_dir(arch), env['LDFLAGS'])
        self.assertIn('LIBS', env)
        self.assertIn('-lc++_shared', env['LIBS'])

        # check `CXXFLAGS` and `CXX`
        for flag in {'CXXFLAGS', 'CXX'}:
            self.assertIn(flag, env)
            self.assertIn('-frtti -fexceptions', env[flag])

    @mock.patch('pythonforandroid.recipe.Recipe.install_libs')
    @mock.patch('pythonforandroid.recipe.isfile')
    @mock.patch('pythonforandroid.build.ensure_dir')
    def test_install_stl_lib(
        self, mock_ensure_dir, mock_isfile, mock_install_lib
    ):
        """
        Test that :meth:`~pythonforandroid.recipe.STLRecipe.install_stl_lib`,
        calls the method :meth:`~pythonforandroid.recipe.Recipe.install_libs`
        with the proper arguments: a subclass of
        :class:`~pythonforandroid.archs.Arch` and our stl lib
        (:attr:`~pythonforandroid.recipe.STLRecipe.stl_lib_name`)
        """
        mock_ensure_dir.return_value = True
        mock_isfile.return_value = False
        mock_install_lib.return_value = True

        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        recipe.ctx = self.ctx
        assert recipe.need_stl_shared, True
        recipe.install_stl_lib(arch)
        mock_install_lib.assert_called_once_with(
            arch,
            '{ndk_dir}/sources/cxx-stl/llvm-libc++/'
            'libs/{arch}/lib{stl_lib}.so'.format(
                ndk_dir=self.ctx.ndk_dir,
                arch=arch.arch,
                stl_lib=recipe.stl_lib_name,
            ),
        )

    @mock.patch('pythonforandroid.recipe.Recipe.install_stl_lib')
    def test_postarch_build(self, mock_install_stl_lib):
        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        assert recipe.need_stl_shared, True
        recipe.postbuild_arch(arch)
        mock_install_stl_lib.assert_called_once_with(arch)

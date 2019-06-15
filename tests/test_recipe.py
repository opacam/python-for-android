import os
import types
import unittest
import warnings
from pythonforandroid.build import Context
from pythonforandroid.recipe import Recipe, StlRecipe, import_recipe
from pythonforandroid.archs import ArchAarch_64
from pythonforandroid.bootstrap import Bootstrap
from pythonforandroid.distribution import Distribution

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


class TestStlRecipe(unittest.TestCase):
    def setUp(self):
        """
        Initialize a Context with a Bootstrap and a Distribution to properly
        test :class:`~pythonforandroid.recipe.StlRecipe`
        """
        self.ctx = Context()
        self.ctx.ndk_api = 21
        self.ctx.android_api = 27
        self.ctx._sdk_dir = '/opt/android/android-sdk'
        self.ctx._ndk_dir = '/opt/android/android-ndk'
        self.ctx.setup_dirs(os.getcwd())
        self.ctx.bootstrap = Bootstrap().get_bootstrap('sdl2', self.ctx)
        self.ctx.bootstrap.distribution = Distribution.get_distribution(
            self.ctx, name='sdl2', recipes=['python3', 'kivy']
        )
        self.ctx.python_recipe = Recipe.get_recipe('python3', self.ctx)

    def test_get_stl_lib_dir(self):
        """
        Test that :meth:`~pythonforandroid.recipe.StlRecipe.get_stl_lib_dir`
        returns the expected path for the stl library
        """
        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        self.assertIsInstance(recipe, StlRecipe)
        self.assertEqual(
            recipe.get_stl_lib_dir(arch),
            os.path.join(
                self.ctx.ndk_dir,
                'sources/cxx-stl/llvm-libc++/libs/{arch}'.format(
                    arch=arch.arch
                ),
            ),
        )

    @mock.patch('pythonforandroid.archs.glob')
    @mock.patch('pythonforandroid.archs.find_executable')
    @mock.patch('pythonforandroid.build.ensure_dir')
    def test_get_recipe_env(
        self, mock_ensure_dir, mock_find_executable, mock_glob
    ):
        """
        Test that :meth:`~pythonforandroid.recipe.StlRecipe.get_recipe_env`
        returns some expected keys and values.

        .. note:: We don't check all the env variables, only those one specific
                  of :class:`~pythonforandroid.recipe.StlRecipe`, the others
                  should be tested in the proper test.
        """
        expected_compiler = (
            '/opt/android/android-ndk/toolchains/'
            'llvm/prebuilt/linux-x86_64/bin/clang'
        )
        mock_find_executable.return_value = expected_compiler
        mock_ensure_dir.return_value = True
        mock_glob.return_value = ['llvm']

        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        self.assertIsInstance(recipe, StlRecipe)
        env = recipe.get_recipe_env(arch)
        # check `glob` and `find_executable` calls
        self.assertEqual(mock_glob.call_count, 4)
        for glob_call, kw in mock_glob.call_args_list:
            self.assertEqual(
                glob_call[0],
                "{ndk_dir}/toolchains/llvm*".format(ndk_dir=self.ctx._ndk_dir),
            )
        mock_find_executable.assert_called_once_with(
            expected_compiler, path=os.environ['PATH']
        )
        self.assertIsInstance(env, dict)

        # check `CPPFLAGS`
        self.assertIn('CPPFLAGS', env)
        self.assertIn('-DANDROID -D__ANDROID_API__=21', env['CPPFLAGS'])

        expected_includes = {
            os.path.join(
                self.ctx.ndk_dir, 'sources/cxx-stl/llvm-libc++/include'
            )
        }
        for include in expected_includes:
            self.assertIn(include, env['CPPFLAGS'])

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
        Test that :meth:`~pythonforandroid.recipe.StlRecipe.install_stl_lib`,
        calls the method :meth:`~pythonforandroid.recipe.Recipe.install_libs`
        with the proper arguments: a subclass of
        :class:`~pythonforandroid.archs.Arch` and our stl lib
        (:attr:`~pythonforandroid.recipe.StlRecipe.stl_lib_name`)
        """
        mock_ensure_dir.return_value = True
        mock_isfile.return_value = False
        mock_install_lib.return_value = True

        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        self.assertIsInstance(recipe, StlRecipe)
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

    @mock.patch('pythonforandroid.recipe.StlRecipe.install_stl_lib')
    def test_postarch_build(self, mock_install_stl_lib):
        arch = ArchAarch_64(self.ctx)
        recipe = Recipe.get_recipe('icu', self.ctx)
        recipe.postbuild_arch(arch)
        mock_install_stl_lib.assert_called_once_with(arch)

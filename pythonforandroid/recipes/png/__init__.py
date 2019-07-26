from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
from multiprocessing import cpu_count
from os.path import join
import sh


class PngRecipe(Recipe):
    name = 'png'
    version = 'v1.6.37'
    url = 'https://github.com/glennrp/libpng/archive/{version}.zip'
    built_libraries = {'libpng16.so': '.libs'}

    def get_recipe_env(self, arch=None):
        env = super(PngRecipe, self).get_recipe_env(arch)
        ndk_lib_dir = join(self.ctx.ndk_platform, 'usr', 'lib')
        ndk_include_dir = join(self.ctx.ndk_dir, 'sysroot', 'usr', 'include')
        env['CFLAGS'] += ' -I{}'.format(ndk_include_dir)
        env['LDFLAGS'] += ' -L{}'.format(ndk_lib_dir)
        env['LDFLAGS'] += ' --sysroot={}'.format(self.ctx.ndk_platform)
        return env

    def do_build_libs(self, arch):
        build_dir = self.get_build_dir(arch.arch)
        with current_directory(build_dir):
            env = self.get_recipe_env(arch)
            build_arch = (
                shprint(sh.gcc, '-dumpmachine')
                .stdout.decode('utf-8')
                .split('\n')[0]
            )
            shprint(
                sh.Command('./configure'),
                '--build=' + build_arch,
                '--host=' + arch.command_prefix,
                '--target=' + arch.command_prefix,
                '--disable-static',
                '--enable-shared',
                '--prefix={}/install'.format(self.get_build_dir(arch.arch)),
                _env=env,
            )
            shprint(sh.make, '-j', str(cpu_count()), _env=env)


recipe = PngRecipe()

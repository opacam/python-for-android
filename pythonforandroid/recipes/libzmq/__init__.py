from pythonforandroid.recipe import StlRecipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
from os.path import exists, join
import sh


class LibZMQRecipe(StlRecipe):
    version = '4.3.1'
    url = 'https://github.com/zeromq/libzmq/releases/download/v{version}/zeromq-{version}.zip'
    depends = []

    def should_build(self, arch):
        super(LibZMQRecipe, self).should_build(arch)
        return not exists(join(self.ctx.get_libs_dir(arch.arch), 'libzmq.so'))

    def build_arch(self, arch):
        super(LibZMQRecipe, self).build_arch(arch)
        env = self.get_recipe_env(arch)

        curdir = self.get_build_dir(arch.arch)
        prefix = join(curdir, "install")
        with current_directory(curdir):
            bash = sh.Command('sh')
            shprint(
                bash, './configure',
                '--host={}'.format(arch.command_prefix),
                '--without-documentation',
                '--prefix={}'.format(prefix),
                '--with-libsodium=no',
                _env=env)
            shprint(sh.make, _env=env)
            shprint(sh.make, 'install', _env=env)
            self.install_libs(arch, 'src/.libs/libzmq.so')

    def get_include_dirs(self, arch):
        return [join(self.get_build_dir(arch.arch), 'include')]


recipe = LibZMQRecipe()

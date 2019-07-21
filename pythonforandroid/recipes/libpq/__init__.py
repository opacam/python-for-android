from pythonforandroid.toolchain import Recipe, current_directory, shprint
import sh


class LibpqRecipe(Recipe):
    version = '9.5.3'
    url = 'http://ftp.postgresql.org/pub/source/v{version}/postgresql-{version}.tar.bz2'
    built_libraries = {'libpq.a': 'src/interfaces/libpq'}
    depends = []

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)

        with current_directory(self.get_build_dir(arch.arch)):
            configure = sh.Command('./configure')
            shprint(configure, '--without-readline', '--host=arm-linux',
                    _env=env)
            shprint(sh.make, 'submake-libpq', _env=env)
            shprint(sh.cp, '-a', 'src/interfaces/libpq/libpq.a',
                    self.ctx.get_libs_dir(arch.arch))


recipe = LibpqRecipe()

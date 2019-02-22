import sh
import os
from glob import glob
from os.path import join, isdir, exists
from pythonforandroid.recipe import StlRecipe, NDKRecipe
from pythonforandroid.toolchain import shprint
from pythonforandroid.util import current_directory, ensure_dir


class ICURecipe(StlRecipe, NDKRecipe):
    name = 'icu4c'
    version = '57.1'
    url = ('http://download.icu-project.org/files/icu4c/'
           '{version}/icu4c-{version_underscore}-src.tgz')

    depends = [('hostpython2', 'hostpython3')]  # installs in python
    patches = ['disable-libs-version.patch']
    libs_names = ['icui18n', 'icuuc', 'icudata', 'icule',
                  'icuio', 'icutu', 'iculx', 'icutest']

    def __init__(self, *args, **kwargs):
        self.generated_libraries = [
            'lib{name}{version}.so'.format(
                name=name,
                version=self.version.split('.')[0]) for name in self.libs_names
        ]
        super(ICURecipe, self).__init__(*args, **kwargs)

    @property
    def versioned_url(self):
        if self.url is None:
            return None
        return self.url.format(
            version=self.version,
            version_underscore=self.version.replace('.', '_'))

    def get_recipe_dir(self):
        if self.ctx.local_recipes is not None:
            local_recipe_dir = join(self.ctx.local_recipes, 'icu')
            if exists(local_recipe_dir):
                return local_recipe_dir
        return join(self.ctx.root_dir, 'recipes', 'icu')

    def get_lib_dir(self, arch):
        lib_dir = join(self.ctx.get_python_install_dir(), "lib")
        ensure_dir(lib_dir)
        return lib_dir

    def build_arch(self, arch, *extra_args):
        env = self.get_recipe_env(arch).copy()
        build_root = self.get_build_dir(arch.arch)

        def make_build_dest(dest):
            build_dest = join(build_root, dest)
            if not isdir(build_dest):
                ensure_dir(build_dest)
                return build_dest, False

            return build_dest, True

        icu_build = join(build_root, "icu_build")
        build_linux, exists = make_build_dest("build_icu_linux")

        host_env = os.environ.copy()
        # reduce the function set
        host_env["CPPFLAGS"] = (
            "-O3 -fno-short-wchar -DU_USING_ICU_NAMESPACE=1 -fno-short-enums "
            "-DU_HAVE_NL_LANGINFO_CODESET=0 -D__STDC_INT64__ -DU_TIMEZONE=0 "
            "-DUCONFIG_NO_LEGACY_CONVERSION=1 "
            "-DUCONFIG_NO_TRANSLITERATION=0 ")

        if not exists:
            configure = sh.Command(
                join(build_root, "source", "runConfigureICU"))
            with current_directory(build_linux):
                shprint(
                    configure,
                    "Linux",
                    "--prefix="+icu_build,
                    "--enable-extras=no",
                    "--enable-strict=no",
                    "--enable-static=no",
                    "--enable-tests=no",
                    "--enable-samples=no",
                    _env=host_env)
                shprint(sh.make, "-j5", _env=host_env)
                shprint(sh.make, "install", _env=host_env)

        build_android, exists = make_build_dest("build_icu_android")
        if not exists:

            configure = sh.Command(join(build_root, "source", "configure"))

            with current_directory(build_android):
                shprint(
                    configure,
                    "--with-cross-build="+build_linux,
                    "--enable-extras=no",
                    "--enable-strict=no",
                    "--enable-static=no",
                    "--enable-tests=no",
                    "--enable-samples=no",
                    "--host="+env["TOOLCHAIN_PREFIX"],
                    "--prefix="+icu_build,
                    _env=env)
                shprint(sh.make, "-j5", _env=env)
                shprint(sh.make, "install", _env=env)

        self.copy_files(arch)

    def copy_files(self, arch):
        src_lib = join(self.get_build_dir(arch.arch), "icu_build", "lib")
        so_files = glob(join(src_lib, '*.so'))
        for f in so_files:
            final_lib = os.path.split(f)[1]
            shprint(sh.cp, f, join(self.ctx.get_libs_dir(arch.arch),
                                   final_lib))

        src_include = join(
            self.get_build_dir(arch.arch), "icu_build", "include")
        dst_include = join(
            self.ctx.get_python_install_dir(), "include", "icu")
        ensure_dir(dst_include)
        shprint(sh.cp, "-r", join(src_include, "layout"), dst_include)
        shprint(sh.cp, "-r", join(src_include, "unicode"), dst_include)


recipe = ICURecipe()

from pythonforandroid.recipe import CompiledComponentsPythonRecipe
from multiprocessing import cpu_count
from os.path import join


class NumpyRecipe(CompiledComponentsPythonRecipe):

    version = '1.15.1'
    url = 'https://pypi.python.org/packages/source/n/numpy/numpy-{version}.zip'
    site_packages_name = 'numpy'
    depends = [('python2', 'python3', 'python3crystax'), 'setuptools']
    call_hostpython_via_targetpython = False

    patches = [
        join('patches', 'fix-numpy.patch'),
        join('patches', 'lib.patch'),
    ]

    def build_compiled_components(self, arch):
        self.setup_extra_args = ['-j', str(cpu_count())]
        super(NumpyRecipe, self).build_compiled_components(arch)
        self.setup_extra_args = []

    def rebuild_compiled_components(self, arch, env):
        self.setup_extra_args = ['-j', str(cpu_count())]
        super(NumpyRecipe, self).rebuild_compiled_components(arch, env)
        self.setup_extra_args = []


recipe = NumpyRecipe()

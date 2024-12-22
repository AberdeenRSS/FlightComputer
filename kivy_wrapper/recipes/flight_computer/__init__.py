from pythonforandroid.recipe import IncludedFilesBehaviour, CppCompiledComponentsPythonRecipe, PythonRecipe
import os
import sys

class CoreRecipe(IncludedFilesBehaviour, PythonRecipe):
    version = 'stable'
    src_filename = "../../../flight_computer"
    name = 'flight_computer'

    conflicts = []

    depends = ['setuptools']

    call_hostpython_via_targetpython = False
    install_in_hostpython = True


recipe = CoreRecipe()
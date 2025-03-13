# PandaModelsBackend

PandaModelsBackend provides a high-fidelity backend for [Grid2op](https://github.com/Grid2op/grid2op) that uses [PowerModels.jl](https://github.com/lanl-ansi/PowerModels.jl). It achieves this using a [pandapower](https://github.com/e2nIEE/pandapower) interface that calls [PandaModels.jl](https://github.com/e2nIEE/PandaModels.jl) using PyCall to call Julia functions from Python.

<img src="https://github.com/gt-sse-center/PandaModelsBackend/blob/main/devtools/power_software_map.png" height=450>

## Installation & Usage

```pip install pandamodelsbackend```

Refer to [test_basic_usage](tests/test_basic_usage.py) for full independently runable example.

```
import grid2op
import pandapower as pp
from pandamodelsbackend import PandaModelsBackend

...
pp_net = pp.from_json(network_file)  # Load PandaPower JSON
backend = PandaModelsBackend(pp_net)
env = grid2op.make(env_name, backend=backend)
```

-----

## Setting up the Development Environment

For newcomers to Julia, setting up a software stack with compatible Python and Julia is perhaps the trickiest part of using PandaModelsBackend.
Like Python, one can get Julia through an installer provided by the language developers or through a package manager, like conda.
Both are shown below and are demonstrated (sort-of, for installers) in [GitHub Actions CI](.github/workflows/ci.yml).
You'll need to separately install certain dependencies into Python and others into Julia. You never need to enter the Julia REPL.
If you get tangled up, the CI file is a good, proven route to consult.
[Docs at pandapower](https://pandapower.readthedocs.io/en/v2.6.0/opf/powermodels.html) may also be helpful.
There are a lot of acceptable ways to get Python+Julia working, so as long as [`python-jl tests/test_backend_api.py`](tests/test_backend_api.py) is working at the end, you're probably good to run grid2op.

##### Notes

* This software stack won't work on M1 Macs.
* Conda can be used for Python and Julia for Linux and Intel Macs. There isn't a `julia` package for Silicon Macs, so you'll need to use the Julia installer (+ conda or installer Python).
* A few problems and solutions have been collected [here](#troubleshooting-the-software-stack).

#### Using a Python virtual environment

- Create a python virtual environment
```python3 -m venv venv```

    - If you don't have virtual env installed refer to this [link](https://www.geeksforgeeks.org/python-virtual-environment/)

    - To activate your environment:
    ```source venv/bin/activate```

    - Install grid2op, pandapower
    ```pip install grid2op pandapower```
    ```pip install julia```

- Julia Installation refer to [this](https://docs.julialang.org/en/v1/manual/installation/)

    - set your path variable to find Julia e.g., on MAC
    ```export PATH=/Applications/Julia-1.11.app/Contents/Resources/julia/bin:$PATH```

    - Add PowerModels, PandaModels Packages in Julia
    Run Juila on command prompt. Access the package manager in julia by typing ]. Now install the packages: add Ipopt PowerModels.

    - Build PyCall: The library PyCall allows to use Python from inside julia. By default, PyCall uses the Conda.jl package to install a Miniconda distribution private to Julia. To use an already installed Python distribution (e.g. Anaconda), set the PYTHON environment variable inside the Julia prompt.

        Find path to your python in venv:
        ```which python```
        e.g., <your python path>  - <your venv folder>/bin/python

        On MacOS:
        ```ENV["PYTHON"]="<your python path>"```

     Access the package manager again in julia by typing ]. Now install the packages: ```add PyCall```. To pass the python environment variable, running build PyCall inside the julia package manager may be necessary.

#### Using Conda

0. copy a conda env spec file like [unix.yaml](devtools/conda-envs/unix.yaml). Customize python version, environment name, etc.

```
# 1. create a new conda env from the spec.
conda env create -f unix.yaml && conda activate test

# 2. install editable PandaModelsBackend
git clone https://github.com/gt-sse-center/PandaModelsBackend.git && cd PandaModelsBackend
pip install -e .

# 3. install PowerModels into Julia
#    equivalent to entering pkg mode of Julia REPL, adding packages, and exiting REPL via:
#    julia <Enter> ] <Enter> add Ipopt PowerModels PyCall <Enter> # await compilation <Ctrl-D>
julia -e 'using Pkg; Pkg.add(["Ipopt", "PowerModels", "PandaModels", "PyCall"])'

# 4. (optional) check languages and power projects installed. $CONDA_PREFIX is placeholder, not literal
which python julia python-jl
#> $CONDA_PREFIX/bin/python
#> $CONDA_PREFIX/bin/julia
#> $CONDA_PREFIX/bin/python-jl

conda list | grep -e power -e grid -e panda
#>grid2op                   1.10.5.post1             pypi_0    pypi
#>pandamodelsbackend        0.1.1                    pypi_0    pypi
#>pandapower                2.14.9             pyhd8ed1ab_1    conda-forge
#>pandas                    2.2.3           py312hf9745cd_1    conda-forge

# equivalent to `julia <Enter> ] <Enter> status <Enter> # observe <Ctrl-D>
julia -e 'using Pkg; Pkg.status(); Pkg.status(outdated=true)'
#>Status `$CONDA_PREFIX/share/julia/environments/test/Project.toml`
#>⌅ [b6b21f68] Ipopt v0.9.1
#>  [2dbab86a] PandaModels v0.7.3
#>⌅ [c36e90e8] PowerModels v0.19.10
#>  [438e738f] PyCall v1.96.4
#>Status `$CONDA_PREFIX/share/julia/environments/test/Project.toml`
#>⌅ [b6b21f68] Ipopt v0.9.1 (<v1.7.2): PandaModels
#>⌅ [c36e90e8] PowerModels v0.19.10 (<v0.21.3): PandaModels

# 5. (optional) check Python, Julia, PandaPower functioning together
julia -e 'using PyCall; math = pyimport("math"); print(math.sin(math.pi/4))'
#>0.7071067811865475
pyMm=$(python -c "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')")
python-jl $CONDA_PREFIX/lib/python$pyMm/site-packages/pandapower/test/opf/test_pandamodels_runpm.py
#>20 passed, 1 xpassed, 1226 warnings in 267.01s (0:04:27)
python-jl tests/test_backend_api.py
#>Ran 31 tests in 58.499s
#>OK
```

-----

## Build
```
git clone https://github.com/gt-sse-center/PandaModelsBackend.git
cd PandaModelsBackend
python3 -m build
pip install -e .
```

## Test
```
cd tests
python test_backend_api.py
# depending on installation, `python-jl` may be needed instead of `python` above
```

-----

## Release Procedure

* On a local clone on branch `main`, update the [CHANGELOG](changelog.md) with PRs, the new version number, and the release date. Commit it.
* Make an annotated tag for the new version. Push it along with any cleanup commits (e.g., changelog above). If you've forked the repo, "origin" will probably be "upstream". See `git remote -v` for names.
```
git tag -a v0.5.0 -m "v0.5.0"
git push --atomic origin main v0.5.0
```
* The CI workflow will take over publication to [PyPI](https://pypi.org/project/pandamodelsbackend/) and making a GitHub release. You can edit the frontmatter for the latter through the GitHub web interface with any particular details (and perhaps a link to the CHANGELOG section).

## Troubleshooting the Software Stack

1. **Problem:**
   Your Python interpreter "/path/to/miniconda/envs/rl2grid/bin/python"
   is statically linked to libpython. Currently, PyJulia does not fully
   support such Python interpreter.

   **Solution:**
   Use `python-jl` from conda (or Julia installation) instead of `python`.

2. **Problem:**
   A pip installation involves compiling, and system compilers aren't working.

   **Solution:**
   `conda install cxx-compiler -c conda-forge` and rerun pip.

3. **Problem:**
   AttributeError in pandapower file d2Sbus_dV2.

   **Solution:**
   This was fixed between v2.14.9 and master for csr_matrix?. Alternately, edit the `diagV` to below:
   ```
   /path/to/site-packages/pandapower/pypower/d2Sbus_dV2.py:    try:                         # added
   /path/to/site-packages/pandapower/pypower/d2Sbus_dV2.py:        D = Ybus.H * diagV       # indented
   /path/to/site-packages/pandapower/pypower/d2Sbus_dV2.py:    except AttributeError:       # added
   /path/to/site-packages/pandapower/pypower/d2Sbus_dV2.py:        D = Ybus.getH() * diagV  # added
   ```

4. **Problem:**
   Package testing for PowerModels, PandaModels, or PandaPower shows a few (not all) failures.

   **Solution:**
   For a clean test suite, PowerModels needs Ipopt>=1 and the others need Ipopt<1. To toggle, do
   something like the below. See [CI](.github/workflows/ci.yml) for a known working testing sequence.
   ```
   julia -e 'using Pkg; Pkg.add(Pkg.PackageSpec(;name="Ipopt", version="0.9")); using Ipopt'
   ```

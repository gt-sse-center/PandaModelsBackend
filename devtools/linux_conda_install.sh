#!/usr/bin/env bash

# This assumes you do have Miniconda/Anaconda installed.
# It *doesn't* assume to have Julia installed and instead downloads Julia from Conda.

# 0. copy a conda env spec file like [unix.yaml](https://github.com/gt-sse-center/PandaModelsBackend/blob/main/devtools/conda-envs/unix.yaml).
#   This uses a wget or curl command like the below if not running this script from a repository clone.
#   Customize python version, environment name, etc.
if [ -f "./conda-envs/unix.yaml" ]; then
    cp -p ./conda-envs/unix.yaml .
else
    curl -o ./unix.yaml https://raw.githubusercontent.com/gt-sse-center/PandaModelsBackend/refs/heads/main/devtools/conda-envs/unix.yaml
    # wget -O ./unix.yaml https://raw.githubusercontent.com/gt-sse-center/PandaModelsBackend/refs/heads/main/devtools/conda-envs/unix.yaml
fi

# 1. create a new conda env from the spec.
conda env create -f ./unix.yaml && conda activate test

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


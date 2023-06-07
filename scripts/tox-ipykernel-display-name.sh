# This adjusts the display name for ipykernels
# As we (assume) use of nb_conda_kernels, this will
# make kernels findable.

if [ $# -lt 1 ]; then
    echo "Usage: $0 display_name_base"
    exit 1
fi

base=$1

eval "$(conda shell.bash hook)"

for path in .tox/* ; do

    suffix=$(basename $path)
    display_name=${base}-${suffix}

    echo $x $display_name
    conda activate $path
    conda activate $path && python -m ipykernel install --sys-prefix --display-name "$display_name"
done

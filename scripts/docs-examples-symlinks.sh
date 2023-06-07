# this creates symlinks to filees in /examples/ directory
# you can link to files using (for example)
# ```{eval-rst}
# usage/notebook
# ```
# the script will creat a link
# /docs/examples/usage/notebook.ipynb -> /examples/usage/notebook.ipynb
#

exts=(ipynb md)

rm -rf docs/examples/usage
for path in $(cat docs/examples/*.md | grep '^usage/'); do

    target="examples/"${path}
    name=$(basename $target)

    if [ -f $target ]; then
        # has extension

        base=${name%.*}
        ext=${name##*.}

    else
        # no extension.  Try to add one
        for ext in ${exts[@]}; do
            tmp=${target}.${ext}
            if [ -f "${tmp}" ] ; then
                base=$name
                target=$tmp
                break
            fi
        done
    fi


    new_dir=docs/examples/$(dirname $path)
    mkdir -p $new_dir

    total_target=$(realpath --relative-to=${new_dir} $target)

    # echo "target $target"
    # echo "base  $base"
    # echo "ext  $ext"
    echo "target $total_target"
    echo "new_dir $new_dir"
    echo ""


    ln -s $total_target $new_dir

done

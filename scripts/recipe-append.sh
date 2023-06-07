# This is to fix issues using grayskull with pyproject.toml only projects
# We fall back to using grayskull to create the majority of the recipe
# but add in the final sections
# Edit .recipe-append.yaml
if [ $# -lt 2 ]; then
    echo "need recipe_base_path, recipe_append_path"
    exit 1
fi

base_path=$1
append_path=$2


if [ ! -f $base_path ]; then
   echo "no $base_path"
   exit 1
fi

if [ ! -f $append_path ]; then
   echo "no $append_path"
   exit
fi


tmp_file=$(mktemp)
cp $base_path $tmp_file

echo "" >> $tmp_file

cat $append_path >> $tmp_file

mv $tmp_file $base_path

cat $base_path

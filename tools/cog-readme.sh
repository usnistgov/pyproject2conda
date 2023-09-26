# Hack to get the correct width output

set -x
set -e
stty cols 100


cog -rP README.md
pre-commit run markdownlint --files README.md
# pandoc -V colorlinks tmp.md -o README.pdf
# rm tmp.md

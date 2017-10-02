# Only need to change these two variables
PKG_NAME=llspy
USER=talley

OS=$TRAVIS_OS_NAME-64
mkdir ~/conda-bld
conda config --set anaconda_upload no
export CONDA_BLD_PATH=~/conda-bld
export VERSION=`date +%Y.%m.%d`
conda build .
echo $CONDA_BLD_PATH
ls $CONDA_BLD_PATH
ls ~/conda-bld
echo $OS
ls $CONDA_BLD_PATH/$OS

anaconda -t $CONDA_UPLOAD_TOKEN upload -u $USER -l nightly $CONDA_BLD_PATH/$OS/$PKG_NAME-`date +%Y.%m.%d`-0.tar.bz2 --force
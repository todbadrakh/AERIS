#!/bin/bash

#SBATCH -A stf243
#SBATCH -N 1
#SBATCH -t 1:00:00
#SBATCH -J UO2.vc-relax
#SBATCH --output=%x-%j.out

prefix=UO2.vc-relax
input=vc-relax.in

module load gcc-native/14.2
module load cray-mpich/9.1.0
module load rocm/7.0.2
module load q-e-sirius/1.0.2-mpi-omp

export HDF5_USE_FILE_LOCKING=FALSE
export SIRIUS_VERBOSITY=1

srun -N 1 -n 8 -c 7 --gpus-per-task=1 --gpu-bind=closest pw.x -in ${input} > ${prefix}.log

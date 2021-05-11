#!/bin/bash

declare -a workdirs=(
  "/afs/cern.ch/work/j/jniedzie/private/svjets/autoencodeSVJ/preselection"
  "/t3home/jniedzie/autoencodeSVJ/preselection"
)

found_workdir=false
 

for workdir in ${workdirs[@]}; do
  echo "Trying to move to ${workdir}"
  if [[ -d "$workdir" ]]
  then
    cd $workdir
    echo "moving to $workdir"
    found_workdir=true
    break
  fi
done

if [ $found_workdir != true ]; then
  echo "Couldn't find working directory..."
  exit
fi


string='My long string'
if [[ $HOSTNAME == *"lxplus"* ]]; then
  echo "Setting environment for lxplus"
  . setenv.sh
else
  echo "Setting environemtn for eth T3"
fi



output_path=results/no_lepton_veto_fat_jets/
#output_path=results/no_lepton_veto_ak4_jets/
#output_path=results/all_cuts_fat_jets/
#output_path=results/all_cuts_ak4_jets/

nEvents=$1
i=$(($2-1))



mkdir -p $output_path

ir=$(($i / 6))
im=$(($i % 6))

masses=(1500 2000 2500 3000 3500 4000)
rinvs=(15 30 45 60 75)

mass=${masses[$im]}
rinv=${rinvs[$ir]}

echo "Running for mass: ${mass}, r_inv: ${rinv}"

#input_path=inputFileLists/input_file_list_m${mass}_r${rinv}.txt
input_path=inputFileLists/input_file_list_m3500_mDark20_r30_alphaPeak.txt
#sample_name=SVJ_m${mass}_r${rinv}
sample_name=SVJ_m3500_mDark20_r30_alphaPeak

./SVJselection $input_path $sample_name $output_path 0 $nEvents

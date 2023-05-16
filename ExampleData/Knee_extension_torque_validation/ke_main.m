% by Basilio Goncalves, basilio.goncalves7@gmail.com, https://github.com/basgoncalves
function ke_main()

activate_msk_modelling

make_ik_file(ikFilePath,coordinates)

create_force_file()

create_msk_model()

define_simulation_parameters() % simulation parameters

run_simulations()

plot_results()



function make_ik_file(ikFilePath,coordinates)
if nargin <2
    ikFilePath = 'C:\Git\msk_modelling_python\ExampleData\Knee_extension_torque_validation\ik.mot';
end

ik = load(ikFilePath);

function activate_msk_modelling()
clear; clc; close all;                                                                                              % clean workspace (use restoredefaultpath if needed)

activeFile = [mfilename('fullpath') '.m'];                                                                          % get dir of the current file
msk_dir  = fileparts(activeFile);

try
    isbopsactive;    % check if the pipeline is in the path
    addpath(genpath([msk_dir fp 'src' fp 'OpenSim']));
    disp([msk_dir ' is already in the path'])
catch
    addpath(genpath(msk_dir));                                                                                          % add current folder to MATLAB path    
end    


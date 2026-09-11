function run_mrs(cfgFile)
% run_mrs(cfgFile) -- BioScout driver for the KU Leuven Muscle Redundancy Solver.
%
% cfgFile is the JSON written by bioscout.mrs.config.MRSConfig.to_json():
%   .model_path .out_path .mrs_dir .time  and .Misc (the Misc struct).
% Writes <out_path>/MRS_Results.mat and prints BIOSCOUT_MRS_OK on success.

cfg = jsondecode(fileread(cfgFile));

if ~isempty(cfg.mrs_dir)
    addpath(genpath(cfg.mrs_dir));
end
if exist('solveMuscleRedundancy', 'file') ~= 2
    error('solveMuscleRedundancy not on the MATLAB path (mrs_dir = "%s")', cfg.mrs_dir);
end

% --- Misc: JSON decodes n x m string arrays as nested cells; flatten them ---
Misc = struct();
names = fieldnames(cfg.Misc);
for i = 1:numel(names)
    v = cfg.Misc.(names{i});
    if iscell(v) && ~isempty(v) && iscell(v{1})
        v = vertcat(v{:});                 % {{'a','b'};{'c','d'}} -> 2x2 cell
    elseif ischar(v)
        v = {v};                           % a lone string stays a cell array
    end
    Misc.(names{i}) = v;
end
Misc.OutPath = cfg.out_path;

% --- time: [t0 t1], or one row per trial ------------------------------------
t = cfg.time(:)';
if numel(t) > 2
    t = reshape(t, 2, [])';
end

if ~exist(cfg.out_path, 'dir'); mkdir(cfg.out_path); end

nOut = nargout('solveMuscleRedundancy');
if nOut >= 3
    [Results, DatStore, MiscOut] = solveMuscleRedundancy(cfg.model_path, t, cfg.out_path, Misc);
else
    [Results, DatStore] = solveMuscleRedundancy(cfg.model_path, t, cfg.out_path, Misc);
    MiscOut = Misc;
end

save(fullfile(cfg.out_path, 'MRS_Results.mat'), 'Results', 'DatStore', 'MiscOut', '-v7');
disp('BIOSCOUT_MRS_OK');
end

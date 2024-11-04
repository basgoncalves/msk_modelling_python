function [morphoscaledOsimModel] = getMorphoScaledModel(osimModel_reference, osimModel_target, baseDir)
import org.opensim.modeling.*
fp = getFp();
addpath('C:\Users\s2849511\coding\versioning\MuscleOptimizer\matlab\MuscleParOptTool')
path = [baseDir fp 'scaling'];
[osimModel_opt, SimInfo] = optimMuscleParams(osimModel_reference, osimModel_target, 9, '.');
morphoscaledOsimModel = join([path fp char(osimModel_opt.getName())],'');
osimModel_opt.print(morphoscaledOsimModel)
end



function [MaxIsomForce] = getMaxIsomForce(muscleName, osimModel)

import org.opensim.modeling.*;
osimModel = Model(osimModel);
osimMuscles = osimModel.getMuscles();

for i = 0:osimMuscles.getSize()-1
    if strcmp(osimMuscles.get(i).getName(),muscleName)
        currenctMuscle = osimMuscles.get(i);
        MaxIsomForce = currenctMuscle.get_max_isometric_force();
    end
end
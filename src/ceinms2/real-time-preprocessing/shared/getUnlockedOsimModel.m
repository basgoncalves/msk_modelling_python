function [ unlockedModelFilename ] = getUnlockedOsimModel( osimModelFilename )
%GETUNLOCKEDOSIMMODEL Summary of this function goes here
%   Removes all the lock from the joints in the model
%   which is required to calculate the splines
    import org.opensim.modeling.*

    addpath('shared')
    fp = getFp();
    osimModel = Model(osimModelFilename);
    coordSet = osimModel.getCoordinateSet();
    for i=0:coordSet.getSize()-1
        coordSet.get(i).setDefaultLocked(false)
    end
    
    [pathstr,name,ext] = fileparts(osimModelFilename);
    unlockedName = [name '_unlocked'];
    unlockedModelFilename = join([pathstr fp unlockedName ext], '');
   % osimModel.setName( unlockedName)
    osimModel.print(unlockedModelFilename)

    
end

